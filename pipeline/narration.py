"""Stage: narration. One WAV per shot from Gemini TTS.

Two cache layers, so post-processing tweaks never spend API quota:
  raw        outputs/narration/raw/<shot>-<rawkey>.wav
             what the model returned (one line). rawkey = hash(text, voice name,
             style, model chain). Costs a TTS request to create.
  processed  outputs/narration/<shot>-<key>.wav
             edge-trimmed (clicks ignored), long pauses capped, short fades,
             optional tempo, loudness-matched. key = hash(raw bytes + processing
             settings). Pure FFmpeg, free to redo.

Two ways to create raw audio:
  * batch  - when >= batch_min lines need raw audio (e.g. the first run), the
             whole script is sent in ONE TTS request (text only, lines separated
             by blank lines) and split at the n-1 longest silences. 1 request
             instead of n (free tier: 10 TTS requests/model/day, FAILURES F13)
             and one consistent voice and pace.
  * single - otherwise (e.g. one edited line): one request for that line.
If the batch split doesn't validate, it falls back to single requests.

Outputs: outputs/narration/manifest.json {shot: {path, duration_s, model}}
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

from . import pricing
from .common import (OUT, STAGE_VERSION, Call, cached_path, duration, ffmpeg, load_env,
                     load_storyboard, log_cache_hit, log_event, model_chain, offline, prune,
                     require_env, selected_shots, stable_hash, with_fallbacks)

RAW_STAGE = "narration/raw"
FADE_IN_S, FADE_OUT_S = 0.02, 0.06
CLICK_S = 0.08  # sound shorter than this at an edge is treated as a click, not speech


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


_last_call = [0.0]


def _throttle(min_interval: float) -> None:
    """Space TTS calls so the free tier's per-minute limit isn't hit (429s
    would push lines onto a backup model with a different voice)."""
    wait = _last_call[0] + min_interval - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()


# ------------------------------------------------------------------ keys
def _chain(sb: dict) -> list[str]:
    return ["offline-silence"] if offline() else model_chain(sb["meta"]["models"], "tts")


def raw_path(sb: dict, shot: dict) -> Path:
    """Model output for one line. Keyed on what the model sees (text, voice,
    style) and the whole fallback chain, so a line made by a backup model is
    kept when the primary recovers. Processing settings are NOT in this key."""
    v = sb["meta"]["narration_voice"]
    key = stable_hash("raw-v1", shot["narration"].strip(), v["voice"], v.get("style", ""), _chain(sb))
    return cached_path(RAW_STAGE, shot["id"], key, "wav")


def _proc_settings(sb: dict) -> dict:
    v = sb["meta"]["narration_voice"]
    return {"max_pause_s": v.get("max_pause_s", 0.45), "tempo": v.get("tempo", 1.0),
            "fade": [FADE_IN_S, FADE_OUT_S], "click_s": CLICK_S, "loudness": -18}


def processed_path(sb: dict, shot: dict, raw: Path) -> Path:
    key = stable_hash(STAGE_VERSION["narration"], raw, _proc_settings(sb))
    return cached_path("narration", shot["id"], key, "wav")


# ------------------------------------------------------------------ processing
def _process(raw: Path, out: Path, settings: dict) -> None:
    """Free post-processing (FFmpeg only):
    - trim edge silence, ignoring clicks shorter than CLICK_S (the F16 start glitch)
    - cap internal pauses at max_pause_s
    - optional pitch-preserving tempo
    - short fade in/out so cut points never click
    - even loudness, 48 kHz mono"""
    edge = (f"silenceremove=start_periods=1:start_duration={settings['click_s']}:"
            f"start_threshold=-45dB:detection=peak")
    pauses = (f"silenceremove=stop_periods=-1:stop_duration={settings['max_pause_s']}:"
              f"stop_threshold=-45dB:stop_silence={settings['max_pause_s']}")
    fi, fo = settings["fade"]
    chain = [edge, "areverse", edge, f"afade=t=in:d={fo}", "areverse", f"afade=t=in:d={fi}", pauses]
    if abs(settings["tempo"] - 1.0) > 1e-3:
        chain.append(f"atempo={settings['tempo']}")
    chain.append(f"loudnorm=I={settings['loudness']}:TP=-2:LRA=11")
    ffmpeg("-i", str(raw), "-af", ",".join(chain), "-ar", "48000", "-ac", "1", str(out))


def _ensure_processed(sb: dict, shot: dict, raw: Path) -> Path:
    out = processed_path(sb, shot, raw)
    call = Call("narration-process", shot["id"], "ffmpeg", "trim+fades+loudnorm", _proc_settings(sb))
    if out.exists():
        log_cache_hit(call, out)
        return out
    t0 = time.time()
    _process(raw, out, _proc_settings(sb))
    side = raw.with_suffix(".json")
    meta = json.loads(side.read_text()) if side.exists() else {}
    out.with_suffix(".json").write_text(json.dumps({**meta, "raw": raw.name}))
    log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out))
    prune("narration", shot["id"], out)
    return out


# ------------------------------------------------------------------ batch raw
def _silences(wav: Path) -> list[tuple[float, float]]:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af",
                          "silencedetect=noise=-40dB:d=0.3", "-f", "null", "-"],
                         capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", res.stderr)]
    return list(zip(starts, ends))


def _split_batch(wav: Path, texts: list[str]) -> list[tuple[float, float]] | None:
    """Cut points at the n-1 longest silences. Returns n (start, end) spans,
    or None if the result doesn't look like the script (then: per-line)."""
    n = len(texts)
    sil = sorted(_silences(wav), key=lambda se: se[1] - se[0], reverse=True)[: n - 1]
    if len(sil) < n - 1:
        return None
    cuts = sorted((a + b) / 2 for a, b in sil)
    bounds = [0.0, *cuts, duration(wav)]
    spans = list(zip(bounds[:-1], bounds[1:]))
    total_chars = sum(len(t) for t in texts)
    total_dur = bounds[-1]
    for (a, b), t in zip(spans, texts):
        expected = total_dur * len(t) / total_chars
        if b - a < 1.0 or not 0.35 <= (b - a) / expected <= 2.8:
            print(f"  batch split rejected: span {b - a:.1f}s vs expected {expected:.1f}s")
            return None
    return spans


def batch_generate(sb: dict, shots: list[dict]) -> int:
    """One TTS request for all `shots`; writes each line's raw WAV. Returns
    the number of lines written (0 = batch failed, caller falls back)."""
    from . import gemini
    voice = sb["meta"]["narration_voice"]
    texts = [s["narration"].strip() for s in shots]
    chain = _chain(sb)
    item = f"batch[{','.join(s['id'] for s in shots)}]"
    # Only the script itself: TTS models speak any instruction text aloud (F15).
    # Paragraph breaks give the pauses the splitter cuts on.
    prompt = "\n\n".join(texts)
    tmp = OUT / RAW_STAGE / "batch.tmp.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)

    def go(model_id: str):
        _throttle(voice.get("min_interval_s", 0))
        pcm, rate = gemini.tts(model_id, prompt, voice["voice"])
        _write_wav(tmp, pcm, rate)

    words = sum(len(t.split()) for t in texts)
    try:
        _, used = with_fallbacks("narration", item, "gemini", chain,
                                 {"voice": voice["voice"], "lines": len(texts),
                                  "chars": sum(map(len, texts)), "mode": "batch"}, go,
                                 attempts_per_model=2, base_delay=6, cost_usd_equiv=pricing.tts_cost(0.55 * words))
    except Exception as e:
        print(f"  batch request failed ({e}); falling back to per-line requests")
        return 0
    spans = _split_batch(tmp, texts)
    if not spans:
        keep = OUT / RAW_STAGE / f"batch-rejected-{int(time.time())}.wav"
        tmp.rename(keep)
        print(f"  kept the unsplittable batch audio at {keep.name}; falling back to per-line requests")
        return 0
    for shot, (a, b) in zip(shots, spans):
        raw = raw_path(sb, shot)
        ffmpeg("-i", str(tmp), "-ss", f"{a:.3f}", "-to", f"{b:.3f}", str(raw))
        raw.with_suffix(".json").write_text(json.dumps(
            {"model": used, "fallback": used != chain[0], "mode": "batch", "batch": item,
             "span_s": [round(a, 3), round(b, 3)]}))
        prune(RAW_STAGE, shot["id"], raw)
    tmp.unlink(missing_ok=True)
    print(f"  batch: {len(shots)} lines from 1 request ({used})")
    return len(shots)


# ------------------------------------------------------------------ single raw
def single_generate(sb: dict, shot: dict) -> Path:
    voice = sb["meta"]["narration_voice"]
    text = shot["narration"].strip()
    raw = raw_path(sb, shot)
    chain = _chain(sb)
    params = {"voice": voice["voice"], "chars": len(text), "mode": "single"}
    if offline():
        # ~0.55 s per Amharic word: a rough stand-in so timing can be tested.
        secs = max(2.0, 0.55 * len(text.split()))
        t0 = time.time()
        ffmpeg("-f", "lavfi", "-i", f"anoisesrc=d={secs}:c=pink:a=0.02", "-ar", "48000", "-ac", "1", str(raw))
        log_event(Call("narration", shot["id"], "offline", chain[0], params), status="ok",
                  latency_s=time.time() - t0, cache_hit=False, output=str(raw))
        raw.with_suffix(".json").write_text(json.dumps({"model": chain[0], "mode": "offline"}))
        return raw
    from . import gemini
    tmp = raw.with_suffix(".tmp.wav")

    def go(model_id: str):
        _throttle(voice.get("min_interval_s", 0))
        spoken = f"{voice['style']}\n{text}" if voice.get("style") else text  # F15: style is spoken aloud
        pcm, rate = gemini.tts(model_id, spoken, voice["voice"])
        _write_wav(tmp, pcm, rate)

    _, used = with_fallbacks("narration", shot["id"], "gemini", chain, params, go,
                             attempts_per_model=2, base_delay=6,
                             cost_usd_equiv=pricing.tts_cost(0.55 * len(text.split())), output=raw)
    tmp.rename(raw)
    raw.with_suffix(".json").write_text(json.dumps({"model": used, "fallback": used != chain[0], "mode": "single"}))
    prune(RAW_STAGE, shot["id"], raw)
    return raw


def narrate_shot(sb: dict, shot: dict) -> Path | None:
    if not shot["narration"].strip():
        return None
    raw = raw_path(sb, shot)
    if raw.exists():
        side = raw.with_suffix(".json")
        model = json.loads(side.read_text()).get("model") if side.exists() else None
        log_cache_hit(Call("narration", shot["id"], "gemini", model or _chain(sb)[0], {"mode": "raw-cache"}), raw)
    else:
        raw = single_generate(sb, shot)
    return _ensure_processed(sb, shot, raw)


def main() -> None:
    load_env()
    sb = load_storyboard()
    if not offline():
        require_env("GEMINI_API_KEY")
    manifest_path = OUT / "narration" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    print("narration:")
    todo = [s for s in selected_shots(sb) if s["narration"].strip() and not raw_path(sb, s).exists()]
    batch_min = sb["meta"]["narration_voice"].get("batch_min", 3)
    if not offline() and len(todo) >= batch_min:
        batch_generate(sb, todo)
    failed = []
    for shot in selected_shots(sb):
        try:
            p = narrate_shot(sb, shot)
        except Exception as e:  # keep going; one bad line shouldn't stop the others
            print(f"  [narration:{shot['id']}] FAILED: {e}")
            failed.append(shot["id"])
            continue
        side = p.with_suffix(".json") if p else None
        made_by = json.loads(side.read_text()).get("model") if side and side.exists() else None
        manifest[shot["id"]] = {"path": str(p.relative_to(OUT.parent)) if p else None,
                                "duration_s": round(duration(p), 3) if p else 0.0,
                                "model": made_by}
    valid_ids = {s["id"] for s in sb["shots"]}
    manifest = {k: v for k, v in manifest.items() if k in valid_ids}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    total = sum(v["duration_s"] for v in manifest.values())
    print(f"  narration total {total:.1f}s")
    if failed:
        sys.exit(f"narration failed for {failed}")


if __name__ == "__main__":
    main()
