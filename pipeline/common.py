"""Shared plumbing for every stage: storyboard loading + validation, content-hash
caching, retries with backoff, and the runs.jsonl call log.

Every stage imports from here so the contract (storyboard.json) and the
evidence trail (runs.jsonl) are handled the same way everywhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"
OUT = ROOT / "outputs"
RUNS = ROOT / "runs.jsonl"
RUN_ID = os.environ.get("RUN_ID") or time.strftime("%Y%m%dT%H%M%S")

# Bump when a stage's code changes in a way that should invalidate its cache.
STAGE_VERSION = {
    "refs": 1,
    "keyframes": 1,
    "narration": 1,
    "music": 1,
    "segments": 1,
    "subtitles": 1,
    "assemble": 1,
}


# ---------------------------------------------------------------- env / config
def load_env() -> None:
    """Minimal .env loader (no dependency). Real env vars win over the file."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def offline() -> bool:
    """OFFLINE=1 replaces model calls with labelled placeholders so the
    plumbing (timing, assembly, caching) can be tested without any keys."""
    return os.environ.get("OFFLINE", "0") == "1"


def require_env(*names: str) -> dict[str, str]:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}. "
                 f"Copy .env.example to .env and fill them in (or run with OFFLINE=1).")
    return {n: os.environ[n] for n in names}


# ---------------------------------------------------------------- storyboard
def load_storyboard(path: Path = STORYBOARD) -> dict:
    """Load and validate the storyboard. Every stage calls this first, so a
    broken contract fails before any model is called."""
    import jsonschema

    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"  - {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors]
        sys.exit("storyboard.json failed schema validation:\n" + "\n".join(lines))
    _semantic_checks(data)
    return data


def _semantic_checks(sb: dict) -> None:
    """Rules from the brief that JSON Schema can't express (pipeline/rules.py).
    Errors stop the run before any model is called; warnings are left to
    `make validate`, so every stage doesn't repeat them."""
    from . import rules
    errs = rules.errors(rules.check(sb))
    if errs:
        sys.exit("storyboard.json breaks the brief's rules:\n" + "\n".join("  " + str(e) for e in errs)
                 + "\n(run `make validate` for details and warnings)")


# ---------------------------------------------------------------- hashing / cache
def stable_hash(*parts: Any) -> str:
    """sha256 over a canonical JSON encoding of the inputs (files by content)."""
    def enc(o: Any) -> str:  # Paths anywhere (even nested) hash by content
        if isinstance(o, Path):
            return "file:" + file_hash(o)
        raise TypeError(type(o))

    h = hashlib.sha256()
    for p in parts:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False, default=enc).encode())
    return h.hexdigest()[:16]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def cached_path(stage: str, name: str, key: str, ext: str) -> Path:
    """Outputs are named <name>-<key>.<ext>. If the file exists the inputs
    have not changed, so the stage can skip the (expensive) call."""
    d = OUT / stage
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}-{key}.{ext}"


def prune(stage: str, name: str, keep: Path) -> None:
    """Remove superseded cache entries for the same item (keeps outputs/ tidy)."""
    for p in (OUT / stage).glob(f"{name}-*"):
        if p.stem != keep.stem and p.is_file():  # keep e.g. <file>.json sidecars
            p.unlink()


# ---------------------------------------------------------------- logging
@dataclass
class Call:
    stage: str
    item: str
    provider: str
    model: str
    params: dict
    seed: int | None = None


def log_event(call: Call, *, status: str, latency_s: float, cache_hit: bool,
              attempts: int = 0, cost_usd_equiv: float = 0.0, gpu_s: float = 0.0,
              output: str | None = None, error: str | None = None, **extra) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "run_id": RUN_ID,
        "stage": call.stage,
        "item": call.item,
        "provider": call.provider,
        "model": call.model,
        "params": call.params,
        "seed": call.seed,
        "status": status,
        "cache_hit": cache_hit,
        "attempts": attempts,
        "latency_s": round(latency_s, 3),
        "gpu_s": round(gpu_s, 1),
        "cost_usd_equiv": round(cost_usd_equiv, 5),
        "output": str(Path(output).relative_to(ROOT)) if output and Path(output).is_absolute() else output,
    }
    if error:
        rec["error"] = error[:500]
    rec.update(extra)
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tag = "cache" if cache_hit else status
    print(f"  [{call.stage}:{call.item}] {tag} {call.model} {rec['latency_s']}s")


class RetryableError(Exception):
    """Raised for 429 / 5xx / timeouts: worth another attempt."""


def with_retries(call: Call, fn: Callable[[], Any], *, max_attempts: int = 3,
                 base_delay: float = 4.0, cost_usd_equiv: float = 0.0,
                 output: Path | None = None) -> Any:
    """Run fn() with exponential backoff on RetryableError. Logs exactly one
    runs.jsonl line for the call (success or final failure)."""
    t0 = time.time()
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = fn()
            log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False,
                      attempts=attempt, cost_usd_equiv=cost_usd_equiv,
                      output=str(output) if output else None)
            return result
        except RetryableError as e:
            last_err = e
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                print(f"  [{call.stage}:{call.item}] retryable error ({e}); retry in {delay:.0f}s")
                time.sleep(delay)
        except Exception as e:  # non-retryable: fail fast
            last_err = e
            break
    log_event(call, status="error", latency_s=time.time() - t0, cache_hit=False,
              attempts=attempt, error=repr(last_err))
    raise last_err  # type: ignore[misc]


class AllModelsFailed(RuntimeError):
    pass


def with_fallbacks(stage: str, item: str, provider: str, models: list[str], params: dict,
                   fn: Callable[[str], Any], *, seed: int | None = None,
                   cost_usd_equiv: float = 0.0, output: Path | None = None,
                   attempts_per_model: int = 2, base_delay: float = 4.0) -> tuple[Any, str]:
    """Try each model in order. Each model gets a short retry budget (for
    momentary 429/503s); if it still fails, move on to the next model instead
    of stopping the run (graceful degradation). Every attempt is logged; a
    success on a backup model carries `fallback_from` = the primary.
    Returns (result, model_that_succeeded)."""
    errors = []
    primary = models[0]
    for i, model in enumerate(models):
        last = i == len(models) - 1
        p = dict(params, fallback_from=primary) if i else dict(params)
        call = Call(stage, item, provider, model, p, seed)
        try:
            result = with_retries(call, lambda m=model: fn(m),
                                  max_attempts=attempts_per_model + (1 if last else 0),
                                  base_delay=base_delay, cost_usd_equiv=cost_usd_equiv, output=output)
            if i:
                print(f"  [{stage}:{item}] succeeded on fallback model {model} (primary {primary} failed)")
            return result, model
        except Exception as e:  # noqa: BLE001 - any failure -> next model
            errors.append(f"{model}: {str(e)[:160]}")
            if not last:
                print(f"  [{stage}:{item}] {model} failed; falling back to {models[i + 1]}")
    raise AllModelsFailed(f"{stage}:{item} failed on every model: " + " | ".join(errors))


def model_chain(models: dict, kind: str) -> list[str]:
    """Primary model followed by its fallbacks, de-duplicated, from the storyboard."""
    chain = [models[kind], *models.get(f"{kind}_fallbacks", [])]
    return list(dict.fromkeys(chain))


def log_cache_hit(call: Call, output: Path) -> None:
    log_event(call, status="ok", latency_s=0.0, cache_hit=True, output=str(output))


def raise_for_http(resp) -> None:
    """Map HTTP status codes onto retryable / fatal errors."""
    if resp.status_code == 429 or resp.status_code >= 500:
        raise RetryableError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")


# ---------------------------------------------------------------- media helpers
def run(cmd: list[str], quiet: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        tail = "\n".join(res.stderr.splitlines()[-25:])
        raise RuntimeError(f"command failed: {' '.join(cmd[:6])} ...\n{tail}")
    return res


def ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args])


def duration(path: Path) -> float:
    res = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)])
    return float(res.stdout.strip())


def shot_by_id(sb: dict, shot_id: str) -> dict:
    for s in sb["shots"]:
        if s["id"] == shot_id:
            return s
    sys.exit(f"unknown shot id {shot_id}")


def selected_shots(sb: dict) -> list[dict]:
    """SHOT=s03 limits a stage to one shot (used by `make shot ID=s03`)."""
    only = os.environ.get("SHOT")
    return [s for s in sb["shots"] if not only or s["id"] == only]


FONT_ETHIOPIC = "/usr/share/fonts/truetype/noto/NotoSerifEthiopic-Bold.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"


def find_font(preferred: str, fallbacks: tuple[str, ...] = ()) -> str:
    for p in (preferred, *fallbacks):
        if Path(p).exists():
            return p
    res = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans"], capture_output=True, text=True)
    return res.stdout.strip()
