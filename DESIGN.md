# DESIGN — ጣና፡ በማዕበል ያልጠፋ ታሪክ / Tana: A Story That Outlasted the Waves

> Written **before** any image, clip or music was generated (25 Nov 2026). Test notes are added below as they happen.

## Brief
| | |
|---|---|
| **Who watches** | Ethiopian youth and families, at home and in the diaspora; international viewers curious about Ethiopian heritage. |
| **Where** | On a phone, mostly vertical (Telegram, TikTok, YouTube Shorts); horizontal on YouTube. Often with sound low, so subtitles must carry the meaning. |
| **What they should feel / understand at the end** | Lake Tana is not only a beautiful landscape. It is a living part of Ethiopia's memory, and protecting it is now *their* part. |
| **Define (one sentence)** | How might we help young Ethiopians see Lake Tana's monasteries as *their* inheritance to protect, not just a tourist view? |
| **Constraints** | 60–90 s, Amharic narration + English subtitles, zero budget (free tiers), about 1.5 days, no real person shown or voiced. |

## Why this story matters to me
I love the title "Tana: A Story That Outlasted the Waves" because it makes me wonder how many stories this beautiful lake holds. To me, Lake Tana is not just a lake; it is a place full of history, memories, culture, and traditions that have survived for generations. I find that really special, and I feel excited to explore these stories and share them with others through this film.

## Story in five sentences
1. At dawn, Lake Tana wakes; it is Ethiopia's largest lake and the source of the Blue Nile.
2. People have lived with and on this lake for generations.
3. Hidden in its island forests are ancient monasteries whose walls and books hold the country's art, faith and knowledge.
4. Scribes made those books by hand, and in times of war and hardship the islands kept them safe: the "waves" did not erase them.
5. Today that trust passes to us: to know, honour and protect it.

## Design decisions
- **Present vs reconstruction is visible.** Historical scenes (s06, s07) get a warm desaturated grade and a vignette. An on-screen "AI reconstruction" tag was tried in the rough cut and turned off because it covered the picture; the end card says the film was made with AI.
- **No real people.** All figures are synthetic and shown from behind, in profile or at a distance. This avoids consent problems and face artefacts, and keeps the focus on the place.
- **No readable script in images.** Models garble Ge'ez letters, so manuscripts are shown as painted illuminations in soft focus. All words come from subtitles and titles added in code.
- **Narration sets the timing.** Shot length = max(planned length, narration + breathing room).
- **Centred composition, square keyframes.** One keyframe serves both 16:9 and 9:16 crops.

## Shot list and reasons (mirrors `storyboard.json`)
| Shot | Era | What we see | Why it exists |
|---|---|---|---|
| s01 | present | Aerial sunrise over the lake + title | Establish place and calm, reverent tone |
| s02 | present | Papyrus tankwa gliding | Heritage is human, not only scenery |
| s03 | present | Monastery revealed through trees | The turn: the landscape hides something deeper |
| s04 | present | Painted church wall | Art as prayer and teaching |
| s05 | present | Illuminated manuscript close-up | Preserved knowledge, made tactile |
| s06 | reconstruction | Scribe writing by the light of beeswax tapers (twaf) held by a helper | The human effort of the generations |
| s07 | reconstruction | Books carried to an island at dusk | Protection through hardship = "the waves" |
| s08 | present | Elderly monk before the painted church | Hand-over from a living guardian to the audience |
| s09 | present | Sunset over the lake | Echo of the opening; title line + call to action |

## Music spotting (after the radio cut gave real timing)
Following the professional order: watch/listen to the cut, spot cues with timecodes, then choose and shape the score. The notes are generated from the measured narration (`make spotting` → `outputs/music/spotting_notes.md`):

Film length 01:20.88 incl. 3.0s end card. Score: `outputs/music/candidates/cand_302.flac`, 66 BPM, D minor. Gain changes ramp over 1.5s; the score is also ducked under every narration line.

| Cue | In | Out | Length | Shots | Gain | What it should do |
|---|---|---|---|---|---|---|
| m1 | 00:00.00 | 00:16.92 | 16.9s | s01–s02 | -3 dB | Open quietly with the dawn; sparse plucked notes, sense of space. |
| m2 | 00:16.92 | 00:41.88 | 25.0s | s03–s05 | +0 dB | Discovery and wonder as the monasteries appear; strings pad enters. |
| m3 | 00:41.88 | 00:59.88 | 18.0s | s06–s07 | -4 dB | Weight of history and hardship; lower, darker, slower. |
| m4 | 00:59.88 | 01:17.88 | 18.0s | s08–s09 | +2 dB | Hope and handover; the opening motif returns, warmer, then resolves. |

The chosen ACE-Step track is shaped per cue (`gain_db`, 1.5 s ramps) and ducked under the voice. Candidates are auditioned **under the narration** (`make audition`), not on their own.

## Viewer comments on the stills (received 26 Nov 2026)
| Comment | Change (storyboard prompts) |
|---|---|
| User 1: replace the candle with the traditional taper (twaf) used in the Ethiopian Orthodox church (reference photo supplied) | s06: a helper holds two joined beeswax tapers with one flame; "candlelight" → "firelight"; camera `pull_out` → `static` so the taper stays visible in 9:16 |
| User 2: make the people's faces Ethiopian | s06 scribe and s07 monks described explicitly; s04 and s05 painted saints in the Gondarine style; s07 now uses a papyrus tankwa |
| Viewer comment: close with an ending and a thank-you | End card says "The End", "Thank you for watching" and "Made with AI"; technical credits and model names were removed |

Prompt lesson: the word "twaf" alone gave ordinary separate candles; describing the object's shape (one grooved stick, "two sticks fused together") gave the joined tapers.

## User test 1 — radio cut (narration + temp music on black)
_Date / where:_ before the narration fixes of 25 Nov; exact time and listening setup not recorded · _People:_ 3 listeners (roles not recorded). Recorded on 26 Nov.

| Person (role) | What they said / where they reacted | What we change |
|---|---|---|
| First listener | The overall audio was too long | Reviewed timing and pacing: text-only batched narration and a 0.45 s pause cap; radio cut 172 s → 79.5 s (F14, E5, E5b) |
| Second listener | English audio sometimes appeared at the end of every sentence, interrupting the Amharic | Removed the English style instruction sent to TTS (`narration_voice.style` is now empty); only Amharic text is sent (F15, E5c) |
| Third listener | Some Amharic sentences lacked natural flow and coherence | Rewrote narration lines in `storyboard.json` (s02–s07, s09), with further wording passes on s02, s03 and s06 |

**Insights:** listeners caught problems that the automated checks missed (spoken English, unnatural Amharic). Length, language purity and phrasing had to be settled before spending on pictures.
**Storyboard changes (commit / diff):** `521533c` (empty TTS style, pause cap, rewritten lines), `f538222` (s02, s03), `2c432f6` (s06). See `git show <commit> -- storyboard.json`.

## User test 2 — near-final cut
_Date / where:_ 26 Nov 2026, near-final film (4 Wan shots + 5 Ken Burns, s03 person removed, F20); viewing device not recorded · _People:_ 3 friends (2 understand Amharic, 1 relied on the English subtitles)

| Person (role) | What they said / where they reacted | What we change |
|---|---|---|
| Friend who speaks Amharic | "Overall, I really enjoyed the video… the Amharic narration is much better now. However, a few transitions could be smoother, and some scenes could use a little more time." | **Changed:** every cut now dips 0.25 s through black instead of a hard cut (`shots.DIP_S`); shot lengths unchanged so narration stays in sync. **Not changed:** shot length: the film is 80.8 s against the 60–90 s limit and each shot is timed to its narration line (see next steps) |
| Friend (reads the English subtitles) | "I noticed English subtitles appearing in a few places, but I wasn't sure whether they were part of the intended design. I also think the subtitles could be slightly larger." | **Changed:** subtitle size +20% (libass 9→11 in 9:16, 15→17 in 16:9). The English subtitles are intended (for viewers who don't speak Amharic) and run under every line |
| Friend who understands Amharic | "I liked the storytelling and the historical atmosphere. Most of the subtitles were readable, but one or two scenes looked a little unusual. Overall, the video communicates the story nicely." | **Not changed yet:** the scenes were not named. The likely candidates are AI artefacts in the generated pictures (cf. the invented person removed from s03, F20) |

**Insights:** compared with test 1, nobody mentioned length or spoken English, and the Amharic narration was called "much better now", so the round-1 fixes (F14, F15, rewritten lines) held. Before this round, a full transcription of the final soundtrack (Gemini, 26 Nov) confirmed 16 Amharic sentences and **no spoken English**; the remaining "English" comment was about the subtitles, which are by design. What is left is finish: cuts, subtitle size, and the realism of a few AI scenes.
**Changes made:** soft dips at every cut (`STAGE_VERSION["segments"]` 3) and larger subtitles (`STAGE_VERSION["assemble"]` 6); both films rebuilt.
**Next steps (not done, with reason):** longer scenes would mean slower narration or shots past the line ends, against a hard 90 s limit; ask Person 3 which scenes looked unusual, and regenerate those keyframes (cheap: FLUX on Cloudflare) rather than Wan clips (~25 GPU min each).
