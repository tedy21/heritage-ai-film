# FAILURES — what broke, what we tried, what fixed it

Format: **symptom → cause → what I tried → fix / workaround → evidence**.

### F1. `make setup` could not create a virtualenv (25 Nov)
- **Symptom:** `python3 -m venv .venv` → "ensurepip is not available".
- **Cause:** Ubuntu's `python3.12-venv` package is not installed, and installing it needs sudo.
- **Fix:** the Makefile now uses the system Python when it already has `jsonschema` and `requests`, then tries a venv, then `pip --user`. A stranger's clean clone still works with one command.

### F2. Offline placeholder generator crashed (25 Nov)
- **Symptom:** FFmpeg `gradients ... speed=0` → "Value 0 out of range [1e-05 - 1]".
- **Fix:** speed=0.01. Found by the offline end-to-end run before any quota was spent, which is the point of `make offline`.

### F3. Cache hashing crashed on nested file paths (25 Nov)
- **Symptom:** `TypeError: Object of type PosixPath is not JSON serializable` when hashing the mix inputs (a list of (path, offset) pairs).
- **Fix:** `stable_hash` now hashes any `Path` at any nesting depth **by file content**. This is what makes downstream caching correct: a regenerated narration WAV changes the mix key even if its file name were reused.

### F4. FFmpeg filters broke on the repo path, which contains a space (`personal/ projects`) (25 Nov)
- **Symptom:** drawtext/subtitles filters could not open font/text/SRT files.
- **Fix:** `shots.fq()` quotes and escapes every path used inside a filter argument. Re-tested from a scratch directory named `t 1`.

### F5. Long subtitles left two-word orphans (25 Nov)
- **Symptom:** s05's 91-character subtitle split into a full cue + "for centuries." (seen on a frame grab).
- **Fix:** `_balanced()` splits long sentences into near-equal pieces at word/comma boundaries.

### F6. Wan 2.2 TI2V-5B image-to-video has no documented diffusers recipe (25 Nov)
- **Symptom (docs):** the HF repo `Wan-AI/Wan2.2-TI2V-5B-Diffusers` is a `WanPipeline` whose documented call has no `image=` argument. `WanImageToVideoPipeline` is documented only for Wan 2.1 14B.
- **What I did:** the notebook tries `WanImageToVideoPipeline` first, prints whether the loaded pipeline accepts `image=`, and records the pipeline used in every timings line.
- **Result:** _TODO after the first Kaggle run_

<!-- Add new entries as they happen: quota (Cloudflare daily neurons, Gemini RPD), OOM on T4, fp16 NaNs, Amharic pronunciation errors, identity/consistency drift, ACE-Step on T4… -->

### F7. Kaggle notebook could not find the uploaded storyboard (25 Nov)
- **Symptom:** `IndexError: list index out of range` on `glob("/kaggle/input/*/storyboard.json")[0]`.
- **Cause:** Kaggle now mounts uploaded datasets one level deeper than the one-level glob assumed.
- **Fix:** a recursive search, `glob("/kaggle/input/**/storyboard.json", recursive=True)`, in both notebooks. Lesson: don't hard-code platform mount layouts; search for the file.

### F8. `uv` not found on Kaggle (25 Nov)
- **Symptom:** `/root/.local/bin/uv: No such file or directory`.
- **Cause:** the curl installer's target path differs on Kaggle, and the install cell's `%cd` wasn't guaranteed to have run.
- **Fix:** `pip install uv`, absolute `%cd /kaggle/working/ACE-Step-1.5` before `uv sync` and `uv run`, and gen.py written to an absolute path.

### F9. ACE-Step crashed on import: invalid matplotlib backend (25 Nov)
- **Symptom:** `ValueError: Key backend: 'module://matplotlib_inline.backend_inline' is not a valid value for backend`, raised while `acestep` imported lightning → torchmetrics → matplotlib.
- **Cause:** Kaggle exports `MPLBACKEND` for its notebook UI. The `uv run` child process inherits it, but ACE-Step's isolated `.venv` has no `matplotlib_inline`.
- **Fix:** `MPLBACKEND=Agg uv run python gen.py`, which overrides the variable for that one command (Agg = headless, file-only rendering).
- **Lesson:** isolated environments still inherit environment variables from the parent process.

### F10. Generated music lost when the Kaggle session stopped (25 Nov)
- **Symptom:** after stopping the session, `/kaggle/working` showed no files; the 3 ACE-Step candidates (seeds 301–303, ~8 s GPU each) could not be downloaded.
- **Cause:** the notebook's Persistence was "No persistence", so `/kaggle/working` is wiped when the session ends. Outputs can only be downloaded from a running session or a saved version.
- **Fix:** set Persistence to "Files only"; zip the results and download them with `FileLink` *before* stopping; regenerate with the **same seeds**, which is why seeds are logged.
- **Lesson:** treat cloud GPU sessions as disposable; copy outputs off the machine as the last step of every run.

### F11. FLUX.1 schnell on Cloudflare rejects a seed (25 Nov, smoke test)
- **Symptom:** `HTTP 400 … Additional or unevaluated properties '/seed' at '/' not allowed` (code 5006).
- **Cause:** Cloudflare's input schema for `@cf/black-forest-labs/flux-1-schnell` has no `seed` field (FLUX.2 klein accepts one).
- **Fix:** don't send `seed` to schnell. **Consequence:** fallback images from schnell are not seed-reproducible; the seed is still logged, and the image file itself is the reproducible artefact. Klein (the primary) stays seeded.
- **Found by:** `make smoke` (run `smoke1`), before any real generation.

### F12. Gemini 3.8 Flash text returned 503 "high demand" (25 Nov, smoke test)
- **Symptom:** HTTP 503 UNAVAILABLE on 3 attempts in two separate runs (`smoke1`, `smoke2`); the retry/backoff worked as designed but the spike outlasted it.
- **Workaround:** switched `meta.models.text` to `gemini-3.5-flash`, which answered in 2.0 s (correct Amharic "ሐይቅ" for "lake"). Text is only used for drafting/translation help, so no film output depends on the 3.8 text model. TTS (`gemini-3.8-flash-tts`) was unaffected.
- **Lesson:** keep the model id in the storyboard, not the code, so swapping models is a one-line contract change.

### F13. Gemini TTS free tier: 10 requests per model per day (25 Nov, radio cut)
- **Symptom:** HTTP 429 on `gemini-3.8-flash-tts` from the 6th line of the second narration run; quota details: `GenerateRequestsPerDayPerProjectPerModel-FreeTier limit 10`, `retryDelay 2781s` (resets at midnight Pacific ≈ 11:00 EAT).
- **What happened next:** the fallback chain kept the run going. s01–s04, s06, s07 came from `gemini-3.8-flash-lite-tts` and s08 from `gemini-2.5-flash-preview-tts`, so the radio cut mixed **three voice models**. A DNS outage mid-run (`Temporary failure in name resolution`) was also retried and survived.
- **Fix:** **batched narration** (`narration.batch_generate`): the whole script goes in ONE request with 2 s pauses between lines, split at the n−1 longest silences (validated against expected line lengths; falls back to per-line if the split looks wrong). 1 request instead of 9 per full narration, and one consistent voice. Editing a single line later still costs one request. Tested on synthetic audio in `tests/test_batch_split.py`.
- **Lesson:** read the quota *details* in a 429, not just the status code; per-day per-model limits change the architecture, not just the retry policy.

### F14. Narration far too long: 155 s for 98 words (25 Nov, radio cut v1)
- **Symptom:** the radio cut came out at 172 s (brief: 60–90 s). Single lines of 10–12 words took 18–22 s.
- **Diagnosis:** Gemini transcription of the audio showed the model was *not* reading the style instruction aloud; it was speaking very slowly with 1–1.5 s pauses. The instruction "calm, warm, unhurried… with reverence and short pauses" was over-applied, and pace varied between requests (s03: 10 words in 7.9 s; s04: 11 words in 19.8 s).
- **Tried:** (1) instruction asking for a "natural steady speaking pace (not slow)" + (2) capping internal pauses at 0.45 s in post → total 112.9 s, still too long and still uneven (7–19 s per line).
- **Resolved (radio3):** the real cause was F15 (the instruction was spoken). Text-only batched narration: 48.6 s of narration, 79.5 s film.

### F15. The TTS model read the English style instruction aloud (25 Nov, found by the user listening)
- **Symptom:** in the radio cut, every line began with spoken English like "Say the following in Amharic…". It was found by **listening**, not by my automated check: the transcription prompt asked for "the language spoken" and silently dropped the English.
- **Cause:** I prompted a TTS model like a chat model. Gemini TTS speaks the text it is given; an instruction prefix is often spoken rather than obeyed. This also explains most of F14's length (s04: 19.8 s with the instruction → **7.9 s** text-only, same voice family).
- **Tried:** moving the style into `systemInstruction` → **HTTP 500** (not supported by the TTS model).
- **Fix:** send only the Amharic text (`narration_voice.style` is now empty; the schema warns about it); tone comes from the voice choice. The batch request is just the lines separated by blank lines.
- **Lesson:** verify generated media with a check that asks the right question ("is ANY English spoken?"), and with a human listener. The automated check had a blind spot exactly where the bug was.

### F16. Click at the very start of the narration (25 Nov, found by the user listening)
- **Symptom:** a glitch at the start of the film. Measured: the first narration clip (s01) began with a ~0.1 s spike peaking at −6 dB before the speech, and batch-cut clips started and stopped abruptly.
- **Cause:** the edge trim treated any sound above −50 dB as speech, so a TTS start click was kept; cut points had no fades.
- **Fix:** edge trimming now ignores sounds shorter than 80 ms (`start_duration=0.08`, peak detection), and every clip gets a 20 ms fade-in / 60 ms fade-out. The first word now comes at 1.5 s, after a 1 s music fade-in. Measured after the fix: the first 0.1 s of s01 is at −39 dB (fade), then speech.

### F17. "No sound" for the last ~7 s (25 Nov, found by the user listening)
- **Symptom:** from ~1:12 to the end (1:20) the film felt silent.
- **Measured:** not silent. After the last line ended (72.7 s) only the ducked, cue-shaped score played at −20 to −28 dB RMS, fading out over 3 s; next to a −15 dB voice it read as dead air.
- **Fix:** an **outro swell**: when the last line ends, the score rises +4 dB over 3 s and carries the ending, then fades out across the end card. Measured after: −14 to −19 dB until the end card, a fade to −53 dB at 80 s.

### Design change prompted by F16: the narration cache was split into raw and processed
- **Problem:** the processing settings (fades, trimming) were part of the same cache key as the TTS request, so fixing a click would have spent new TTS quota (10/day, F13).
- **Change:** `outputs/narration/raw/` holds model output, keyed by text, voice and model chain; `outputs/narration/` holds processed audio, keyed by the raw file bytes and the processing settings. The existing lines were migrated into the raw layer. Result for the F16/F17 rebuild (`fix5`): **0 API calls**, 9 lines reprocessed by FFmpeg.

### F18. Export true peak above the −1 dBTP ceiling (25 Nov, found by an audit against the brief)
- **Symptom:** the rough cut measured −14.3 LUFS but **−0.7 dBTP** (`ffmpeg -af ebur128=peak=true`); the brief (Appendix B) asks for true peaks below −1 dB.
- **Tried 1:** a brickwall `alimiter` at −2 dBFS after the two-pass loudnorm. The mix WAV then peaked at exactly −2.0 dBFS, but the MP4 still measured −0.76 dB.
- **Cause:** the **AAC encoder adds ~1.2 dB of overshoot** when it compresses the audio, so a ceiling set on the WAV is not the ceiling of the delivered file. (Linear loudnorm alone can't hold a ceiling either.)
- **Fix:** limiter at −3 dBFS with latency compensation (keeps sync), `STAGE_VERSION["assemble"]` bumped so the cache rebuilds. Measured after: **−1.5 dBTP**, −15.0 LUFS (within 1 LU of the target), both ratios.
- **Lesson:** measure the delivered file, not the intermediate.
- **Came back (26 Nov):** after switching from the temp pad to score 302, both films measured **−0.6 dBTP** although the mix WAV still peaked at −3.0 dBFS: AAC overshoot depends on the content (about 2.4 dB here, 1.2 dB before). A −4 dBFS limiter gave −3.5 dBTP / −15.3 LUFS; **−3.5 dBFS** gives **−2.7 dBTP / −15.1 LUFS** on both ratios (kept). The loudness is 1.1 LU under the −14 target. Re-measure after any audio change.

### F19. Wan 2.2 ran out of GPU memory on the Kaggle T4 (26 Nov, notebook run)
- **Symptom:** the first full run ended with all 5 shots `status: error`: `OutOfMemoryError: CUDA out of memory` (s01 after 15.9 s; s02–s09 within 0.4 s each, because the failed shot's memory was never released). Peak allocated memory was **15.45 GB** on a ~15 GB T4. `outputs/clips/timings.json` keeps all **8 failed attempts** next to the 5 successes, and they were imported into `runs.jsonl` as errors.
- **Tried 1:** restart the session and set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (less memory fragmentation) → the cascade stopped, but s01 still ran out of memory after 15.4 s. The model with `enable_model_cpu_offload()` simply does not fit: that mode moves *whole* sub-models (the 5B transformer) onto the GPU at once.
- **Fix:** `enable_sequential_cpu_offload()` moves weights layer by layer → **2.74 GB peak**, all 5 shots `ok`. **Cost:** ~25.7 s per diffusion step, **~1460–1490 s (≈ 25 min) per 4 s clip**, 2 h 2 min of GPU time for 5 shots. System RAM came close to the limit (≈ 28.7 / 30 GB), so this is also the most this setup can hold. Only one of the two T4s is used.
- **Also confirmed:** the image-to-video class loads (`WanImageToVideoPipeline`, `image=` accepted), so the clips start from our keyframes; each 4 s clip is slowed at most 1.6× (~6 s of motion) and then holds its last frame for the rest of the 8–10 s shot (`shots._clip`).
- **Lesson:** test one shot (`todo[:1]`) before a batch run, and record failed GPU calls too: they are part of the real cost.

### F20. Wan invented a person in s03 (26 Nov, found by the user watching)
- **Symptom:** in the monastery-through-the-trees shot (0:16–0:24) a dark, smeared figure appears at the right of the hut and walks into the doorway. The keyframe has no person; the clip adds one from about 1 s in (checked frame by frame at 0.2, 1, 2, 3 and 3.9 s).
- **Cause:** image-to-video models fill a doorway or path with "plausible" motion; the motion prompt ("slow push forward between the trees, leaves sway") did not forbid people, and the negative prompt has no "person". The figure is also badly formed (a glitch, not a character).
- **Fix (no new GPU time):** `render: "kenburns"` for s03, so the shot is a slow push-in over the clean keyframe. The Wan clip stays in `outputs/clips/` (it is part of the logged cost) but is no longer used. Film now: 4 Wan shots (s01, s02, s08, s09) + 5 Ken Burns; 80.8 s, −15.1 LUFS, −2.7 dBTP unchanged.
- **Lesson:** watch every generated clip to the end before using it; for a re-render, add "people, person, figure" to the negative prompt of shots that should be empty.
