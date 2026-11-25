# ARCHITECTURE

## One contract, five stages
```
                       schema/storyboard.schema.json
                                   │ validates (every stage, before any call)
                                   ▼
                            storyboard.json  ◄── the only thing a human edits
      ┌──────────────┬─────────────┼───────────────┬──────────────────┐
      ▼              ▼             ▼               ▼                  │
  narration      keyframes       clips           music                │
  Gemini TTS     refs → FLUX     Wan 2.2 (Kaggle) ACE-Step (Kaggle)    │
  outputs/       outputs/refs    outputs/clips   outputs/music        │
  narration/     outputs/keyframes                                    │
      │              │             │               │                  │
      └──────┬───────┴─────────────┴───────────────┘                  │
             ▼                                                        │
        assemble (FFmpeg, deterministic) ◄────────────────────────────┘
        timeline → segments (Ken Burns | clip) → subtitles → mix (duck + loudnorm) → export ×2
             ▼
        outputs/final/tana_16x9.mp4, tana_9x16.mp4        runs.jsonl ← one line per call, every stage
```

| Stage | Script | Reads from storyboard | Writes | Runs on |
|---|---|---|---|---|
| validate | `pipeline/validate.py` | everything | — | local |
| narration | `pipeline/narration.py` | `shots[].narration`, `meta.narration_voice`, `meta.models.tts` | `outputs/narration/<shot>-<hash>.wav`, `manifest.json` (measured durations) | Gemini API |
| keyframes | `pipeline/keyframes.py` | `references[]`, `shots[].image_prompt/era/refs/seed`, style blocks | `outputs/refs/…`, `outputs/keyframes/<shot>-<hash>.jpg`, `manifest.json` | Cloudflare Workers AI |
| clips | `notebooks/wan22_i2v_kaggle.py` | `shots[].motion_prompt/seed/render`, keyframes | `outputs/clips/<shot>.mp4`, `timings.json` | Kaggle T4 |
| music | `notebooks/acestep_kaggle.py`, `pipeline/music.py` | `music.caption/bpm/key/chosen` | `outputs/music/…` | Kaggle T4 / local temp pad |
| assemble | `pipeline/assemble.py` (+ `timeline.py`, `shots.py`, `subtitles.py`) | everything + all manifests | `outputs/segments/…`, `outputs/subs/subtitles_en.srt`, `outputs/final/*` | local FFmpeg |

`make film` = `pipeline/run.py` = validate → narration → keyframes → assemble (music is resolved inside assemble).
`make radio` = narration → assemble `--radio` (black picture, Phase 1 prototype).

## Contracts
- **storyboard.json** is validated twice before any model call: by JSON Schema (types, enums, 8–12 shots, required `reason` per shot), then by semantic checks in `common._semantic_checks` (unique ids, references exist, music cues point to real shots, narration has a subtitle).
- **Manifests** (`outputs/narration/manifest.json`, `outputs/keyframes/manifest.json`, `outputs/final/timeline.json`) are the hand-off between stages. Assembly reads only manifests and the storyboard, never a model.
- **GPU stages** live on Kaggle because that is where the free GPU is. Their contract is a file drop: `outputs/clips/<shot>.mp4` and `music.chosen`, plus `timings.json`, which `make import-gpu` appends to runs.jsonl.

## Caching: only what changed is regenerated
Every artefact is named `<item>-<key>.<ext>`, where `key = sha256(stage version, the exact inputs)[:16]`:

| Artefact | Key inputs |
|---|---|
| narration WAV | text, voice, style instruction, TTS model |
| reference image | prompt + style block, seed, model |
| keyframe | prompt + style/reconstruction block, seed, model, **bytes** of the reference images |
| segment | **bytes** of keyframe or clip, camera move, length, overlays, aspect, fps |
| mix | **bytes** of each narration WAV + offsets, music bytes, ducking, volume, length |
| final export | keys of segments + mix + subtitles |

If the file exists, the stage logs a `cache_hit: true` line and skips the work. Because downstream keys hash upstream **file contents**, a change propagates exactly as far as it matters. Measured (offline run): editing the narration of s04 re-ran 1 TTS call, 2 segments (s04 16:9 + 9:16), the mix and the 2 exports. Nothing else ran.
Old entries for the same item are pruned so `outputs/` holds only the current version. `STAGE_VERSION` in `common.py` invalidates a stage's cache when its code changes meaningfully.

## Failure handling
| Failure | Handling |
|---|---|
| Broken storyboard | Fails before any call, with the JSON path of every error |
| HTTP 429 / 5xx / timeout / empty TTS response | `with_retries`: exponential backoff (4 s, 8 s, 16 s…), max 3–4 attempts, one log line with `attempts` |
| HTTP 4xx (bad key, bad model id) | Fail fast (retrying will not help), logged with the error, then the next model in the chain |
| A model stays overloaded (503) or out of quota (429) | **Model fallback chain** (`common.with_fallbacks`): each model in `meta.models.{text,tts}` + `*_fallbacks` gets 2 attempts, then the next one is tried. A backup success is logged with `fallback_from`; the sidecar `<file>.json` records which model made each narration line. The cache key covers the whole chain, so a line made by a backup is not regenerated when the primary recovers. Tested in `tests/test_fallbacks.py` (`make test`). |
| Primary image model fails | Automatic fallback to `meta.models.image_fallback` (text-only), logged with `fallback_from` |
| No Wan clip for a shot / clip failed | Ken Burns move over the keyframe (always available) |
| No chosen score yet | Clearly-labelled temp pad from FFmpeg |
| One shot fails in a stage | The other shots still complete. The stage exits non-zero and lists the failed shots, and a re-run only retries those (cache). |
| Kaggle session timeout | The notebook saves each clip and timings.json after every shot and skips finished shots on re-run |
| No API keys | `OFFLINE=1` / `make offline` runs the whole pipeline with labelled placeholders to test timing and assembly |

## runs.jsonl schema
`ts, run_id, stage, item, provider, model, params, seed, status, cache_hit, attempts, latency_s, gpu_s, cost_usd_equiv, output, [error], [fallback_from], [imported]`
`make costs` aggregates it per stage for COSTS.md.

## Audio chain
narration WAVs (trimmed, normalised to -18 LUFS each) placed at `shot start + 0.6 s` → music (pre-levelled to -20 LUFS, `volume_db`, 2 s fade-in, 3 s fade-out) → `sidechaincompress` keyed by the narration (threshold 0.02, ratio 6, attack 300 ms, release 1500 ms) → sum → **two-pass `loudnorm`** to -14 LUFS integrated, -1 dBTP.

## Picture chain
Square 1024² keyframes → cover-crop to 1280×720 or 720×1280 → `zoompan` at 3× oversampling (no jitter) or a Wan clip (first 0.25 s trimmed, slowed ≤1.6× then last-frame hold) → reconstruction grade and tag → title overlay (Noto Serif Ethiopic) on s01 → concat + end card → burned-in subtitles (≤2 lines × 40 chars, raised in 9:16 for the platform UI safe area) → H.264/AAC, 24 fps CFR, `+faststart`.
