---
name: word-card
description: "Use on «создай карточку для…»: word meanings mind-map PNG."
version: 1.1.0
author: Nikolay Efimov (nikser), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [english, vocabulary, phrasal-verbs, russian-speakers, image]
    related_skills: [word-breakdown, english-tutor]
---

# Word Card

One English word → one picture: the word in an ellipse in the centre, arrows to its meanings, phrasal
verbs or collocations. Each branch: the phrase (red), Russian translation (green), 1–2 short examples
(black) and, only when it helps, how it differs from a confusable neighbour (orange, `≠ …`).
Explanations are **in Russian** — the learner is a Russian speaker; examples stay English.

Trigger: «создай карточку для <word>», «карточку на <word>», «все значения <word> картинкой».

## When to Use

- A polysemous word (`sick`, `get`, `run`), a verb with many particles, a word with tricky neighbours.
- **Russian → English:** «создай карточку для специально / намеренно». Centre = the main Russian
  word, `subtitle` = the other Russian synonyms; branches = English equivalents. Here `vs` is the
  point of the card — register, connotation and the false friend (`specially` vs `specifically`).
  Check each English candidate's Cambridge entry; ru→en dictionaries aren't on Cambridge.
- Don't use for pronunciation — that's `word-breakdown` (syllables, stress, sounds).

## Prerequisites

- Python 3 + `cairosvg` via `uv run --with cairosvg` (nothing installed globally).
- Font **DejaVu Sans** (Cyrillic + IPA glyphs).

## Procedure

1. **Collect meanings from a dictionary, not from memory.** `web_extract` the Cambridge entries
   `https://dictionary.cambridge.org/dictionary/english/<word>` and `.../english-russian/<word>`;
   the page is long — grep the saved file for `### ` (sense headings) and `Idioms`.
2. **Pick 4–10 branches** (the script caps at 10), most frequent first. One branch = one usable
   phrase, not an abstract sense: `call in sick`, not «болезнь (в контексте работы)».
   - `head`: the phrase as it is said, with a label if needed: `be sick (UK)`, `sick! (slang)`.
   - `tr`: 1–3 Russian equivalents, comma-separated.
   - `ex`: 1–2 examples, ≤8 words each, everyday or IT context. A second item may be a related
     collocation with its translation: `sick leave — больничный`.
   - `vs` — **only when a Russian speaker would really confuse it**: `ill`, `tired of`, US vs UK,
     register (`только неформально`). Skip it otherwise; an empty field is fine.
3. **Render:**
   ```
   write_file("$TMPDIR/wc/<word>.json", <spec>)
   terminal(command="uv run --with cairosvg python <skill_dir>/scripts/card.py $TMPDIR/wc/<word>.json $TMPDIR/wc/<word>.png", timeout=180)
   ```
   Spec:
   ```json
   {"word": "sick", "subtitle": "/sɪk/ · СИК",
    "items": [{"head": "sick of", "tr": "достало, сыт по горло",
               "ex": ["I'm sick of these flaky tests."], "vs": "tired of — мягче: «устал от»"}],
    "footer": "optional source line"}
   ```
   Layout is automatic: first half of the items go on top, one per side (from 4 items), rest at
   the bottom. Order the list accordingly.
4. **Check** the PNG with `vision_analyze`: nothing clipped, no overlaps, arrows don't cross text,
   Cyrillic and IPA render. Fix by shortening text, not by shrinking fonts.
5. **Send** `MEDIA:<path>.png` plus 2–4 lines of text: what's on the card, and anything left out.
   If `english-tutor` runs for this learner, offer to add the phrases to its SRS.

## Pitfalls

- Long `head` or `tr` wraps into many lines and makes its row tall — keep `head` ≤18 chars,
  `tr` ≤35. Side boxes are narrower (380 px) — put the shortest items at positions `n/2` and `n/2+1`.
- Wrapping width is estimated from average glyph width, so lines break a bit early; that's on purpose.
- Slang and region labels go into `head` or `vs` — never present slang as the neutral meaning.
- Self-check: `uv run --with cairosvg python scripts/card.py --selftest`.
