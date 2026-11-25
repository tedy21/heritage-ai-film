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
