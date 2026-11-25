"""`make film`: validate -> narration -> keyframes -> music -> assemble.

Each stage is cached by a hash of its inputs, so a re-run only regenerates
what changed. GPU stages (Wan 2.2 clips, ACE-Step score) run on Kaggle via
notebooks/ and are picked up from outputs/clips and music.chosen when present;
without them the film still builds (Ken Burns + temp pad).
"""
from __future__ import annotations

import sys

from . import assemble, keyframes, narration
from .common import RUN_ID, load_env, load_storyboard


def main() -> None:
    load_env()
    load_storyboard()  # fail fast on a broken contract
    print(f"run {RUN_ID}")
    narration.main()
    keyframes.main()
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    assemble.main()


if __name__ == "__main__":
    main()
