"""List-price equivalents used to turn free-tier usage into a cost estimate.

We pay nothing (free tiers), but COSTS.md reports what the same run would cost
at list price. These numbers are ESTIMATES copied from public pricing pages;
check them before quoting and update the `checked` date. Each entry says what
it is based on so a reader can verify it.
"""
checked = "2026-11-25 (to verify against current pricing pages)"

# Gemini TTS: audio output billed per token; ~25 audio tokens per second.
GEMINI_TTS_USD_PER_M_OUTPUT_TOKENS = 10.0
GEMINI_TTS_TOKENS_PER_AUDIO_SECOND = 25
# Gemini Flash text: per 1M tokens (input, output)
GEMINI_TEXT_USD_PER_M_IN = 0.30
GEMINI_TEXT_USD_PER_M_OUT = 2.50
# Cloudflare Workers AI FLUX image (approx. per 1024px image incl. steps)
CF_FLUX_USD_PER_IMAGE = {"flux-1-schnell": 0.0011, "flux-2-klein-4b": 0.0015}
# Cloud GPU rental comparable to a Kaggle/Colab T4 (on-demand, per hour)
T4_USD_PER_HOUR = 0.35


def tts_cost(audio_seconds: float) -> float:
    return audio_seconds * GEMINI_TTS_TOKENS_PER_AUDIO_SECOND * GEMINI_TTS_USD_PER_M_OUTPUT_TOKENS / 1e6


def text_cost(tokens_in: int, tokens_out: int) -> float:
    return tokens_in * GEMINI_TEXT_USD_PER_M_IN / 1e6 + tokens_out * GEMINI_TEXT_USD_PER_M_OUT / 1e6


def image_cost(model: str) -> float:
    for k, v in CF_FLUX_USD_PER_IMAGE.items():
        if k in model:
            return v
    return 0.0015


def gpu_cost(gpu_seconds: float) -> float:
    return gpu_seconds / 3600 * T4_USD_PER_HOUR
