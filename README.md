# Heritage AI Film — ጣና፡ በማዕበል ያልጠፋ ታሪክ
**Tana: A Story That Outlasted the Waves.** An 80-second documentary short about Lake Tana and its island monasteries, narrated in Amharic with English subtitles and an original score. It is generated end to end by a small code pipeline from one file, [`storyboard.json`](storyboard.json).

> 🎬 Vertical (9:16): _link_ · Horizontal (16:9): _link_ · Walkthrough: _link_ · Post: _link_

## Run it
```bash
git clone https://github.com/tedy21/heritage-ai-film && cd heritage-ai-film
cp .env.example .env          # add GEMINI_API_KEY, CF_ACCOUNT_ID, CF_API_TOKEN
make film                     # → outputs/final/tana_16x9.mp4 and tana_9x16.mp4
```
Requirements: Python 3.11+, FFmpeg with libass (`apt install ffmpeg`), and the Noto fonts (`fonts-noto-core`, which includes Noto Serif Ethiopic). No GPU is needed locally.

| Command | What it does |
|---|---|
| `make validate` | Check `storyboard.json` against [`schema/`](schema/storyboard.schema.json) |
| `make smoke` | Call each provider once; log latency to `runs.jsonl` |
| `make radio` | Phase 1 radio cut: narration + temp music on black |
| `make film` | Whole pipeline; re-runs regenerate only what changed |
| `make shot ID=s04` | Regenerate one shot's narration/keyframe, then re-assemble |
| `make offline` | Whole pipeline with labelled placeholders (no keys), to test plumbing |
| `make kaggle-input` / `make import-gpu` | Hand off to and back from the Kaggle GPU notebooks |
| `make costs` | Per-stage latency, GPU minutes and list-price table from `runs.jsonl` |

## What it does
1. **Narration:** Gemini TTS, one Amharic line per shot, measured. The measured lengths set the shot lengths.
2. **Keyframes:** FLUX on Cloudflare Workers AI. A golden reference sheet comes first, then every keyframe is conditioned on it with a shared style block.
3. **Moving shots:** Wan 2.2 TI2V-5B image-to-video on a free Kaggle T4 ([notebook](notebooks/wan22_i2v_kaggle.py)), with a Ken Burns move over the keyframe as the fallback.
4. **Music:** ACE-Step 1.5 instrumental candidates on Kaggle ([notebook](notebooks/acestep_kaggle.py)); one is chosen by ear under the narration.
5. **Assembly (FFmpeg):** ducking with sidechain compression, two-pass loudness normalisation to −14 LUFS, burned-in English subtitles, "AI reconstruction" tags on historical scenes, the AI end card, and both aspect ratios.

GPU work runs in notebooks because the free GPU lives on Kaggle. Their outputs are committed, so `make film` from a clean clone rebuilds the film without a GPU.

## What it costs
$0 on free tiers. The measured latency per stage and the list-price equivalent are in [COSTS.md](COSTS.md).

## Documents
[DESIGN.md](DESIGN.md) (audience, intent, user tests) · [ARCHITECTURE.md](ARCHITECTURE.md) (stages, contracts, caching, failures) · [EXPERIMENTS.md](EXPERIMENTS.md) · [FAILURES.md](FAILURES.md) · [COSTS.md](COSTS.md) · [ETHICS.md](ETHICS.md) (consent, licences, labelling)

**Made with AI.** Historical scenes are AI reconstructions, not photographs. See [ETHICS.md](ETHICS.md).
