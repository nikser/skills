---
name: word-breakdown
description: "Pronunciation breakdown for Russian speakers + board image."
version: 1.0.0
author: Nikolay Efimov (nikser), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [english, pronunciation, phonics, russian-speakers, image]
    related_skills: [english-tutor]
---

# Word Breakdown

Explains how an English word or phrase is pronounced, the way a teacher does it on a whiteboard:
syllables, stress, letter → sound → **reading rule**, IPA, an approximate Cyrillic hint and the one trap
a Russian speaker is most likely to fall into. Each word also gets a PNG "whiteboard" card and a link to
real speech on [YouGlish](https://youglish.com). Explanations are written **in Russian** — the learner
is a Russian speaker; only the English material stays English.

On demand only: the learner says «разбери слова», «разбери фразу», «как произносится …» or sends a word list.

## When to Use

- «разбери слова / фразу», «как произносится X», a list of words from a lesson.
- Don't use for: judging the learner's own pronunciation — the agent doesn't hear audio, it only
  explains the reference pronunciation. Translation-only requests.

## Prerequisites

- Python 3 + `cairosvg` (run via `uv run --with cairosvg`, nothing installed globally).
- A font with Cyrillic and IPA glyphs: **DejaVu Sans / DejaVu Sans Mono** (`fonts-dejavu`).

## Procedure

1. **Text breakdown per word / phrase (in Russian):**
   - syllables with `|`, stressed one in capitals: `CU | cum | ber`;
   - **IPA** from a dictionary (UK / US if they differ) — never guessed from memory;
   - every non-obvious letter → sound → **why** (the rule, not just the result):
     c before e/i/y = [s], else [k]; open vs closed syllable; magic e works only under stress;
     unstressed er/or/a = [ə]; a doubled consonant keeps the vowel short (`car` [kɑː] vs `carry` [kæri]);
     s after a vowel or voiced consonant = [z]; qu = [kw];
   - Cyrillic hint, with the caveat that it is approximate;
   - ⚠️ **one trap** — the most likely one for a Russian speaker (list below).
2. **Whiteboard card per word** — rendered by script, not by an image model (those garble letters):
   ```
   write_file("$TMPDIR/wb/<slug>.json", <spec>)
   terminal(command="uv run --with cairosvg python <skill_dir>/scripts/board.py $TMPDIR/wb/<slug>.json $TMPDIR/wb/<slug>.png", timeout=180)
   ```
   Spec (only `syllables` is required; always fill `translation`):
   ```json
   {"syllables": ["cu", "cum", "ber"], "stress": [0],
    "above": {"0": "кью", "1": "а"}, "below": {"0": "c → [k]", "2": "er → [ə]"},
    "translation": "огурец", "ipa": "/ˈkjuː.kʌm.bə/", "hint": "КЬЮ-кам-бэ",
    "notes": ["c перед e/i/y = [s], иначе [k]"], "trap": "не «кукумбер»"}
   ```
   Phrase: a syllable that starts a new word begins with a space — `["long", " time", " no", " see"]`.
   Keep `above` / `below` labels short (~10 chars) or they collide with the neighbouring syllable;
   `translation` is 1–4 words, drawn in green under the word.
   Criterion: every PNG opened with `vision_analyze` — no overlaps, nothing clipped, Cyrillic and IPA render.
3. **Send** each card as `MEDIA:<path>.png` next to its text breakdown.
4. **Live examples** at the end: `https://youglish.com/pronounce/<word>/english`
   (spaces → `%20`; accent: `/english/us`, `/english/uk`) and, for movie/TV phrases,
   `https://getyarn.io/yarn-find?text=<phrase>`.
5. If `english-tutor` runs for this learner, add the words to its `data/srs.json` (box 0).

## Typical traps for Russian speakers

Pick the one that applies, don't list them all:

- **Final devoicing:** `mood` → «мут», `side` → «сайт». English keeps final b/d/g/v/z voiced,
  and the pair often changes the word (`mood` / `mute`).
- **«г» after ng:** `long` → «лонг». ng is one nasal sound [ŋ], no [g] at the end.
- **w as «в»:** `weak` → «вик». Lips rounded like «у», teeth don't touch the lip.
- **Reading by letters:** `series` → «сериес»; Russian stress on cognates: `episode` «эпизОд».
- **Stress shifted to the Russian pattern:** `frequency` «фреквЕнси», `develop`, `component`.
- **Unreduced vowels:** unstressed syllables pronounced fully instead of [ə] / [ɪ].
- **th** → «с / з / ф»; **short vs long** vowels (`ship` / `sheep`); **æ** read as «а» or «е».
- **Fast speech:** clusters drop a sound (`weakest side` → «уи́кис сайд») — explain it so the
  learner recognises it by ear.

## Pitfalls

- More than ~5 words — cards only for the hardest ones, ask about the rest; Telegram sends each as a separate photo.
- The word is set in a monospace font so the red syllable bars land exactly between letters;
  labels are centred on the syllable, not on a specific letter.
- Self-check: `uv run --with cairosvg python scripts/board.py --selftest`.
- YouGlish's free tier limits searches per day; Yarn returns 403 to bots, so its link can't be
  pre-checked — give it without promising results.
- No audio unless asked; if asked — `text_to_speech` with the word and an example sentence.
