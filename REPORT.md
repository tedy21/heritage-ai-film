# Report — ጣና፡ በማዕበል ያልጠፋ ታሪክ / Tana: A Story That Outlasted the Waves

80.8 s Amharic heritage short with English subtitles, 9:16 and 16:9. Repository: <https://github.com/tedy21/heritage-ai-film> (`make film` rebuilds both films from a clean clone, no GPU needed). Built 25–26 Nov 2026 at $0 on free tiers (list-price equivalent ≈ $0.86, COSTS.md).

> **[YOUR WORDS — remove this note when done]** Everything below is drafted from the repository's logs. Read each section, change anything that is not how *you* saw it, and rewrite the marked parts in your own voice. The interview will ask about these points.

## 1. What I set out to make, and for whom
**Audience:** young Ethiopians and families at home and in the diaspora, watching on a phone, often with the sound low; secondly, international viewers curious about Ethiopian heritage.
**Intent:** that by the end they see Lake Tana's island monasteries not as a tourist view but as *their* inheritance to know, honour and protect (DESIGN.md, written before anything was generated).

The film moves from the present-day lake (sunrise, tankwa paddlers, a monastery among trees) to what the monasteries hold (wall paintings, manuscripts), then to two AI reconstructions (a scribe working by taper light; monks carrying books to an island in hard times), and back to the present: "today this trust is in our hands".

**Why it matters to me:** I love the title "Tana: A Story That Outlasted the Waves" because it makes me wonder how many stories this beautiful lake holds. To me, Lake Tana is not just a lake; it is a place full of history, memories, culture, and traditions that have survived for generations. I find that really special, and I feel excited to explore these stories and share them with others through this film.

**Pipeline:** `storyboard.json` is the contract for every stage: Gemini TTS narration (measured lengths set shot lengths) → FLUX.2 klein keyframes on Cloudflare, conditioned on a reference sheet → Wan 2.2 TI2V-5B image-to-video on a Kaggle T4 for 4 shots, a Ken Burns move for the other 5 → ACE-Step 1.5 score → FFmpeg assembly (ducking, two-pass loudnorm to −15.1 LUFS / −2.7 dBTP, burned-in subtitles, AI end card). Every model call is a line in `runs.jsonl`; outputs are cached by content hash, so a change regenerates only what it touches.

## 2. What I learned from my audience
I tested three times, and each round changed the film (DESIGN.md).

| Round | What people said | What changed |
|---|---|---|
| **User test 1** (radio cut: narration + music on black, 3 listeners) | Too long; English audio at the end of sentences; Amharic lacked flow | The TTS model was *reading my English style instruction aloud* and dragging every line (F14, F15). Sending Amharic text only cut the radio cut from 172 s to 79.5 s; lines rewritten (commits `521533c`, `f538222`, `2c432f6`) |
| **Comments on the stills** (26 Nov) | The scribe's candle should be a traditional Ethiopian twaf; faces should look Ethiopian; end card should say thanks | s06 and s04 prompts rewritten (E14, E15); end card "The End / Thank you for watching / Made with AI" |
| **User test 2** (near-final film, 3 viewers) | "Amharic narration is much better now"; transitions could be smoother; subtitles slightly larger; one or two scenes looked unusual | 0.25 s dip at every cut, subtitles +20%; unnamed odd scenes logged as next step |

**The main lesson:** listeners caught what my automated checks missed. My transcription check asked for "the language spoken" and silently dropped the English, the exact bug it should have found (F15). Before round 2 I therefore re-checked the final soundtrack with a question aimed at the bug ("list every *spoken* English word"): none. Round 2's "English" comment turned out to be about the subtitles, which are by design.

**[YOUR WORDS]** One sentence on what surprised you most in what people said.

## 3. The hardest problem and how I solved it
**Getting clean, natural Amharic narration that fits 60–90 s** (F13–F17, E5–E5c).
- **Symptom:** the first radio cut was 172 s for 98 words; single lines took 18–22 s.
- **Wrong first diagnosis:** I thought the model was simply speaking too slowly, so I changed the instruction to "natural steady pace" and capped pauses: still 113 s and uneven (E5).
- **Real cause, found by a person listening:** Gemini TTS speaks the text it is given. My English style instruction ("Say the following in Amharic…") was being *spoken*, in English, before each line (F15). Moving it to `systemInstruction` returned HTTP 500 (E5c).
- **Fix:** send only the Amharic text, in one batched request split at the longest silences (E5b): one consistent voice, steadier pace, 1/9 of the 10-requests-per-day quota (F13). Result: 48.6 s of narration, a 79.5 s film.
- **Follow-ups the same ears found:** a click at the start (F16) and an ending that felt silent (F17). Fixing those without spending TTS quota led to splitting the narration cache into raw model output and processed audio: the F16/F17 rebuild made **0 API calls**.

A close second was motion: Wan 2.2 ran out of memory on the 15 GB T4 (8 failed attempts, all logged). Sequential CPU offload fixed it at 2.74 GB peak, but at ~25 min per 4 s clip, 122.7 GPU min in total (F19). Then Wan invented a person in an empty scene, so I dropped that clip and kept the Ken Burns shot (F20).

**[YOUR WORDS]** If you think the motion problem was harder, swap the order and say why.

## 4. A suggested practice that helped, and one that did not
**Helped: a JSON contract between stages + logging every call.**
Because every stage reads `storyboard.json` and every call lands in `runs.jsonl` with its inputs' hash, late changes stayed cheap and visible: swapping s03 from Wan to Ken Burns was a one-word change that rebuilt only s03; changing narration processing cost no TTS calls; and the log kept the 8 failed GPU attempts, so COSTS.md shows the *real* cost of motion, not just the successful runs. The validator (`pipeline/rules.py`) turns the brief's rules into checks that run before every build, for example that the end card says the film was made with AI (tested in `tests/test_rules.py`).

**Did not beat my instinct: a reference sheet before keyframes, used for every shot.**
Conditioning keyframes on the golden monastery reference made the exteriors match exactly (E3), but the reference *won over the prompt*: the "interior wall" came out as the outside of the church, the manuscript close-up was placed outdoors, and the sunset took the reference's morning light. Text-only prompts gave the right interior, close-up and sunset. The rule I ended with: use references only for shots with the same framing and light (s01–s03, s08). The reference itself also needed help: a generic "round church" prompt gave a village hut on 4/4 images until I named the defining features (cross finial, veranda ring, stone wall: 4/4, E3b).

**[YOUR WORDS]** Say in a sentence whether this matches your experience, or choose a different pair.

## 5. Ceiling work
Honest answer: I did not complete a full ceiling direction. What I did beyond the floor:
- **Reproducibility check:** after a Kaggle session wiped the music, the same seeds re-generated **byte-identical** score files (E10b).
- **Begena experiment prepared, not run:** ACE-Step with a described vs a named Ethiopian prayer lyre, seeds 401–403 (E13). Deferred once score 302 was chosen.
- **Frontier comparison:** not possible without paid access; noted in COSTS.md.

## 6. What I would build next
- **Make the music Ethiopian:** the captions "krar-like / washint-like" gave a Western-classical score (E10). Run E13 and E12 (named scale and instruments), or record a real begena/krar with permission.
- **Fix the unnamed "unusual" scenes** from user test 2: ask which ones, then regenerate those keyframes (seconds on Cloudflare) rather than Wan clips (~25 GPU min each). Add "person, people" to Wan's negative prompt for empty scenes (F20).
- **Longer motion:** 4 s Wan clips are slowed and then hold their last frame; a second Kaggle GPU or a longer clip setting would remove the freeze.
- **A tool for others:** the storyboard contract already makes the pipeline reusable; a small CLI that takes someone else's storyboard (another lake, another language) would test that claim.

## 7. How I worked with the coding agent
The stage scripts were written with **Claude Code (Claude Opus 5.5)**. I designed the story, audience and storyboard, chose between candidates (score 302, prompts), ran the Kaggle GPU notebooks, listened and watched, and ran the user tests; the agent wrote and fixed code from what I reported. Two cases where the human step mattered: the agent's transcription check missed the spoken English that I heard (F15), and an agent suggestion (`make offline`) overwrote real outputs with placeholders, which I restored with git.

**[YOUR WORDS]** One sentence on what you would do differently next time when working with an agent.
