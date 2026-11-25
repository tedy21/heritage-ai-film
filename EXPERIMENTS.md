# EXPERIMENTS — hypothesis → change → result

Rules: change **one** thing, keep the seed fixed, and cite the evidence (runs.jsonl `run_id`s, file names, or what testers said).

| # | Hypothesis | Change (one variable) | Result (evidence) | Decision |
|---|---|---|---|---|
| E1 | Measured narration timing gives a film inside 60–90 s with the planned shot lengths | Narration drives shot length (`timeline.py`) | Offline: 79.6 s total. _TODO: real TTS measurement_ | |
| E2 | A style block on every prompt keeps the 9 keyframes looking like one film | s01–s03 with vs without `style_block` (same seeds) | _TODO_ | |
| E3 | Conditioning on the golden reference keeps the monastery architecture consistent | s03/s04 with `refs` vs text-only (FLUX.2 klein, same seed) | _TODO_ | |
| E4 | FLUX.2 klein beats FLUX.1 schnell for this look at similar latency | Same prompt + seed on both | _TODO (latency from runs.jsonl)_ | |
| E5 | A delivery instruction improves Amharic narration more than switching voice | TTS with vs without the style line; then voice A vs B | _TODO (native listener)_ | |
| E6 | Asking for "out of focus writing" avoids garbled Ge'ez in s05 | Prompt with vs without the phrase | _TODO_ | |
| E7 | Wan at 480p is good enough on a phone and much cheaper than 720p | Same shot, 832×480 vs 1280×704 | _TODO (gpu_s)_ | |
| E8 | Motion-only i2v prompts drift less than full descriptions | s02 motion-only vs subject+motion prompt | _TODO_ | |
| E9 | Ducking at ratio 6 keeps narration clear without the music "pumping" | ratio 4 vs 6 vs 10 | _TODO_ | |
| E10 | The detailed ACE-Step caption ("Ethiopian-inspired… krar-like… washint-like") gives an Ethiopian-sounding score that sits under the voice | 3 candidates, seeds 301–303, turbo DiT, no LM planner (`llm_initialized=False`) | All 3 generated (85.0 s each, 7.7–12.5 s GPU on a T4; loudness −18.0 / −17.9 / −15.8 LUFS). **First listen: they sound Western classical, not Ethiopian.** The words "krar-like"/"washint-like" didn't steer the timbre. _TODO: listen under the narration and pick one._ | Hypothesis partly failed → E12 |
| E10b | Same seeds reproduce the same score | Re-ran seeds 301–303 after the session was wiped (F10) | Byte-identical files (same UUIDs and sizes: 13,724,955 / 13,839,591 / 13,222,886 B) | Seeds are a reliable reproduction key |
| E12 | Naming concrete Ethiopian musical features gets closer than "Ethiopian-inspired" | Caption names the tizita/anchihoye pentatonic scale, masenqo (one-string fiddle), krar lyre, soft kebero hand drum; same seeds | _TODO (optional, if GPU time allows)_ | |
| E11 | Ken Burns vs Wan on the same shot: viewers can't strongly tell on a phone | Blind A/B with ≥5 people | _TODO (ceiling)_ | |
