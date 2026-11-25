"""Summarise runs.jsonl per stage: calls, cache hits, failures, latency,
GPU minutes and list-price equivalent. `make costs` pastes this into COSTS.md."""
from __future__ import annotations

import json
from collections import defaultdict

from .common import RUNS


def main() -> None:
    if not RUNS.exists():
        print("no runs.jsonl yet")
        return
    agg = defaultdict(lambda: {"calls": 0, "hits": 0, "errors": 0, "lat": [], "gpu": 0.0, "usd": 0.0, "models": set()})
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        a = agg[r["stage"]]
        if r.get("cache_hit"):
            a["hits"] += 1
            continue
        a["calls"] += 1
        a["errors"] += r["status"] != "ok"
        a["lat"].append(r["latency_s"])
        a["gpu"] += r.get("gpu_s", 0)
        a["usd"] += r.get("cost_usd_equiv", 0)
        a["models"].add(r["model"])
    print("| stage | calls | cache hits | errors | median latency s | total latency s | GPU min | list-price USD | models |")
    print("|---|---|---|---|---|---|---|---|---|")
    tot = 0.0
    for stage, a in agg.items():
        lat = sorted(a["lat"])
        med = lat[len(lat) // 2] if lat else 0
        tot += a["usd"]
        print(f"| {stage} | {a['calls']} | {a['hits']} | {a['errors']} | {med:.1f} | {sum(lat):.0f} | "
              f"{a['gpu'] / 60:.1f} | {a['usd']:.4f} | {', '.join(sorted(a['models']))} |")
    print(f"\nTotal list-price equivalent: ${tot:.4f}")


if __name__ == "__main__":
    main()
