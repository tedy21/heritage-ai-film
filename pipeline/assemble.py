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
import json
import re
import time
from pathlib import Path

from . import shots as shots_mod
from . import subtitles, timeline
from .common import (OUT, ROOT, STAGE_VERSION, Call, duration, ffmpeg, file_hash, load_env,
                     load_storyboard, log_cache_hit, log_event, run, stable_hash)
from .music import music_track

TARGET_LUFS, TARGET_TP, TARGET_LRA = -14.0, -1.0, 11.0


def _cached(name: str, key: str, ext: str = "mp4") -> Path:
    d = OUT / "final"
    d.mkdir(parents=True, exist_ok=True)
    return d / f".{name}-{key}.{ext}"


def build_mix(sb: dict, tl: dict, music: Path) -> Path:
    narr = [(ROOT / s["narration"], s["narration_start"]) for s in tl["shots"] if s["narration"]]
    duck = {"threshold": 0.02, "ratio": 6, "attack_ms": 300, "release_ms": 1500, **sb["music"].get("ducking", {})}
    total = tl["total"]
    key = stable_hash(STAGE_VERSION["assemble"], [(p, o) for p, o in narr], music, duck,
                      sb["music"]["volume_db"], total, TARGET_LUFS)
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
    fade_out = max(total - 3.0, 0)
    fc = ";".join(chains + [
        "".join(f"[n{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:dropout_transition=0,"
        f"apad=whole_dur={total},atrim=0:{total}[narr]",
        "[narr]asplit=2[nmix][nkey]",
        f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{total},asetpts=N/SR/TB,"
        f"loudnorm=I=-20:TP=-3,volume={sb['music']['volume_db']}dB,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={fade_out:.2f}:d=3[mus]",
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
           f"offset={m['target_offset']}:linear=true", "-ar", "48000", str(out))
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
    if final.exists() and stamp.exists() and stamp.read_text() == key:
        log_cache_hit(call, final)
        return final
    t0 = time.time()
    lst = OUT / "final" / f".{name}.concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segments))
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


def radio_cut(sb: dict, tl: dict, mix: Path, srt: Path) -> Path:
    """Narration + temp music over black, with subtitles so non-Amharic testers can follow."""
    segs = []
    w, h = shots_mod.ASPECTS["16x9"]
    black = OUT / "final" / ".black.mp4"
    ffmpeg("-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={tl['total']}:r={sb['meta']['fps']}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p", str(black))
    segs.append(black)
    return export(sb, tl, "16x9", mix, srt, segs, "radio_cut")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radio", action="store_true", help="narration-only radio cut on black")
    ap.add_argument("--aspects", default="16x9,9x16")
    a = ap.parse_args()
    load_env()
    sb = load_storyboard()
    tl = timeline.compute(sb)
    timeline.save(tl)
    print(f"assemble: total {tl['total']:.1f}s ({len(tl['shots'])} shots + end card)")
    if not 60 <= tl["total"] <= 90:
        print(f"  WARNING: total {tl['total']:.1f}s is outside the 60-90 s brief")
    music = music_track(sb)
    srt = subtitles.build_srt(sb, tl)
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
