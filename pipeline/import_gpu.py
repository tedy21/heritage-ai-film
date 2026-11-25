"""Import the timings.json written by the Kaggle notebooks into runs.jsonl, so
GPU calls are logged like every other model call (one line per call).

  python -m pipeline.import_gpu outputs/clips/timings.json outputs/music/candidates/timings.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import pricing
from .common import RUNS, RUN_ID


def main() -> None:
    seen = set()
    if RUNS.exists():
        for line in RUNS.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("imported"):
                seen.add((r["stage"], r["item"], r.get("seed"), r["latency_s"]))
    n = 0
    with open(RUNS, "a", encoding="utf-8") as f:
        for path in sys.argv[1:]:
            for r in json.loads(Path(path).read_text()):
                k = (r["stage"], r["item"], r.get("seed"), r["latency_s"])
                if k in seen:
                    continue
                r.update({"run_id": RUN_ID, "imported": True, "cache_hit": False,
                          "cost_usd_equiv": round(pricing.gpu_cost(r.get("gpu_s", 0)), 5)})
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"imported {n} GPU call records into runs.jsonl")


if __name__ == "__main__":
    main()
