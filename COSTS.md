# COSTS — measured latency, GPU minutes, list-price equivalent

Everything runs on free tiers, so the actual cost is **$0**. The table below comes from `runs.jsonl` via `make costs`. List-price equivalents use the rates in `pipeline/pricing.py`, which are estimates to verify against the current pricing pages.

## Free-tier limits found (fill in from the smoke test and dashboards)
| Provider | What I found on 25 Nov 2026 | Hit it? |
|---|---|---|
| Gemini API (text + TTS) | Smoke test 25 Nov: TTS `gemini-3.8-flash-tts` 3.2–4.2 s per short line; text `gemini-3.8-flash` 503 "high demand" (twice), `gemini-3.5-flash` 2.0 s. Listing models took 30 s once. _TODO: RPM/RPD from AI Studio_ | 503 overload (not quota) |
| Cloudflare Workers AI | Smoke test 25 Nov (512×512): FLUX.1 schnell 2.3 s, FLUX.2 klein 4B 5.3–9.2 s. _TODO: daily free neurons used_ | No |
| Kaggle GPU | 30 h/week shown; 00:35 used after ACE-Step setup + 2 runs. Working disk 19.5 GiB (ACE-Step env + models filled 17.2 GiB) | Disk nearly |

## Per-stage measurements
_Paste `make costs` output here after the final run._

## Frontier comparison
No frontier lane access (Nano Banana / Omni Flash / Lyria are behind paid billing). _If an org key is shared, run E-frontier on one shot and record cost, latency and the blind preference test._
