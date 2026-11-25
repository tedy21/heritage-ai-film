"""Shot timing is driven by the narration (professionals cut picture to the
voice track): each shot lasts max(storyboard duration_s, lead + narration + tail).
"""
from __future__ import annotations

import json

from .common import OUT

LEAD_S = 0.6        # picture before the voice starts
FIRST_LEAD_S = 1.5  # let the score establish before the very first word
TAIL_S = 0.9   # breath after the voice ends
END_CARD_S = 3.5


def compute(sb: dict) -> dict:
    manifest_path = OUT / "narration" / "manifest.json"
    narr = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    t = 0.0
    shots = []
    for i, s in enumerate(sb["shots"]):
        n = narr.get(s["id"], {})
        nd = float(n.get("duration_s") or 0.0)
        lead = FIRST_LEAD_S if i == 0 else LEAD_S
        length = max(float(s["duration_s"]), lead + nd + TAIL_S if nd else 0.0)
        length = round(length * sb["meta"]["fps"]) / sb["meta"]["fps"]  # whole frames
        shots.append({"id": s["id"], "start": round(t, 3), "length": length,
                      "narration": n.get("path"), "narration_start": round(t + lead, 3),
                      "narration_len": nd})
        t += length
    return {"shots": shots, "end_card_start": round(t, 3), "end_card_len": END_CARD_S,
            "total": round(t + END_CARD_S, 3)}


def save(tl: dict) -> None:
    (OUT / "final").mkdir(parents=True, exist_ok=True)
    (OUT / "final" / "timeline.json").write_text(json.dumps(tl, indent=2))
