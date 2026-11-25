"""Stage: English subtitles (SRT) timed to the measured narration.

Readability rules: at most 2 lines of ~40 characters per cue. Long lines are
split at sentence / clause boundaries and the narration window is shared
between cues in proportion to their length.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from .common import OUT

MAX_LINE = 40
MAX_CUE = 2 * MAX_LINE


def _chunks(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?:;])\s+", text.strip()) if p.strip()]
    out: list[str] = []
    for p in parts:
        out.extend(_balanced(p))
    return out


def _balanced(p: str) -> list[str]:
    """Split a sentence longer than one cue into near-equal pieces at word
    boundaries (prefer commas), so no cue ends up as a two-word orphan."""
    if len(p) <= MAX_CUE:
        return [p]
    n = -(-len(p) // MAX_CUE)
    target = len(p) / n
    words, pieces, cur = p.split(" "), [], ""
    for w in words:
        if cur and len(cur) >= target * 0.8 and (cur.endswith(",") or len(cur) + len(w) + 1 > target * 1.15) \
                and len(pieces) < n - 1:
            pieces.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    pieces.append(cur)
    return pieces


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def build_srt(sb: dict, tl: dict) -> Path:
    shots = {s["id"]: s for s in sb["shots"]}
    cues = []
    for t in tl["shots"]:
        text = shots[t["id"]]["subtitle_en"].strip()
        if not text:
            continue
        start = t["narration_start"]
        span = t["narration_len"] or (t["length"] - 1.0)
        end_limit = t["start"] + t["length"] - 0.1
        chunks = _chunks(text)
        total = sum(len(c) for c in chunks)
        cur = start
        for c in chunks:
            dur = span * len(c) / total
            end = min(cur + max(dur, 1.2), end_limit)
            cues.append((cur, end, "\n".join(textwrap.wrap(c, MAX_LINE))))
            cur = end
    out = OUT / "subs" / "subtitles_en.srt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cues, 1)),
                   encoding="utf-8")
    return out
