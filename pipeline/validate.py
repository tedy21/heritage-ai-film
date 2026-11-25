"""`make validate`: schema + semantic checks, plus a few budget warnings."""
from __future__ import annotations

import sys
from pathlib import Path

from .common import STORYBOARD, load_storyboard


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else STORYBOARD
    sb = load_storyboard(path)
    shots = sb["shots"]
    words = sum(len(s["narration"].split()) for s in shots)
    min_len = sum(s["duration_s"] for s in shots)
    print(f"{path.name}: valid. {len(shots)} shots, {words} narration words, "
          f">= {min_len:.0f}s before narration timing")
    for s in shots:
        if len(s["subtitle_en"]) > 120:
            print(f"  note: {s['id']} subtitle is {len(s['subtitle_en'])} chars (will be split into several cues)")


if __name__ == "__main__":
    main()
