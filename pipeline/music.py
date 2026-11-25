"""Stage: music. Uses the chosen ACE-Step score (music.chosen in the
storyboard, generated on Kaggle by notebooks/acestep_kaggle.py). Until a score
is chosen, a clearly-labelled temp pad is synthesised with FFmpeg so the radio
cut and rough cuts have something to sit on.
"""
from __future__ import annotations

import time
from pathlib import Path

from .common import (ROOT, STAGE_VERSION, Call, cached_path, ffmpeg, load_storyboard,
                     log_cache_hit, log_event, stable_hash)

# D minor pad (D3 F3 A3 D4) with slow swells; a placeholder, not the score.
_PAD = ("aevalsrc=exprs='"
        "0.10*sin(2*PI*146.83*t)*(0.6+0.4*sin(2*PI*0.031*t))+"
        "0.07*sin(2*PI*174.61*t)*(0.6+0.4*sin(2*PI*0.043*t+1))+"
        "0.07*sin(2*PI*220.00*t)*(0.6+0.4*sin(2*PI*0.037*t+2))+"
        "0.05*sin(2*PI*293.66*t)*(0.5+0.5*sin(2*PI*0.029*t+3))'"
        ":s=48000:d=120")


def music_track(sb: dict) -> Path:
    chosen = sb["music"].get("chosen")
    if chosen:
        p = ROOT / chosen
        if not p.exists():
            raise SystemExit(f"music.chosen points to a missing file: {chosen}")
        log_cache_hit(Call("music", "score", "ace-step", sb["meta"]["models"].get("music", "ace-step"),
                           {"file": chosen}), p)
        return p
    key = stable_hash(STAGE_VERSION["music"], _PAD)
    out = cached_path("music", "temp_pad", key, "wav")
    call = Call("music", "temp_pad", "ffmpeg", "aevalsrc-temp-pad", {"note": "placeholder until ACE-Step score is chosen"})
    if out.exists():
        log_cache_hit(call, out)
        return out
    t0 = time.time()
    ffmpeg("-f", "lavfi", "-i", _PAD, "-af",
           "lowpass=f=1800,aecho=0.8:0.7:120|240:0.3|0.2,aformat=channel_layouts=stereo", str(out))
    log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out))
    return out


if __name__ == "__main__":
    print("music:", music_track(load_storyboard()))
