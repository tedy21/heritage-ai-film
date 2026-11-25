"""`make validate`: schema + the brief's rules, with a readable report.

  python -m pipeline.validate [storyboard.json] [--strict]
Exit code 1 on any ERROR (or any WARNING with --strict).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import rules
from .common import SCHEMA, STORYBOARD


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    path = Path(args[0]) if args else STORYBOARD
    import jsonschema

    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema_errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    print(f"Validating {path.name}")
    print(f"  1. Schema ({SCHEMA.name}): " + ("OK" if not schema_errs else f"{len(schema_errs)} error(s)"))
    for e in schema_errs:
        print(f"     ERROR   {'/'.join(map(str, e.path)) or '(root)'}: {e.message}")
    if schema_errs:
        sys.exit(1)  # rules assume a well-shaped file

    findings = rules.check(data)
    n_err = len(rules.errors(findings))
    n_warn = len(findings) - n_err
    print(f"  2. Rules from the brief: {n_err} error(s), {n_warn} warning(s)")
    for f in sorted(findings, key=lambda x: (x.level != "ERROR", x.where)):
        print(f"     {f}")

    shots = data["shots"]
    words = sum(len(s["narration"].split()) for s in shots)
    planned = sum(s["duration_s"] for s in shots) + rules.END_CARD_S
    print(f"  Summary: {len(shots)} shots, {words} narration words, planned {planned:.0f}s incl. end card, "
          f"{sum(s['era'] == 'reconstruction' for s in shots)} reconstruction shot(s)")
    if n_err or (strict and n_warn):
        sys.exit(1)
    print("  RESULT: valid" + (" (with warnings)" if n_warn else ""))


if __name__ == "__main__":
    main()
