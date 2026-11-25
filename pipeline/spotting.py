"""Spotting: turn the storyboard's music cues (shot ranges + intent) into
timecoded spotting notes from the *measured* narration timeline, the way a
director and composer spot a film after watching it.

  python -m pipeline.spotting   -> outputs/music/spotting_notes.md

Also provides cue_gain_expr(): a piecewise-linear gain curve (dB) with ramps
between cues, used by assemble.build_mix to shape one score track so it
follows the film's arc (quiet open, darker middle, warmer close).
"""
from __future__ import annotations

from .common import OUT, load_storyboard
from . import timeline

RAMP_S = 1.5
OUTRO_SWELL_DB = 4.0  # when the last line ends, the score rises to carry the ending


def tc(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02}:{s:05.2f}"


def cue_times(sb: dict, tl: dict) -> list[dict]:
    shots = {s["id"]: s for s in tl["shots"]}
    out = []
    for c in sb["music"]["cues"]:
        a = shots[c["from_shot"]]["start"]
        b = shots[c["to_shot"]]["start"] + shots[c["to_shot"]]["length"]
        out.append({**c, "start": round(a, 2), "end": round(b, 2), "gain_db": c.get("gain_db", 0.0)})
    return out


def cue_gain_expr(sb: dict, tl: dict) -> str | None:
    """ffmpeg expression in t -> linear gain, or None if all cues are 0 dB."""
    cues = cue_times(sb, tl)
    pts = [(0.0, cues[0]["gain_db"])]
    for prev, nxt in zip(cues, cues[1:]):
        b = nxt["start"]
        pts += [(max(b - RAMP_S / 2, 0.0), prev["gain_db"]), (b + RAMP_S / 2, nxt["gain_db"])]
    # Outro: after the last spoken line, the music takes over instead of
    # leaving several seconds of near-silence (user test, F17).
    voiced = [s for s in tl["shots"] if s["narration_len"]]
    last_end = voiced[-1]["narration_start"] + voiced[-1]["narration_len"] if voiced else tl["total"]
    g_end = cues[-1]["gain_db"]
    if last_end + RAMP_S < tl["total"]:
        pts += [(last_end + 0.3, g_end), (last_end + 0.3 + RAMP_S * 2, g_end + OUTRO_SWELL_DB)]
        g_end += OUTRO_SWELL_DB
    pts.append((tl["total"] + 10, g_end))
    pts = sorted(pts)
    expr = f"{pts[-1][1]}"
    for (t0, g0), (t1, g1) in reversed(list(zip(pts, pts[1:]))):
        seg = f"{g0}+({g1}-({g0}))*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f}"
        expr = f"if(lt(t,{t1:.3f}),{seg},{expr})"
    return f"pow(10,({expr})/20)"


def write_notes(sb: dict, tl: dict) -> str:
    rows = ["| Cue | In | Out | Length | Shots | Gain | What it should do |", "|---|---|---|---|---|---|---|"]
    for c in cue_times(sb, tl):
        rows.append(f"| {c['id']} | {tc(c['start'])} | {tc(c['end'])} | {c['end'] - c['start']:.1f}s | "
                    f"{c['from_shot']}–{c['to_shot']} | {c['gain_db']:+.0f} dB | {c['intent']} |")
    md = ("# Spotting notes (generated from the measured narration timeline)\n\n"
          f"Film length {tc(tl['total'])} incl. {tl['end_card_len']}s end card. "
          f"Score: `{sb['music'].get('chosen') or 'temp pad (no score chosen yet)'}`, "
          f"{sb['music']['bpm']} BPM, {sb['music']['key']}. Gain changes ramp over {RAMP_S}s; "
          "the score is also ducked under every narration line.\n\n" + "\n".join(rows) + "\n")
    path = OUT / "music" / "spotting_notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    return md


if __name__ == "__main__":
    sb = load_storyboard()
    print(write_notes(sb, timeline.compute(sb)))
