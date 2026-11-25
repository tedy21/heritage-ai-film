# PLAN: how the work is controlled

**Deadline:** Thu 26 Nov 2026, 23:59 EAT (both assignments).
**Source of truth for "are we ready?":** `make status`, which checks the repo against every rubric criterion.
**This file:** the order of work, what "done" means for each step, and the rules that stop wasted or repeated work.

---

## 1. Working rules (why the work doesn't get redone or missed)

1. **One step at a time, in order.** A step starts only when the previous step's *definition of done* is met. *Why:* the brief's approval chain (story → radio cut → stills → clips → edit) avoids regenerating expensive material.
2. **Change the storyboard, never the outputs.** Every creative change is an edit to `storyboard.json`, then a `make` command. *Why:* the cache rebuilds only what changed, and the change is visible in git.
3. **Validate before spending.** `make validate` (schema + the brief's rules) runs before every stage automatically; no API call happens on a broken plan.
4. **Check before you call.** Before any paid or limited call, check the quota table below. If a call would exceed it, batch it or wait for the reset.
5. **Measure, then decide.** Every choice gets evidence: a `runs.jsonl` line, a test, a listener's words, or an `EXPERIMENTS.md` row. No "it looked better" without a note.
6. **Write it down when it happens.** Breakage → `FAILURES.md` (symptom → cause → tried → fix). Comparison → `EXPERIMENTS.md` (one change, fixed seed). Feedback → `DESIGN.md`.
7. **End every step with:** `make status` → update the tracker below → a commit (one step = one commit).
8. **Never commit secrets.** `.env` is ignored and `make status` scans for keys.

## 2. Quota budget (free tiers, measured, not guessed)

| Resource | Limit found | Used so far | Rule |
|---|---|---|---|
| Gemini TTS (`gemini-3.8-flash-tts`) | **10 requests / model / day**, resets ≈ 11:00 EAT (F13) | 3 today (batch + timeout retry) | Full narration = 1 batched request; edits = 1 per line |
| Gemini text (`gemini-3.5-flash`) | not yet hit | 3 | Script check is cached; re-runs are free until the script changes |
| Cloudflare Workers AI (FLUX) | ~50–170 images / day (brief) | 2 (smoke) | Refs 8 + keyframes 9 ≈ 17 per full pass; regenerate only changed shots |
| Kaggle T4 GPU | 30 h / week, 19.5 GB disk | ≈ 0:35 h | New notebook for Wan; Persistence "Files only"; download before stopping (F10) |

## 3. Phases and tasks (tick as you go; one phase = one commit)

**Phase 1: Foundation** ✅
- [x] 1.1 Pipeline, schema + brief-rules validator, caching, retries, model fallbacks, runs.jsonl
- [x] 1.2 Smoke test of every provider (Gemini, Cloudflare, Kaggle)
- [x] 1.3 Docs scaffold: README, ARCHITECTURE, DESIGN, ETHICS, FAILURES, EXPERIMENTS, COSTS, PLAN
- [x] 1.4 `make status` (rubric check) and `make script` (back-translation subtitle check)

**Phase 2: Lock the words** *(today)*
- [x] 2.1 s02 (ውስጥ → ላይ), s03 (drop "older than the lake"), s06 (ጧፍ, ፊደል በፊደል በብራና ላይ)
- [x] 2.2 Clean Amharic narration (batched TTS, no English spoken) + script check 9/9, no notes
- [x] 2.3 Radio cut rebuilt with the final words (80.8 s)
- [ ] 2.4 **You:** user test 1, play `radio_cut.mp4` to 3+ people, send their answers
- [ ] 2.5 Claude: write test 1 into DESIGN.md + make 1 storyboard change from it
- Done when: `make status` shows user test 1 = 3/3

**Phase 3: Pictures** ✅
- [x] 3.1 Reference sheet: 4 lake + 4 monastery candidates; monastery prompt fixed (E3b); c1 + c1 chosen
- [x] 3.2 9 keyframes; s02/s04/s05/s06/s09 fixed (E3); s08 woman → monk (E3c)
- [x] 3.3 Rough cut, both ratios, Ken Burns (the safety net)
- [x] 3.4 Export to the brief's spec: −1.5 dBTP (F18), 3 s end card, on-screen tag removed

**Phase 4: Music**
- [x] 4.1 3 ACE-Step candidates (301–303), spotting notes, per-cue shaping, auditions
- [x] 4.2 Begena experiment prepared (E13: named vs described caption, seeds 401–403)
- [ ] 4.3 **You:** Kaggle run for the begena sets, download `music.zip`
- [ ] 4.4 Claude: import, auditions, measure, write E13
- [ ] 4.5 **You:** choose the score (begena or 301–303) + one-sentence reason
- [ ] 4.6 Claude: set `music.chosen`, log E10, rebuild both films
- Done when: `make status` shows the score chosen

**Phase 5: Motion** *(tomorrow morning)*
- [ ] 5.1 Claude: prepare the Kaggle input (keyframes + storyboard), pick 4–6 shots
- [ ] 5.2 **You:** run the Wan notebook (new notebook, T4), download the zip before stopping
- [ ] 5.3 Claude: `make import-gpu` → clips replace Ken Burns shot by shot
- Done when: GPU minutes appear in COSTS.md (if Wan fails, keep Ken Burns, fix the end card text, log it)

**Phase 6: Polish + evidence**
- [ ] 6.1 Claude: experiments up to 10/10 with results (now 8)
- [ ] 6.2 Claude: final assembly, both ratios
- [ ] 6.3 **You:** user test 2 (3+ people) on the near-final film, send their answers
- [ ] 6.4 Claude: write test 2 into DESIGN.md + make the changes
- Done when: experiments 10/10, user test 2 = 3/3

**Phase 7: Write-up** *(tomorrow afternoon)*
- [ ] 7.1 **You:** 2–3 sentences "why this matters to me" (DESIGN.md)
- [ ] 7.2 Claude: draft REPORT.md + final docs + `make costs`; state the coding agent used
- [ ] 7.3 **You:** make the report personal → export to PDF
- Done when: `make status` shows the report done

**Phase 8: Ship** *(tomorrow evening, by 22:00)*
- [ ] 8.1 Claude: clean-clone test (`git clone` → `make film`)
- [ ] 8.2 Claude: write the walkthrough script; **you** record it (≤ 5 min)
- [ ] 8.3 **You:** post the film with the AI label on
- [ ] 8.4 **You:** add the links to the README, run `make status`, submit both forms
- Done when: everything green and submitted before 23:59

## 4. Fallbacks (decided in advance, so a failure never stops the film)

| If… | Then… |
|---|---|
| TTS quota runs out | wait for the 11:00 EAT reset, or the fallback chain uses the next TTS model (logged) |
| FLUX.2 klein fails | FLUX.1 schnell automatically (text-only, logged) |
| Wan 2.2 fails or the GPU quota runs out | Ken Burns over the keyframes; the film is complete without clips (the brief allows this) |
| ACE-Step score doesn't fit | keep the best candidate with per-cue shaping; E12 caption retry only if GPU time allows |
| A tester finds a wrong word | edit one line → `make radio` → 1 TTS request |
| Running out of time | priority: film in both ratios → user tests → REPORT → experiments → ceiling work |

## 5. Ceiling work (only after step 9, if time allows)

1. **Second language track** (Afaan Oromo or Tigrinya): the same storyboard and pipeline; document where TTS fails. Cheapest, and high insight.
2. **Blind A/B** Ken Burns vs Wan on the same shot, 5+ people (E11).
3. **Script check as a tool:** back-translation already flags meaning and fact problems; describe it in the report as an idea of our own.

## 6. Decision log (short; details live in the linked files)

| When | Decision | Why | Evidence |
|---|---|---|---|
| 25 Nov | Place story (Lake Tana), no real people | consent gate, faster | ETHICS.md |
| 25 Nov | Text-only TTS, batched | the instruction was spoken aloud; 10 requests/day quota | F13, F15, E5b/E5c |
| 25 Nov | Raw/processed narration cache split | audio fixes must not cost quota | F16 note, ARCHITECTURE |
| 25 Nov | Spotting + per-cue shaping before choosing the score | the professional order (Appendix C) | DESIGN.md spotting table |
| 25 Nov | Script back-translation check stage | accurate subtitles; one Amharic reader | `outputs/script/review.md` |
| 25 Nov | s02 "ውስጥ"→"ላይ"; s03 "ከሐይቁ ዕድሜ የገፋ"→"ዘመናትን የተሻገረ" | boats travel *on* water; monasteries are not older than the lake (script check flagged it) | `outputs/script/review.md` 9/9, no notes; 2 TTS calls, run 20261125T164028 |
| 25 Nov | Remove the on-screen "AI reconstruction" tag; s06 "በሻማ ብርሃን … ቃል በቃል፣ ገጽ በገጽ" → "በጧፍ ብርሃን … ፊደል በፊደል በብራና ላይ" | the tag covered the picture; ጧፍ (beeswax taper) and ፊደል (the Ge'ez letters) are specific to Ethiopian manuscript culture, ሻማ/ገጽ were generic | `meta.reconstruction_tag: false`; end card still discloses reconstructions; script check 9/9; 1 TTS call |
| 25 Nov | s08: young woman → elderly monk from behind | several Lake Tana island monasteries do not admit women; a monk is the living guardian of the heritage | E3c; 2 images |
