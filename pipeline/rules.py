"""Storyboard rules from the challenge specification ("The Heritage Short").

JSON Schema (schema/storyboard.schema.json) checks the *shape* of the file.
These rules check what the brief *asks for*, which a schema can't express.
Each rule names the part of the brief it comes from.

  ERROR   breaks a requirement or would break the pipeline -> the run stops
          before any model is called.
  WARNING goes against a tip / good practice in the brief -> printed only
          (make validate STRICT=1 treats warnings as errors).

Used by common.load_storyboard() (errors stop every stage) and by
`make validate` (prints everything).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILM_MIN_S, FILM_MAX_S = 60, 90          # brief: "a 60-90 second short film"
END_CARD_S = 3.5                          # matches timeline.END_CARD_S
SHOTS_MIN, SHOTS_MAX = 8, 12              # brief Phase 1.4: "eight to twelve shots"
SUB_LINE, SUB_LINES = 40, 2               # Appendix B: "at most two lines and about 40 characters per line"
MOTION_MAX_WORDS = 30                     # Appendix B: i2v prompt = motion + camera only
MIN_SHOT_SIZES = 3                        # Appendix B: "varying shot size helps the viewer"
TEXT_IN_IMAGE = re.compile(r"\b(sign|signage|caption|title text|written words|letters|inscription|readable)\b", re.I)
KEY_IN_CAPTION = re.compile(r"\b(\d{2,3}\s*bpm|[A-G](#|b)?\s*(major|minor))\b", re.I)


@dataclass
class Finding:
    level: str      # "ERROR" | "WARNING"
    where: str      # e.g. "shots[s03]"
    message: str
    source: str     # which part of the brief / which failure it comes from

    def __str__(self) -> str:
        return f"{self.level:7} {self.where}: {self.message}  [{self.source}]"


def check(sb: dict) -> list[Finding]:
    f: list[Finding] = []

    def err(where, msg, src):
        f.append(Finding("ERROR", where, msg, src))

    def warn(where, msg, src):
        f.append(Finding("WARNING", where, msg, src))

    shots = sb["shots"]
    ids = [s["id"] for s in shots]

    # ---- structure & contract integrity -------------------------------
    if len(ids) != len(set(ids)):
        err("shots", "shot ids are not unique", "contract")
    expected = [f"s{i:02}" for i in range(1, len(shots) + 1)]
    if ids != expected:
        err("shots", f"shot ids must run s01..s{len(shots):02} in order (got {', '.join(ids)})", "contract")
    if not SHOTS_MIN <= len(shots) <= SHOTS_MAX:
        err("shots", f"{len(shots)} shots; the brief asks for {SHOTS_MIN}-{SHOTS_MAX}", "Phase 1.4")

    # ---- length -------------------------------------------------------
    planned = sum(s["duration_s"] for s in shots) + END_CARD_S
    if planned > FILM_MAX_S:
        err("shots[].duration_s", f"planned length {planned:.0f}s (incl. end card) exceeds {FILM_MAX_S}s", "brief: 60-90 s")
    elif planned < FILM_MIN_S:
        warn("shots[].duration_s", f"planned length {planned:.0f}s is under {FILM_MIN_S}s "
             "(narration may still stretch it; check after `make radio`)", "brief: 60-90 s")

    # ---- every shot has a reason; narration <-> subtitles -------------
    for s in shots:
        w = f"shots[{s['id']}]"
        if len(s["reason"].split()) < 5:
            err(w, "reason is too short to state why the shot exists", "Design thinking: every shot has a stated reason")
        if s["narration"].strip() and not s["subtitle_en"].strip():
            err(w, "has narration but no English subtitle", "brief: English subtitles")
        if s["subtitle_en"].strip() and not s["narration"].strip():
            warn(w, "has a subtitle but no narration (nothing is spoken)", "brief: accurate subtitles")
        long_words = [x for x in s["subtitle_en"].split() if len(x) > SUB_LINE]
        if long_words:
            err(w, f"subtitle word longer than {SUB_LINE} chars cannot be wrapped: {long_words[0][:20]}...", "Appendix B: subtitles")
        if len(s["subtitle_en"]) > 4 * SUB_LINE * SUB_LINES:
            warn(w, f"subtitle is {len(s['subtitle_en'])} chars (> {4 * SUB_LINE * SUB_LINES}); "
                 "it will flash through many cues - shorten it", "Appendix B: subtitles")

    # ---- images & motion ----------------------------------------------
    ref_ids = {r["id"] for r in sb["references"]}
    used_refs = set()
    for s in shots:
        w = f"shots[{s['id']}]"
        for r in s.get("refs", []):
            used_refs.add(r)
            if r not in ref_ids:
                err(w, f"refers to unknown reference {r}", "contract")
        if s["era"] == "present" and not s.get("refs"):
            warn(w, "present-day shot has no reference image (consistency)", "Phase 2.1: reference sheet first")
        m = TEXT_IN_IMAGE.search(s["image_prompt"])
        if m and not re.search(r"\b(no|without|blurred|out of focus)\b[^,]*" + re.escape(m.group(0)), s["image_prompt"], re.I):
            warn(w, f"image prompt asks for '{m.group(0)}'; text inside images comes out garbled", "Appendix B: add text in code")
        if s["render"] == "wan" and not s["motion_prompt"].strip():
            err(w, "render=wan needs a motion_prompt", "Phase 2.2")
        if len(s["motion_prompt"].split()) > MOTION_MAX_WORDS:
            warn(w, f"motion prompt has {len(s['motion_prompt'].split())} words; describe only motion + camera",
                 "Appendix B: don't re-describe the subject in i2v")
    for r in sb["references"]:
        if r["id"] not in used_refs:
            warn(f"references[{r['id']}]", "reference is never used by any shot", "contract")
        if r.get("chosen", 0) >= r.get("candidates", 1):
            err(f"references[{r['id']}]", "chosen index is out of range", "contract")
    if len({s["shot_size"] for s in shots}) < MIN_SHOT_SIZES:
        warn("shots[].shot_size", f"fewer than {MIN_SHOT_SIZES} different shot sizes", "Appendix B: vary shot size")
    seeds = [s["seed"] for s in shots]
    if len(seeds) != len(set(seeds)):
        warn("shots[].seed", "two shots share a seed (fine for A/B tests, odd otherwise)", "reproducibility")

    # ---- AI labelling & ethics -----------------------------------------
    card = " ".join(sb["meta"].get("end_card") or [])
    if "ai" not in card.lower().split() and "AI" not in card:
        err("meta.end_card", "end card must say the film was made with AI", "brief: visible AI end card")
    if any(s["era"] == "reconstruction" for s in shots) and "reconstruct" not in card.lower():
        warn("meta.end_card", "there are reconstruction shots but the end card doesn't mention reconstructions",
             "ETHICS: labelling plan")
    if sb["meta"]["narration_voice"].get("style", "").strip():
        warn("meta.narration_voice.style", "a style instruction is sent to TTS and may be spoken aloud",
             "FAILURES F15")

    # ---- music ----------------------------------------------------------
    music = sb["music"]
    pos = {sid: i for i, sid in enumerate(ids)}
    covered = []
    for c in music["cues"]:
        for k in ("from_shot", "to_shot"):
            if c[k] not in pos:
                err(f"music.cues[{c['id']}]", f"{k}={c[k]} is not a shot id", "contract")
        if c["from_shot"] in pos and c["to_shot"] in pos:
            a, b = pos[c["from_shot"]], pos[c["to_shot"]]
            if a > b:
                err(f"music.cues[{c['id']}]", "from_shot comes after to_shot", "Appendix C: spotting")
            covered += list(range(a, b + 1))
    if sorted(covered) != list(range(len(shots))):
        missing = [ids[i] for i in range(len(shots)) if i not in covered]
        dup = sorted({ids[i] for i in covered if covered.count(i) > 1})
        err("music.cues", f"cues must cover every shot exactly once (missing: {missing or '-'}, overlapping: {dup or '-'})",
            "Appendix C: spotting")
    cap = music["caption"].lower()
    if "instrumental" not in cap:
        warn("music.caption", "caption doesn't say 'instrumental'; a score under narration should have no vocals",
             "Appendix B: write instrumental")
    if KEY_IN_CAPTION.search(music["caption"]):
        warn("music.caption", "tempo/key belong in the bpm/key fields, not the caption", "Appendix B: ACE-Step tips")
    if music.get("chosen") and not (ROOT / music["chosen"]).exists():
        err("music.chosen", f"file not found: {music['chosen']}", "contract")

    return f


def errors(findings: list[Finding]) -> list[Finding]:
    return [x for x in findings if x.level == "ERROR"]
