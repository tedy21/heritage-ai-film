"""`make status`: check the repository against the challenge rubric.

Each check maps to a graded criterion and looks for *written evidence* (the
graders read code, text and logs, not media). Run it before every commit and
before submitting; each line says what to do about anything not green.

  ✅ done   ⚠️ partly / needs a human step   ❌ missing
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

from .common import OUT, ROOT, RUNS

OK, PART, MISS = "✅", "⚠️ ", "❌"


def _read(name: str) -> str:
    p = ROOT / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _filled_rows(md: str, heading: str) -> int:
    """Count table rows with real content under a DESIGN.md test heading."""
    if heading not in md:
        return 0
    section = md.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = [r for r in section.splitlines() if r.startswith("|") and not r.startswith("|---")][1:]
    return sum(1 for r in rows if len(re.sub(r"[|\s]", "", r)) > 10)


def _duration(path) -> float:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def checks() -> list[tuple[str, str, str, str]]:
    """(criterion, status, check, next action)"""
    out = []
    add = lambda c, ok, what, todo="": out.append((c, ok, what, todo))  # noqa: E731

    # --- Software engineering & reproducibility (20)
    c = "SW eng (20)"
    r = subprocess.run([sys.executable, "-m", "pipeline.validate"], cwd=ROOT, capture_output=True, text=True)
    add(c, OK if r.returncode == 0 else MISS, "storyboard passes schema + brief rules", "fix `make validate` errors")
    runs = [json.loads(line) for line in RUNS.read_text(encoding="utf-8").splitlines()] if RUNS.exists() else []
    stages = {x["stage"] for x in runs if not x.get("cache_hit")}
    need = {"narration", "keyframes", "music", "assemble"}
    add(c, OK if need <= stages else PART, f"runs.jsonl: {len(runs)} lines, stages logged: {', '.join(sorted(stages)) or '-'}",
        f"run the missing stages: {', '.join(sorted(need - stages))}" if not need <= stages else "")
    add(c, OK if any(x.get("cache_hit") for x in runs) else MISS, "caching evidence (cache-hit lines in runs.jsonl)")
    add(c, OK if any((x.get("attempts") or 0) > 1 for x in runs) else PART, "retries evidence (attempts > 1 logged)")
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    leak = [f for f in tracked if f == ".env"]
    secret_hit = subprocess.run(["git", "grep", "-lE", r"AIza[0-9A-Za-z_-]{20,}"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    add(c, OK if not leak and not secret_hit else MISS, "no secrets committed (.env untracked, no API keys in tracked files)",
        "remove the secret from git history" if leak or secret_hit else "")
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, capture_output=True, text=True)
    add(c, OK if tests.returncode == 0 else MISS, "unit tests pass (`make test`)", "fix failing tests")
    films = [OUT / "final" / "tana_16x9.mp4", OUT / "final" / "tana_9x16.mp4"]
    add(c, OK if all(f.exists() for f in films) else MISS, "`make film` has produced both aspect ratios",
        "generate keyframes, then `make film`")
    add(c, PART, "clean-clone run verified", "Step 12: git clone into a temp folder, add .env, `make film`")

    # --- Documentation (10)
    c = "Docs (10)"
    readme, arch = _read("README.md"), _read("ARCHITECTURE.md")
    add(c, OK if "make film" in readme else MISS, "README: one-command run")
    add(c, OK if all(k in arch.lower() for k in ("contract", "cach", "failure")) else PART, "ARCHITECTURE: contracts, caching, failure handling")
    add(c, OK if "_link_" not in readme else PART, "README film/walkthrough/post links filled", "add links at the end (Step 12)")

    # --- Design thinking (10)
    c = "Design (10)"
    design = _read("DESIGN.md")
    add(c, OK if "Who watches" in design and "feel" in design else MISS, "audience + intent written before generating")
    add(c, OK if "TODO (user" not in design else PART, "personal 'why this matters to me' written", "write 2-3 sentences in DESIGN.md")
    t1 = _filled_rows(design, "## User test 1")
    t2 = _filled_rows(design, "## User test 2")
    add(c, OK if t1 >= 3 else MISS, f"user test 1 (radio cut): {t1}/3 people recorded", "play radio_cut.mp4 to 3+ people")
    add(c, OK if t2 >= 3 else MISS, f"user test 2 (near-final): {t2}/3 people recorded", "Step 10")

    # --- Experiments (10)
    c = "Experiments (10)"
    rows = [r for r in _read("EXPERIMENTS.md").splitlines() if re.match(r"^\| E\d", r)]
    done = [r for r in rows if "_TODO" not in r]
    add(c, OK if len(done) >= 10 else (PART if done else MISS), f"{len(done)}/10 experiments with results ({len(rows)} listed)",
        "run the open experiments as their steps happen")
    add(c, OK if _read("storyboard.json") and json.loads(_read("storyboard.json"))["music"].get("chosen") else MISS,
        "score chosen and the reason written", "listen to the auditions, set music.chosen, log why (Step 7)")

    # --- Failures (10)
    c = "Failures (10)"
    n_fail = len(re.findall(r"^### F\d+", _read("FAILURES.md"), re.M))
    add(c, OK if n_fail >= 5 else PART, f"FAILURES.md: {n_fail} real blockers with tried/fixed")

    # --- Measurement (5)
    c = "Measurement (5)"
    costs = _read("COSTS.md")
    add(c, OK if "Generated by `make costs`" in costs else MISS, "per-stage latency/GPU/list-price table", "`make costs`")
    add(c, OK if any(x.get("gpu_s") for x in runs if x["stage"] == "clips") else PART, "Wan GPU minutes measured", "Step 8")
    add(c, PART, "frontier comparison", "only if an org key is shared; otherwise say so in COSTS.md (done)")

    # --- Consent, labelling, licences (5)
    c = "Ethics (5)"
    eth = _read("ETHICS.md")
    add(c, OK if "Consent record" in eth else MISS, "consent record (no real person shown/voiced)")
    add(c, OK if "Licences" in eth and "Labelling plan" in eth else MISS, "licences + labelling plan")

    # --- Report (30)
    c = "Report (30)"
    rep = next((p for p in ("REPORT.md", "REPORT.pdf", "report.pdf") if (ROOT / p).exists()), None)
    add(c, OK if rep else MISS, "report written (audience, hardest problem, practice that helped / didn't, ceiling work)",
        "Step 11")

    # --- Film (assignment 2)
    c = "Film (A2)"
    for f in films:
        d = _duration(f)
        add(c, OK if 60 <= d <= 90 else (MISS if not d else PART), f"{f.name}: {d:.1f}s (60-90 s)" if d else f"{f.name}: not built")
    review = OUT / "script" / "review.json"
    if review.exists():
        rows_r = json.loads(review.read_text(encoding="utf-8"))["rows"]
        bad = [r["id"] for r in rows_r if not r.get("match")]
        notes = [r["id"] for r in rows_r if r.get("note")]
        add(c, OK if not bad and not notes else PART,
            f"subtitle check: {len(rows_r) - len(bad)}/{len(rows_r)} match" + (f", notes on {', '.join(notes)}" if notes else ""),
            "review outputs/script/review.md" if notes or bad else "")
    else:
        add(c, MISS, "subtitle back-translation check", "`make script`")
    return out


def main() -> None:
    res = checks()
    width = max(len(r[2]) for r in res)
    cur = None
    for crit, st, what, todo in res:
        if crit != cur:
            print(f"\n{crit}")
            cur = crit
        print(f"  {st} {what.ljust(width)}" + (f"  → {todo}" if todo and st != OK else ""))
    n_ok = sum(r[1] == OK for r in res)
    print(f"\n{n_ok}/{len(res)} checks green.")


if __name__ == "__main__":
    main()
