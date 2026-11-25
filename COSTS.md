# COSTS — measured latency, GPU minutes, list-price equivalent

Everything runs on free tiers, so the actual cost is **$0**. The table below comes from `runs.jsonl` via `make costs`. List-price equivalents use the rates in `pipeline/pricing.py`, which are estimates to verify against the current pricing pages.

## Free-tier limits found (fill in from the smoke test and dashboards)
| Provider | What I found on 25 Nov 2026 | Hit it? |
|---|---|---|
| Gemini API (text + TTS) | _TODO: RPM / RPD shown in AI Studio_ | |
| Cloudflare Workers AI | _TODO: daily free neurons; images per day in practice_ | |
| Kaggle GPU | _TODO: weekly GPU hours shown_ | |

## Per-stage measurements
_Paste `make costs` output here after the final run._

## Frontier comparison
No frontier lane access (Nano Banana / Omni Flash / Lyria are behind paid billing). _If an org key is shared, run E-frontier on one shot and record cost, latency and the blind preference test._
