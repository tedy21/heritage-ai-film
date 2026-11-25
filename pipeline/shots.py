"""Stage: moving shots -> per-aspect video segments.

For each shot and each aspect ratio a segment of exactly the timeline length
is rendered:
  * render == "wan" and outputs/clips/<shot>.mp4 exists -> the Wan 2.2 clip
    (generated on Kaggle by notebooks/wan22_i2v_kaggle.py), cover-cropped,
    first 0.25 s trimmed, gently slowed / held to fill the shot;
  * otherwise -> a Ken Burns move over the keyframe (the always-available
    fallback, also a respectable shot in its own right).
Reconstruction shots get a warm, desaturated grade, a vignette and an
"AI reconstruction" tag so viewers can tell them from present-day scenes.
Segments are cached by hash(source bytes + move + length + grade + aspect).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .common import (FONT_ETHIOPIC, FONT_LATIN, OUT, ROOT, STAGE_VERSION, Call, cached_path,
                     duration, ffmpeg, log_cache_hit, log_event, prune, stable_hash)

ASPECTS = {"16x9": (1280, 720), "9x16": (720, 1280)}

_MOVES = {
    "push_in":   ("1+0.15*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pull_out":  ("1.15-0.15*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pan_left":  ("1.12", "(iw-iw/zoom)*(1-on/{N})", "ih/2-(ih/zoom/2)"),
    "pan_right": ("1.12", "(iw-iw/zoom)*on/{N}", "ih/2-(ih/zoom/2)"),
    "tilt_up":   ("1.12", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(1-on/{N})"),
    "tilt_down": ("1.12", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*on/{N}"),
    "static":    ("1.04", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
}

GRADE_RECON = "eq=saturation=0.55:contrast=1.05,colorbalance=rs=0.10:gs=0.03:bs=-0.10,vignette=PI/4.5"


def fq(p) -> str:
    """Quote a file path for use inside an FFmpeg filter argument (spaces, colons)."""
    return "'" + str(p).replace("\\", "/").replace("'", r"'\''").replace(":", r"\:") + "'"


def _cover(w: int, h: int) -> str:
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"


def _overlays(sb: dict, shot: dict, w: int, h: int, length: float) -> list[str]:
    f = []
    if shot["era"] == "reconstruction":
        f.append(GRADE_RECON)
        fs = int(h * 0.024)
        f.append(f"drawtext=fontfile={fq(FONT_LATIN)}:text='AI reconstruction':fontsize={fs}:"
                 f"fontcolor=white@0.85:box=1:boxcolor=black@0.35:boxborderw={fs // 3}:"
                 f"x={int(w * 0.05)}:y={int(h * 0.06)}")
    if shot.get("overlay_title"):
        tdir = OUT / "segments"
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "title_am.txt").write_text(sb["meta"]["title_am"], encoding="utf-8")
        (tdir / "title_en.txt").write_text(sb["meta"]["title_en"], encoding="utf-8")
        big = int(min(w, h) * (0.075 if w > h else 0.068))
        small = int(big * 0.42)
        alpha = f"if(lt(t,1),0,if(lt(t,2),t-1,if(lt(t,{length - 1.5:.2f}),1,max(0,({length - 0.5:.2f}-t)))))"
        f.append(f"drawtext=fontfile={fq(FONT_ETHIOPIC)}:textfile={fq(tdir / 'title_am.txt')}:fontsize={big}:"
                 f"fontcolor=white:alpha='{alpha}':shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                 f"x=(w-tw)/2:y=h*0.40-th")
        f.append(f"drawtext=fontfile={fq(FONT_LATIN)}:textfile={fq(tdir / 'title_en.txt')}:fontsize={small}:"
                 f"fontcolor=white:alpha='{alpha}':shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                 f"x=(w-tw)/2:y=h*0.40+{int(big * 0.35)}")
    return f


def _kenburns(src: Path, out: Path, camera: str, w: int, h: int, length: float, fps: int,
              overlays: list[str]) -> None:
    frames = int(round(length * fps))
    z, x, y = (e.format(N=max(frames - 1, 1)) for e in _MOVES[camera])
    up_w, up_h = w * 3, h * 3  # oversample so the slow move doesn't jitter
    vf = ",".join([_cover(up_w, up_h),
                   f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}",
                   *overlays, "format=yuv420p"])
    ffmpeg("-loop", "1", "-i", str(src), "-vf", vf, "-frames:v", str(frames),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(fps), str(out))


def _clip(src: Path, out: Path, w: int, h: int, length: float, fps: int, overlays: list[str]) -> None:
    trim = 0.25
    avail = max(duration(src) - trim, 0.5)
    slow = min(max(length / avail, 1.0), 1.6)  # slow at most 1.6x, then hold the last frame
    vf = ",".join([f"trim=start={trim}", "setpts=PTS-STARTPTS", f"setpts={slow:.4f}*PTS",
                   f"fps={fps}", _cover(w, h), f"tpad=stop_mode=clone:stop_duration={length}",
                   *overlays, "format=yuv420p"])
    ffmpeg("-i", str(src), "-vf", vf, "-t", f"{length:.3f}", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(fps), str(out))


def clip_for(shot: dict) -> Path | None:
    p = OUT / "clips" / f"{shot['id']}.mp4"
    return p if shot["render"] == "wan" and p.exists() else None


def build_segment(sb: dict, shot: dict, keyframe: Path, length: float, aspect: str) -> Path:
    w, h = ASPECTS[aspect]
    fps = sb["meta"]["fps"]
    clip = clip_for(shot)
    src = clip or keyframe
    overlays = _overlays(sb, shot, w, h, length)
    mode = "wan-clip" if clip else f"kenburns:{shot['camera']}"
    key = stable_hash(STAGE_VERSION["segments"], src, mode, length, overlays, aspect, fps,
                      sb["meta"]["title_am"] if shot.get("overlay_title") else "")
    name = f"{shot['id']}_{aspect}"
    out = cached_path("segments", name, key, "mp4")
    call = Call("segments", name, "ffmpeg", mode, {"length": length, "src": str(src.relative_to(ROOT))})
    if out.exists():
        log_cache_hit(call, out)
        return out
    t0 = time.time()
    if clip:
        _clip(clip, out, w, h, length, fps, overlays)
    else:
        _kenburns(keyframe, out, shot["camera"], w, h, length, fps, overlays)
    log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out))
    prune("segments", name, out)
    return out


def end_card(sb: dict, aspect: str, length: float) -> Path:
    w, h = ASPECTS[aspect]
    fps = sb["meta"]["fps"]
    lines = sb["meta"].get("end_card") or ["Made with AI"]
    key = stable_hash(STAGE_VERSION["segments"], lines, aspect, length, fps)
    name = f"endcard_{aspect}"
    out = cached_path("segments", name, key, "mp4")
    call = Call("segments", name, "ffmpeg", "drawtext-endcard", {"lines": lines})
    if out.exists():
        log_cache_hit(call, out)
        return out
    t0 = time.time()
    big = int(min(w, h) * 0.07)
    small = int(min(w, h) * 0.028)
    filters = []
    y = h * 0.38
    (OUT / "segments").mkdir(parents=True, exist_ok=True)
    for i, line in enumerate(lines):
        tf = OUT / "segments" / f"endcard_{i}.txt"
        tf.write_text(line, encoding="utf-8")
        fs = big if i == 0 else small
        filters.append(f"drawtext=fontfile={fq(FONT_LATIN)}:textfile={fq(tf)}:fontsize={fs}:fontcolor=white:"
                       f"x=(w-tw)/2:y={int(y)}")
        y += fs * (1.9 if i == 0 else 1.7)
    filters += ["fade=t=in:st=0:d=0.6", "format=yuv420p"]
    ffmpeg("-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={length}:r={fps}",
           "-vf", ",".join(filters), "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out))
    log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out))
    prune("segments", name, out)
    return out


def keyframe_paths() -> dict[str, Path]:
    m = OUT / "keyframes" / "manifest.json"
    if not m.exists():
        raise SystemExit("no keyframes yet: run `make keyframes` first")
    return {k: ROOT / v for k, v in json.loads(m.read_text()).items()}
