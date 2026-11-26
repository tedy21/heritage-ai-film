# ETHICS — consent, cultural care, licences, labelling

## Consent record
| Person | Appears (face/likeness)? | Voiced? | Consent |
|---|---|---|---|
| — | No real person is shown. Figures (paddler, scribe and helper, monks, painted saints) are generic and AI-generated, shown from behind, in profile or at a distance, and not based on anyone. | No. Narration is a Gemini TTS **prebuilt synthetic voice** (`Charon`), not a clone of anyone's voice. | Not required (no real person). If a real relative's face, likeness or voice is ever added, their recorded, informed consent to that exact use and those exact words goes here **before** generation. |

## Cultural and religious care
- The monasteries of Lake Tana are active Ethiopian Orthodox Tewahedo sacred places. Prompts describe them respectfully. There are no invented rituals, no identifiable clergy, and no copying of specific real icons.
- Historical scenes (s06, s07) are graded differently from present-day scenes. They carry no on-screen or end-card reconstruction label in the current cut (see the labelling plan).
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
| Score | ACE-Step 1.5 | MIT licence; trained on licensed, royalty-free and synthetic data (per the authors and the challenge brief) | Usable commercially per the challenge brief |
| Narration | Gemini TTS (Gemini API free tier) | Google Gemini API terms; free-tier inputs may be used to improve products | Usable with disclosure |
| Script help | Gemini Flash | Gemini API terms | — |
| Assembly | FFmpeg | LGPL/GPL tool; does not affect output | — |
| Fonts | Noto Sans, Noto Serif Ethiopic | SIL Open Font License | — |
| This repo | — | see LICENSE | — |

## Labelling plan
1. **In the film:** historical shots (s06, s07) get a distinct warm, desaturated grade with a vignette. The 3 s end card says "The End", "Thank you for watching" and "Made with AI". An on-screen "AI reconstruction" tag was used in the rough cut; it was turned off (`meta.reconstruction_tag: false`) because it covered the image and read as clutter on a phone. AI disclosure is also provided through platform labels and the metadata below.
2. **In the file:** MP4 metadata `title` and `comment` say it is made with AI and name the models. We add no step that removes watermarks or provenance. Honest limits: Gemini TTS audio carries an inaudible SynthID watermark, but our processing (trim, fades, loudnorm, ducking, AAC encoding) changes the waveform, and we have no tool to verify the watermark survives. FFmpeg re-encoding does not carry over provider metadata from source files. So the visible end card and the platform labels are the labelling we rely on.
3. **On platforms:** YouTube "altered or synthetic content" = ON; TikTok "AI-generated content" label = ON; the post text says it was made with AI.
