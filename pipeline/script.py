"""Stage: script check (Gemini text). Back-translates every Amharic narration
line to English in ONE request and compares it with the storyboard's English
subtitle, so subtitle accuracy is checked by evidence, not by assumption.

It never edits storyboard.json: a person decides what to change.

  python -m pipeline.script   -> outputs/script/review.json + review.md
Cached by hash(narration + subtitles + model chain): re-runs cost nothing until
the script changes.
"""
from __future__ import annotations

import json
import re

from . import pricing
from .common import (OUT, Call, load_env, load_storyboard, log_cache_hit, model_chain,
                     require_env, stable_hash, with_fallbacks)

PROMPT = """You are checking subtitles for an Amharic documentary.
For each numbered Amharic line, give:
- "back_translation": a faithful, literal English translation of the Amharic (not of the subtitle)
- "match": true if the given English subtitle has the same meaning, false if meaning differs
- "note": one short sentence on any difference, factual concern, or unnatural Amharic; "" if none
Return ONLY a JSON array of objects with keys id, back_translation, match, note.

Lines:
"""


def main() -> None:
    load_env()
    sb = load_storyboard()
    require_env("GEMINI_API_KEY")
    from . import gemini
    lines = [s for s in sb["shots"] if s["narration"].strip()]
    chain = model_chain(sb["meta"]["models"], "text")
    key = stable_hash("script-check-v1", [(s["id"], s["narration"], s["subtitle_en"]) for s in lines], chain)
    out_dir = OUT / "script"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "review.json"
    if out.exists() and json.loads(out.read_text()).get("key") == key:
        log_cache_hit(Call("script", "back-translation", "gemini", chain[0], {}), out)
        print((out_dir / "review.md").read_text(encoding="utf-8"))
        return

    body = PROMPT + "\n".join(f'{s["id"]}: AMHARIC: {s["narration"]}\n     SUBTITLE: {s["subtitle_en"]}' for s in lines)

    def go(model_id: str):
        text, usage = gemini.generate_text(model_id, body, temperature=0.0)
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            raise RuntimeError(f"no JSON array in reply: {text[:200]}")
        return json.loads(m.group(0)), usage

    (rows, usage), used = with_fallbacks(
        "script", "back-translation", "gemini", chain, {"lines": len(lines), "temperature": 0.0}, go,
        cost_usd_equiv=pricing.text_cost(len(body) // 3, 1500), output=out)
    out.write_text(json.dumps({"key": key, "model": used, "rows": rows}, indent=2, ensure_ascii=False))

    subs = {s["id"]: s["subtitle_en"] for s in lines}
    md = [f"# Script check: Amharic → English back-translation ({used})", "",
          "| Shot | Match | Back-translation of the Amharic | Current subtitle | Note |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r.get('id')} | {'✅' if r.get('match') else '❌'} | {r.get('back_translation', '')} | "
                  f"{subs.get(r.get('id'), '')} | {r.get('note', '')} |")
    bad = [r.get("id") for r in rows if not r.get("match")]
    md += ["", f"**{len(rows) - len(bad)}/{len(rows)} lines match.**" + (f" Review: {', '.join(bad)}." if bad else "")]
    (out_dir / "review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
