# ETHICS — consent, cultural care, licences, labelling

## Consent record
| Person | Appears (face/likeness)? | Voiced? | Consent |
|---|---|---|---|
| — | No real person is shown. Figures (paddler, scribe, carriers, young visitor) are generic, AI-generated, seen from behind or far away, and not based on anyone. | No. Narration is a Gemini TTS **prebuilt synthetic voice** (`Charon`), not a clone of anyone's voice. | Not required (no real person). If a real relative's face, likeness or voice is ever added, their recorded, informed consent to that exact use and those exact words goes here **before** generation. |

## Cultural and religious care
- The monasteries of Lake Tana are active Ethiopian Orthodox Tewahedo sacred places. Prompts describe them respectfully. There are no invented rituals, no identifiable clergy, and no copying of specific real icons.
- Historical scenes are labelled **"AI reconstruction"** on screen and on the end card, and are visually graded differently from present-day scenes.
- Factual claims in the narration are kept few and general (largest lake, source of the Blue Nile, manuscripts kept for centuries, treasures protected on the islands in hard times). _TODO: user verifies each line; a native speaker checks the Amharic and the pronunciation of names._
- No readable Ge'ez text is generated (it would be garbled and could misrepresent scripture).

## Private data
No private family information is sent to any API. Prompts contain only public, descriptive text about the place.

## Licences
| Component | Model / tool | Licence / terms | Output use |
|---|---|---|---|
| Keyframes | FLUX.2 klein 4B via Cloudflare Workers AI | Apache 2.0 (4B weights); Cloudflare Workers AI terms | Usable |
| Keyframe fallback | FLUX.1 schnell via Cloudflare | Apache 2.0 | Usable |
| Moving shots | Wan 2.2 TI2V-5B (Kaggle) | Apache 2.0 | Usable |
| Score | ACE-Step 1.5 | Code MIT; trained on licensed, royalty-free and synthetic data per the authors. _TODO: confirm weights licence on the HF model card._ | Usable commercially per the challenge brief |
| Narration | Gemini TTS (Gemini API free tier) | Google Gemini API terms; free-tier inputs may be used to improve products | Usable with disclosure |
| Script help | Gemini Flash | Gemini API terms | — |
| Assembly | FFmpeg | LGPL/GPL tool; does not affect output | — |
| Fonts | Noto Sans, Noto Serif Ethiopic | SIL Open Font License | — |
| This repo | — | see LICENSE | — |

## Labelling plan
1. **In the film:** an "AI reconstruction" tag on historical shots, plus a 3.5 s end card: "Made with AI", the models used, and "Historical scenes are AI reconstructions, not photographs."
2. **In the file:** MP4 metadata `comment` says it is made with AI. Provider watermarks and provenance (SynthID on Gemini audio) are left intact. We never strip metadata.
3. **On platforms:** YouTube "altered or synthetic content" = ON; TikTok "AI-generated content" label = ON; the post text says it was made with AI.
