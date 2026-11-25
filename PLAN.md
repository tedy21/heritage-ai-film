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

**Phase 1: Foundation** ✅ *(pipeline, Kaggle music, smoke test, radio cut)*

**Phase 2: Lock the words** *(today)*
- [ ] 2.1 You: decide s02 (ውስጥ / ላይ) and s03 (fix "older than the lake")
- [ ] 2.2 Claude: `make radio` + `make script` → 9/9, no notes
- [ ] 2.3 You: user test 1, play `radio_cut.mp4` to 3+ people, send me their answers
- [ ] 2.4 Claude: write test 1 into DESIGN.md + make 1 storyboard change from it
- Done when: `make status` shows user test 1 = 3/3

**Phase 3: Pictures** *(today, runs alongside 2.3)*
- [ ] 3.1 Claude: generate 4 reference-sheet candidates (FLUX)
- [ ] 3.2 You: pick 1 reference
- [ ] 3.3 Claude: generate 9 keyframes, you flag any bad ones, Claude redoes only those
- [ ] 3.4 Claude: `make film` → rough cut, 16:9 + 9:16 (Ken Burns, the safety net)
- Done when: both MP4s exist, 60–90 s

**Phase 4: Music**
- [ ] 4.1 You: listen to auditions 301 / 302 / 303, pick one + one-sentence reason
- [ ] 4.2 Claude: set `music.chosen`, log E10, rebuild the film
- Done when: `make status` shows the score chosen

**Phase 5: Motion** *(tomorrow morning)*
- [ ] 5.1 Claude: prepare the Kaggle input (keyframes + storyboard)
- [ ] 5.2 You: run the Wan notebook (new notebook, T4), download the zip before stopping
- [ ] 5.3 Claude: `make import-gpu` → clips replace Ken Burns shot by shot
- Done when: GPU minutes appear in COSTS.md (if Wan fails, keep Ken Burns and log it)

**Phase 6: Polish + evidence**
- [ ] 6.1 Claude: run experiments up to 10/10 with results
- [ ] 6.2 Claude: final assembly, both ratios
- [ ] 6.3 You: user test 2 (3+ people), send their answers
- [ ] 6.4 Claude: write test 2 into DESIGN.md + make the changes
- Done when: experiments 10/10, user test 2 = 3/3

**Phase 7: Write-up** *(tomorrow afternoon)*
- [ ] 7.1 You: 2–3 sentences "why this matters to me" (DESIGN.md)
- [ ] 7.2 Claude: draft REPORT.md + final docs + `make costs`
- [ ] 7.3 You: make the report personal → export to PDF
- Done when: `make status` shows the report done

**Phase 8: Ship** *(tomorrow evening, by 22:00)*
- [ ] 8.1 Claude: clean-clone test (`git clone` → `make film`)
- [ ] 8.2 Claude: write the walkthrough script; you record it (≤ 5 min)
- [ ] 8.3 You: post the film with the AI label on
- [ ] 8.4 You: add the links to the README, run `make status`, submit both forms
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
