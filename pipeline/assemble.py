"""Stage: assembly (FFmpeg only, deterministic).

  1. timeline from measured narration
  2. narration stem: each shot's WAV placed at its offset
  3. music stem: score (or temp pad) looped/trimmed, faded, ducked under the
     narration with sidechaincompress
  4. mix -> two-pass loudnorm to -14 LUFS / -1 dBTP
  5. per aspect: concat shot segments + end card, burn subtitles, mux
Outputs: outputs/final/tana_16x9.mp4, outputs/final/tana_9x16.mp4
         (--radio: outputs/final/radio_cut.mp4, black picture + narration + temp music)
"""
from __future__ import annotations

import argparse
import os
import json
import re
import time
from pathlib import Path

from . import shots as shots_mod
from . import subtitles, timeline
from .common import (OUT, ROOT, STAGE_VERSION, Call, duration, ffmpeg, file_hash, load_env,
                     load_storyboard, log_cache_hit, log_event, run, stable_hash)
from .music import music_track
from . import spotting

TARGET_LUFS, TARGET_TP, TARGET_LRA = -14.0, -1.0, 11.0
LIMIT_DB = -3.0  # sample ceiling before AAC; AAC adds ~1.2 dB overshoot (measured, F18)
LIMIT_LIN = round(10 ** (LIMIT_DB / 20), 4)


def _cached(name: str, key: str, ext: str = "mp4") -> Path:
    d = OUT / "final"
    d.mkdir(parents=True, exist_ok=True)
    return d / f".{name}-{key}.{ext}"


def build_mix(sb: dict, tl: dict, music: Path) -> Path:
    narr = [(ROOT / s["narration"], s["narration_start"]) for s in tl["shots"] if s["narration"]]
    duck = {"threshold": 0.02, "ratio": 6, "attack_ms": 300, "release_ms": 1500, **sb["music"].get("ducking", {})}
    total = tl["total"]
    shape = spotting.cue_gain_expr(sb, tl)
    key = stable_hash(STAGE_VERSION["assemble"], [(p, o) for p, o in narr], music, duck,
                      sb["music"]["volume_db"], total, TARGET_LUFS, shape)
    out = _cached("mix", key, "wav")
    call = Call("assemble", "mix", "ffmpeg", "sidechaincompress+loudnorm",
                {"ducking": duck, "music_db": sb["music"]["volume_db"], "target_lufs": TARGET_LUFS})
    if out.exists():
        log_cache_hit(call, out)
        return out
    t0 = time.time()
    args, chains = [], []
    for i, (p, offset) in enumerate(narr):
        args += ["-i", str(p)]
        ms = int(offset * 1000)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}:all=1[n{i}]")
    n = len(narr)
    args += ["-stream_loop", "-1", "-i", str(music)]
    fade_out = max(tl["end_card_start"] - 0.5, 0)  # fade the score across the end card
    fc = ";".join(chains + [
        "".join(f"[n{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:dropout_transition=0,"
        f"apad=whole_dur={total},atrim=0:{total}[narr]",
        "[narr]asplit=2[nmix][nkey]",
        f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{total},asetpts=N/SR/TB,"
        f"loudnorm=I=-20:TP=-3,volume={sb['music']['volume_db']}dB,"
        + (f"volume='{shape}':eval=frame," if shape else "") +
        f"afade=t=in:st=0:d=1,afade=t=out:st={fade_out:.2f}:d={total - fade_out:.2f}[mus]",
        f"[mus][nkey]sidechaincompress=threshold={duck['threshold']}:ratio={duck['ratio']}:"
        f"attack={duck['attack_ms']}:release={duck['release_ms']}[ducked]",
        "[nmix][ducked]amix=inputs=2:normalize=0:duration=first[pre]",
    ])
    pre = out.with_name(out.stem + ".pre.wav")
    ffmpeg(*args, "-filter_complex", fc, "-map", "[pre]", "-ar", "48000", str(pre))
    # two-pass loudnorm: measure, then apply linearly
    res = run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af",
               f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json", "-f", "null", "-"])
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S).group(0))
    ffmpeg("-i", str(pre), "-af",
           f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA={TARGET_LRA}:measured_I={m['input_i']}:"
           f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
           f"offset={m['target_offset']}:linear=true,"
           # linear loudnorm can't hold the ceiling and AAC adds overshoot: a brickwall
           # at LIMIT_DB keeps the exported AAC true peak under -1 dBTP (brief: Appendix B)
           f"alimiter=limit={LIMIT_LIN}:level=disabled:latency=1:attack=5:release=50", "-ar", "48000", str(out))
    pre.unlink(missing_ok=True)
    for old in (OUT / "final").glob(".mix-*.wav"):
        if old != out:
            old.unlink()
    log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out),
              measured_input_lufs=m["input_i"])
    return out


def _sub_style(aspect: str) -> str:
    # libass scales SRT styles against a 288px-high canvas
    if aspect == "9x16":
        return "FontName=Noto Sans,FontSize=9,Outline=1,Shadow=0,BorderStyle=1,MarginV=62,MarginL=20,MarginR=20"
    return "FontName=Noto Sans,FontSize=15,Outline=1,Shadow=0,BorderStyle=1,MarginV=16"


def export(sb: dict, tl: dict, aspect: str, mix: Path, srt: Path, segments: list[Path], name: str) -> Path:
    key = stable_hash(STAGE_VERSION["assemble"], segments, mix, srt, aspect)
    final = OUT / "final" / f"{name}.mp4"
    stamp = OUT / "final" / f".{name}.key"
    call = Call("assemble", name, "ffmpeg", "concat+subtitles+mux", {"aspect": aspect, "segments": len(segments)})
    lst = OUT / "final" / f".{name}.concat.txt"
    # relative paths: the list is committed, so no machine-specific absolute paths
    lst.write_text("".join(f"file '{os.path.relpath(p, lst.parent)}'\n" for p in segments))
    if final.exists() and stamp.exists() and stamp.read_text() == key:
        log_cache_hit(call, final)
        return final
    t0 = time.time()
    vf = f"subtitles={shots_mod.fq(srt)}:force_style='{_sub_style(aspect)}'"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(mix),
           "-vf", vf, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-r", str(sb["meta"]["fps"]), "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-metadata", f"title={sb['meta']['title_en']}",
           "-metadata", "comment=Made with AI (FLUX, Wan 2.2, Gemini TTS, ACE-Step). Historical scenes are AI reconstructions.",
           "-movflags", "+faststart", str(final))
    stamp.write_text(key)
    log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(final),
              duration_s=round(duration(final), 2))
    return final


def _black(sb: dict, tl: dict) -> Path:
    """Black picture for the radio cut, with the film title (Amharic + English)
    centred above the subtitle area so testers know what they're watching."""
    from .common import FONT_ETHIOPIC, FONT_LATIN
    w, h = shots_mod.ASPECTS["16x9"]
    titles = [sb["meta"]["title_am"], sb["meta"]["title_en"]]
    black = OUT / "final" / f".black-{stable_hash(tl['total'], titles, 'title-v1')}.mp4"
    if not black.exists():
        d = OUT / "final"
        (d / ".title_am.txt").write_text(titles[0], encoding="utf-8")
        (d / ".title_en.txt").write_text(titles[1], encoding="utf-8")
        fq = shots_mod.fq
        vf = (f"drawtext=fontfile={fq(FONT_ETHIOPIC)}:textfile={fq(d / '.title_am.txt')}:fontsize=64:"
              f"fontcolor=white:x=(w-tw)/2:y=h*0.36-th,"
              f"drawtext=fontfile={fq(FONT_LATIN)}:textfile={fq(d / '.title_en.txt')}:fontsize=28:"
              f"fontcolor=white@0.75:x=(w-tw)/2:y=h*0.36+24,"
              f"fade=t=in:st=0:d=1")
        ffmpeg("-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={tl['total']}:r={sb['meta']['fps']}",
               "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p", str(black))
        for old in d.glob(".black-*.mp4"):
            if old != black:
                old.unlink()
    return black


def radio_cut(sb: dict, tl: dict, mix: Path, srt: Path) -> Path:
    """Narration + music over black, with subtitles so non-Amharic testers can follow."""
    return export(sb, tl, "16x9", mix, srt, [_black(sb, tl)], "radio_cut")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radio", action="store_true", help="narration-only radio cut on black")
    ap.add_argument("--aspects", default="16x9,9x16")
    ap.add_argument("--audition", action="store_true",
                    help="radio cut once per candidate in outputs/music/candidates, to choose the score under the voice")
    a = ap.parse_args()
    load_env()
    sb = load_storyboard()
    tl = timeline.compute(sb)
    timeline.save(tl)
    print(f"assemble: total {tl['total']:.1f}s ({len(tl['shots'])} shots + end card)")
    if not 60 <= tl["total"] <= 90:
        print(f"  WARNING: total {tl['total']:.1f}s is outside the 60-90 s brief")
    spotting.write_notes(sb, tl)
    srt = subtitles.build_srt(sb, tl)
    if a.audition:
        cands = sorted((ROOT / "outputs" / "music" / "candidates").glob("*.flac"))
        if not cands:
            raise SystemExit("no candidates in outputs/music/candidates")
        for c in cands:
            mix = build_mix(sb, tl, c)
            out = export(sb, tl, "16x9", mix, srt, [_black(sb, tl)], f"audition_{c.stem}")
            print("  ->", out.relative_to(ROOT))
        return
    music = music_track(sb)
    mix = build_mix(sb, tl, music)
    if a.radio:
        print("  ->", radio_cut(sb, tl, mix, srt).relative_to(ROOT))
        return
    keyframes = shots_mod.keyframe_paths()
    for aspect in a.aspects.split(","):
        segs = [shots_mod.build_segment(sb, s, keyframes[s["id"]], t["length"], aspect)
                for s, t in zip(sb["shots"], tl["shots"])]
        segs.append(shots_mod.end_card(sb, aspect, tl["end_card_len"]))
        print("  ->", export(sb, tl, aspect, mix, srt, segs, f"tana_{aspect}").relative_to(ROOT))


if __name__ == "__main__":
    main()
