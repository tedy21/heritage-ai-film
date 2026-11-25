"""Phase 1 smoke test: call every hosted provider once and log latency to
runs.jsonl, so we learn early what works (and which model ids exist).

  python -m pipeline.smoke_test
"""
from __future__ import annotations

import os
import time

from .common import OUT, Call, load_env, load_storyboard, log_event, with_retries


def main() -> None:
    load_env()
    sb = load_storyboard()
    models = sb["meta"]["models"]
    out = OUT / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    results = {}

    if os.environ.get("GEMINI_API_KEY"):
        from . import gemini
        t0 = time.time()
        try:
            names = gemini.list_models()
            log_event(Call("smoke", "gemini-list", "gemini", "models.list", {}), status="ok",
                      latency_s=time.time() - t0, cache_hit=False, n_models=len(names))
            tts_like = [n for n in names if "tts" in n]
            flash = [n for n in names if "flash" in n and "tts" not in n]
            print("  gemini models with 'tts':", tts_like)
            print("  gemini flash text models:", flash[:12])
            for want, pool in (("text", flash), ("tts", tts_like)):
                if models[want] not in names:
                    print(f"  !! storyboard meta.models.{want}={models[want]} not offered; "
                          f"candidates: {pool[:5]}")
        except Exception as e:
            results["gemini-list"] = repr(e)
        try:
            text, _ = with_retries(Call("smoke", "gemini-text", "gemini", models["text"], {"prompt": "hello"}),
                                   lambda: gemini.generate_text(models["text"], "Reply with the single Amharic word for 'lake'."))
            results["gemini-text"] = text.strip()
        except Exception as e:
            results["gemini-text"] = f"FAILED {e!r}"
        try:
            from .narration import _write_wav
            pcm, rate = with_retries(Call("smoke", "gemini-tts", "gemini", models["tts"], {"voice": "Charon"}),
                                     lambda: gemini.tts(models["tts"], "ሰላም። ይህ ሙከራ ነው።", "Charon"))
            _write_wav(out / "tts_smoke.wav", pcm, rate)
            results["gemini-tts"] = f"ok {len(pcm) / 2 / rate:.1f}s audio at {rate} Hz"
        except Exception as e:
            results["gemini-tts"] = f"FAILED {e!r}"
    else:
        results["gemini"] = "skipped: GEMINI_API_KEY not set"

    if os.environ.get("CF_ACCOUNT_ID") and os.environ.get("CF_API_TOKEN"):
        from . import cloudflare
        for m in (models["image_fallback"], models["image"]):
            try:
                img = with_retries(Call("smoke", "cf-image", "cloudflare", m, {"size": "512x512"}, 1),
                                   lambda m=m: cloudflare.generate(m, "calm lake at sunrise, photograph", seed=1,
                                                                   width=512, height=512))
                (out / f"{m.split('/')[-1]}.jpg").write_bytes(img)
                results[m] = f"ok {len(img) // 1024} KB"
            except Exception as e:
                results[m] = f"FAILED {e!r}"
    else:
        results["cloudflare"] = "skipped: CF_ACCOUNT_ID / CF_API_TOKEN not set"

    print("\nsmoke test results:")
    for k, v in results.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
