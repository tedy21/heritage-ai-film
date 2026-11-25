"""Stage: references + keyframes.

1. References first (practice: lock the look before shots). Each reference
   gets N candidate images (seed, seed+1, ...); `chosen` in the storyboard
   picks the golden one.
2. Each shot's keyframe is generated with the style block appended and, for
   present-day shots, conditioned on its golden reference image(s).

Cache key = hash(prompt + blocks + model + seed + reference image bytes), so
editing one shot's image_prompt regenerates exactly one keyframe.
Fallback: if the primary model fails after retries, the fallback model is used
(text-only) and the switch is logged.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from . import pricing
from .common import (OUT, STAGE_VERSION, Call, cached_path, ffmpeg, load_env, load_storyboard,
                     log_cache_hit, log_event, offline, prune, require_env, selected_shots,
                     stable_hash, with_retries, FONT_LATIN)

SIZE = 1024  # square keyframes: centre-cropped later to 16:9 and 9:16


def _placeholder(out: Path, label: str, seed: int) -> None:
    hue = seed % 360
    ffmpeg("-f", "lavfi", "-i", f"gradients=s={SIZE}x{SIZE}:d=1:seed={seed}:speed=0.01",
           "-vf", f"hue=h={hue},drawtext=fontfile='{FONT_LATIN}':text='{label}':fontsize=64:"
                  f"fontcolor=white:x=(w-tw)/2:y=(h-th)/2",
           "-frames:v", "1", "-q:v", "3", str(out))


def _small_ref(src: Path) -> Path:
    """Reference images are sent at 512px to stay within input limits."""
    dst = src.with_name(src.stem + ".512.jpg")
    if not dst.exists():
        ffmpeg("-i", str(src), "-vf", "scale=512:512:force_original_aspect_ratio=decrease", "-q:v", "3", str(dst))
    return dst


def _generate(stage: str, item: str, prompt: str, seed: int, out: Path, models: dict,
              refs: list[Path]) -> None:
    if offline():
        call = Call(stage, item, "offline", "offline-placeholder", {"prompt": prompt[:120]}, seed)
        t0 = time.time()
        _placeholder(out, item, seed)
        log_event(call, status="ok", latency_s=time.time() - t0, cache_hit=False, output=str(out))
        return
    from . import cloudflare
    primary = models["image"]
    params = {"prompt": prompt, "size": f"{SIZE}x{SIZE}", "steps": 4,
              "refs": [str(r.relative_to(OUT.parent)) for r in refs]}
    try:
        data = with_retries(Call(stage, item, "cloudflare", primary, params, seed),
                            lambda: cloudflare.generate(primary, prompt, seed=seed, refs=refs),
                            cost_usd_equiv=pricing.image_cost(primary), output=out)
    except Exception as e:
        fb = models["image_fallback"]
        print(f"  [{stage}:{item}] primary failed ({e}); falling back to {fb}")
        params = {**params, "refs": [], "fallback_from": primary}
        data = with_retries(Call(stage, item, "cloudflare", fb, params, seed),
                            lambda: cloudflare.generate(fb, prompt, seed=seed),
                            cost_usd_equiv=pricing.image_cost(fb), output=out)
    out.write_bytes(data)


def build_refs(sb: dict) -> dict[str, Path]:
    """Returns {ref_id: path of chosen candidate}."""
    chosen: dict[str, Path] = {}
    style = sb["meta"]["style_block"]
    model = sb["meta"]["models"]["image"]
    for ref in sb["references"]:
        prompt = f"{ref['prompt']}, {style}"
        for i in range(ref.get("candidates", 1)):
            seed = ref["seed"] + i
            key = stable_hash(STAGE_VERSION["refs"], prompt, seed, "offline" if offline() else model)
            out = cached_path("refs", f"{ref['id']}-c{i}", key, "jpg")
            if out.exists():
                log_cache_hit(Call("refs", f"{ref['id']}-c{i}", "cloudflare", model, {}, seed), out)
            else:
                _generate("refs", f"{ref['id']}-c{i}", prompt, seed, out, sb["meta"]["models"], [])
                prune("refs", f"{ref['id']}-c{i}", out)
            if i == ref.get("chosen", 0):
                chosen[ref["id"]] = out
    return chosen


def build_keyframe(sb: dict, shot: dict, refs: dict[str, Path]) -> Path:
    m = sb["meta"]
    block = m["style_block"] if shot["era"] == "present" else m["reconstruction_block"]
    prompt = f"{shot['image_prompt']}, {block}"
    ref_paths = [_small_ref(refs[r]) for r in shot.get("refs", []) if r in refs]
    model = "offline" if offline() else m["models"]["image"]
    key = stable_hash(STAGE_VERSION["keyframes"], prompt, shot["seed"], model, *ref_paths)
    out = cached_path("keyframes", shot["id"], key, "jpg")
    if out.exists():
        log_cache_hit(Call("keyframes", shot["id"], "cloudflare", model, {}, shot["seed"]), out)
        return out
    _generate("keyframes", shot["id"], prompt, shot["seed"], out, m["models"], ref_paths)
    prune("keyframes", shot["id"], out)
    return out


def main() -> None:
    load_env()
    sb = load_storyboard()
    if not offline():
        require_env("CF_ACCOUNT_ID", "CF_API_TOKEN")
    print("references:")
    refs = build_refs(sb)
    print("keyframes:")
    manifest_path = OUT / "keyframes" / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failed = []
    for shot in selected_shots(sb):
        try:
            manifest[shot["id"]] = str(build_keyframe(sb, shot, refs).relative_to(OUT.parent))
        except Exception as e:
            print(f"  [keyframes:{shot['id']}] FAILED: {e}")
            failed.append(shot["id"])
    ids = {s["id"] for s in sb["shots"]}
    manifest = {k: v for k, v in manifest.items() if k in ids}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    if failed:
        sys.exit(f"keyframes failed for {failed}")


if __name__ == "__main__":
    main()
