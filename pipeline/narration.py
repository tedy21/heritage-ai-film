"""Stage: narration. One WAV per shot from Gemini TTS, cached by a hash of
(text, voice, style, model). Changing one line regenerates one file.

Output: outputs/narration/<shot>-<key>.wav (48 kHz mono, silence trimmed)
        outputs/narration/manifest.json  {shot: {path, duration_s}}
"""
from __future__ import annotations

import json
import sys
import time
import wave
from pathlib import Path

from . import pricing
from .common import (OUT, STAGE_VERSION, Call, cached_path, duration, ffmpeg, load_env,
                     load_storyboard, log_cache_hit, log_event, offline, prune,
                     require_env, selected_shots, stable_hash, with_retries)


def _write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def _normalise(raw: Path, out: Path) -> None:
    """Trim leading/trailing silence, resample to 48 kHz, even loudness."""
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB,"
            "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse")
    ffmpeg("-i", str(raw), "-af", f"{trim},loudnorm=I=-18:TP=-2:LRA=11",
           "-ar", "48000", "-ac", "1", str(out))


def narrate_shot(sb: dict, shot: dict) -> Path | None:
    text = shot["narration"].strip()
    if not text:
        return None
    m = sb["meta"]
    model = "offline-silence" if offline() else m["models"]["tts"]
    voice = m["narration_voice"]
    key = stable_hash(STAGE_VERSION["narration"], text, voice, model)
    out = cached_path("narration", shot["id"], key, "wav")
    call = Call("narration", shot["id"], "offline" if offline() else "gemini", model,
                {"voice": voice["voice"], "style": voice["style"], "chars": len(text)})
    if out.exists():
        log_cache_hit(call, out)
        return out

    if offline():
        # ~0.55 s per Amharic word: a rough stand-in so timing can be tested.
        secs = max(2.0, 0.55 * len(text.split()))
        t0 = time.time()
        ffmpeg("-f", "lavfi", "-i", f"anoisesrc=d={secs}:c=pink:a=0.02", "-ar", "48000", "-ac", "1", str(out))
        log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out))
        return out

    from . import gemini
    raw = out.with_suffix(".raw.wav")

    def go():
        pcm, rate = gemini.tts(model, f"{voice['style']}\n{text}", voice["voice"])
        _write_wav(raw, pcm, rate)
        return rate

    with_retries(call, go, max_attempts=4, base_delay=8,
                 cost_usd_equiv=pricing.tts_cost(0.55 * len(text.split())), output=out)
    _normalise(raw, out)
    raw.unlink(missing_ok=True)
    prune("narration", shot["id"], out)
    return out


def main() -> None:
    load_env()
    sb = load_storyboard()
    if not offline():
        require_env("GEMINI_API_KEY")
    manifest_path = OUT / "narration" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    print("narration:")
    failed = []
    for shot in selected_shots(sb):
        try:
            p = narrate_shot(sb, shot)
        except Exception as e:  # keep going; one bad line shouldn't stop the others
            print(f"  [narration:{shot['id']}] FAILED: {e}")
            failed.append(shot["id"])
            continue
        manifest[shot["id"]] = {"path": str(p.relative_to(OUT.parent)) if p else None,
                                "duration_s": round(duration(p), 3) if p else 0.0}
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
