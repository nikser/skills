---
name: english-tutor
description: "Run 3-a-day English drills in Telegram, track errors."
version: 1.0.0
author: Nikolay Efimov (nikser), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [english, teaching, spaced-repetition, telegram, cron]
    related_skills: [word-breakdown]
---

# English Tutor

Runs a personal English program (default: A2 → B1+, work/IT English) as three micro-sessions a day
in a Telegram chat: rule notes, multiple-choice drills answered as one line of letters, free-text
production, immediate feedback, an error ledger, spaced repetition and automatic difficulty steps.
The program itself lives in files (`PLAN.md`, `CURRICULUM.md`); the skill executes it and keeps
progress. Explanations are written in the learner's native language (`state.json → native_language`);
the pitfalls below are tuned for Russian speakers but the mechanics are language-neutral.

## When to Use

- A cron slot of the program fires (morning / midday / evening).
- The learner answers a block, sends free text, or asks for feedback / an extra task.
- Setting up the program for a new learner, changing schedule, difficulty or topics.
- Don't use for: translation requests, one-off grammar questions outside a program,
  pronunciation of single words (use `word-breakdown`).

## Prerequisites

- `ENGLISH_TUTOR_DIR` — working dir (default `~/english-tutor`).
- `TELEGRAM_BOT_TOKEN`, `TUTOR_CHAT_ID`, optional `TUTOR_THREAD_ID` (forum topic). `scripts/tg.py`
  reads the token from env or from `$TUTOR_ENV_FILE` (default `$HERMES_HOME/.env`).
- Optional, voice slot only: `ffmpeg` and an STT provider configured in Hermes.

## Setup (once per learner)

1. Copy `templates/` into `$ENGLISH_TUTOR_DIR` (`data/` included), create `logs/sessions.jsonl` and an
   empty `PROGRESS.md`.
2. Ask the learner (one form): self-assessed level, goal, topics of interest, answer format.
   Fill `state.json` and the header of `PLAN.md`.
3. Create three `cronjob` jobs (one per slot) with `skills: ["english-tutor"]`, `deliver: "local"`
   (the slot sends its own messages via `tg.py`) and `failure_deliver` pointing to the learner's chat.
   Cron runs in UTC: convert the learner's local times, and schedule a one-shot job on the next DST
   change that rewrites all three schedules.
4. Day 1 = placement test (see `CURRICULUM.md`). Criterion: `placement_done: true` and
   `verified_level` set from the learner's actual answers, not from self-assessment.

## Sending

```
write_file("$ENGLISH_TUTOR_DIR/data/outbox.json", [ ...items... ])
terminal(command="python3 <skill_dir>/scripts/tg.py $ENGLISH_TUTOR_DIR/data/outbox.json", timeout=120)
```

Items: `{"type":"msg","text":"...","parse_mode":"HTML"}`, `{"type":"quiz","q":...,"options":[...],"correct":0,"explain":...}`.
Telegram limits (else HTTP 400): question ≤300, option ≤100, explanation ≤200 chars, 2–10 options.
Criterion: every item printed `ok msg_id=...`, exit code 0.

## Capturing answers (the core constraint)

**Telegram quiz polls are not a data source.** Answers to polls arrive as `poll_answer` updates, which
Hermes' gateway does not route into the session — the agent never sees them. Asking the learner to
retype poll verdicts ("1 right, 2 wrong") fails in practice: fragments arrive without block labels.

Working scheme:

1. A slot's questions go out as **one `msg`**: numbered, options a/b/c, `parse_mode: HTML`
   (`___` blanks break Markdown).
2. End with: "Reply with one line, e.g. `A1c A2a A3b` (format sample, not the key)."
3. **Write the key to `state.json → pending_answer_key` BEFORE sending**, with `example_shown`.
   A cron session has no chat context; without a stored key the answer cannot be graded.
4. **Spread correct answers across letters**: never all the same letter, no more than two equal in a row.
5. **The format sample must differ from the key in ≥2 positions — and from samples of all previous
   blocks.** A sample equal to the key makes the block unmeasurable.
6. Polls may be added only as self-check (instant rule display), never instead of the text block.

### Grading

- Match an incoming line to a key by **reply-to message first**, then by prefix and number of answers.
  If the learner replies to the block's message, ignore a wrong or missing prefix.
- Several open blocks: give each its own prefix letter (A, B, Q, R…). **Keep ≤3 open keys**; close keys
  older than 72 h without verdict (topics stay in SRS) and say so.
- Duplicate / missing numbers in a line: grade the unambiguous items, ask about the rest in one short
  line, keep the block out of accuracy until clarified.
- **Never invent a verdict.** Lost key → recover it from the outbox file; nothing to recover → say so.
- A block with a construction flaw (all-same-letter key, sample = key) is **not counted**: no SRS moves,
  no ledger credit, no accuracy. Tell the learner why and send a recheck with shuffled positions.
- Don't recompute the level until there is a verdict for **every** item of a test — partial replies are not totals.

## Procedure (one slot)

1. **Read state:** `state.json`, `errors.json`, `srs.json`, last 2–3 lines of `logs/sessions.jsonl`.
   Grade any pending answers first (format below), then build the slot.
2. **Build the slot** from `CURRICULUM.md` for the current week:
   - **A:** rule note (3–5 lines, one work example) + 3 drills + 1 SRS/ledger review item.
   - **B:** 5–7 collocations + 3 usage questions + 1 "write your own sentence with …".
   - **C:** production in the week's genre (standup, PR comment, email, STAR answer); Sunday — week summary.
   At most **one open production task**: learners answer letters readily but skip text when several pile up.
   Criterion: ≤5 messages per `tg.py` run, questions numbered `1/4…4/4` inside the text.
3. **Difficulty:** 1.0–1.2 short stimulus, coarse distractors; 1.3–1.6 longer stimulus, close
   distractors, ~50% production; 1.7–2.0 paragraph stimulus, register and hedging, timed one-liners.
4. **Feedback — immediately after every answer**, in this shape, max 3 errors:
   ```
   ✅ What's right: <one concrete line>
   ❌ <learner's phrase>
   ✅ <corrected phrase>
   📌 Rule: <1–2 lines — WHY, i.e. what meaning changes>
   🔁 Tomorrow's check: <topic>
   ⭐ How a native speaker would say it: <natural version of the same thought>
   ```
   No errors → say so and raise the bar of the next task.
5. **Ledger** (`errors.json`): new pattern → `{id, pattern, example_wrong, example_right, rule,
   status:"open", first_seen, hits, correct_streak}`; repeat → `hits+1`, `correct_streak=0`, `drilling`.
   **Fixed** = 3 correct on ≥3 different days, last ≥7 days after the first. Same-day answers count once.
   Never relax the 7-day rule to make a step happen.
6. **SRS:** new item → box 0, due tomorrow; correct → box+1, due = today + intervals[box]; wrong → box 0.
7. **Log:** one line in `sessions.jsonl` `{date, slot, week, day, difficulty, topic, asked, correct,
   errors_new, errors_fixed, note}`; evening slot adds a short paragraph to `PROGRESS.md`.
8. **Level step** (once a day max): 7-day accuracy ≥85% AND ≥2 fixed errors → `difficulty += 0.1`;
   <60% → `-0.1` and repeat the week. Criterion: `state.json` matches the last log line.

## What the first weeks of real use showed

- **Grammar rules fix in 1–2 days, calques don't.** "had a problem" for "ran into an issue" returns
  again and again: rules are understood once, phrases must be met many times. Drill calques in
  production, not multiple choice — learners recognise them in a/b/c and still can't produce them.
- **Production beats letter choice as evidence.** A rule failed in a block and used correctly in free
  text an hour later — trust the text. And the reverse: perfect a/b/c on articles, then articles lost in
  the same day's standup → reset the streak.
- **Errors flip.** First the present perfect is missing, a week later it's overused ("we've had a
  workaround"). Teach contrastive pairs in one question, not rules in isolation.
- **The 7-day rule holds difficulty flat for the first 8–10 days.** Raise the bar inside tasks instead
  (longer text, hedging, tense contrast) and tell the learner why, or it looks like stalling.
- **Placement must be graded per item.** A partial reply read as a total once pushed a plan two levels
  down and had to be rewritten.

## Voice slot (optional)

Only with a working STT provider. The agent never hears audio — only the transcript. Format: shadowing
a given target sentence (store it in `state.json → pending_voice_target`); every 4th time a free
40-second standup. `scripts/voice.py AUDIO --text '<transcript>' --target '<sentence>'` measures pace,
pauses, pitch range, phrase-final direction and words the recogniser lost. Report only those;
**never judge individual phonemes or accent** — it can't be measured from a transcript.
No STT → don't offer the slot.

## Pitfalls

- Cron sessions don't see the chat; step 1 is mandatory.
- In unattended cron runs, shell `python3 -c` / `execute_code` may be blocked by approvals — use
  `read_file` / `patch` / `write_file` for state.
- Don't rewrite `PLAN.md` / `CURRICULUM.md` mid-program without the learner's decision.
- Missed slot is not made up with double load: its items go to SRS.
- Pause = pause the three cron jobs and close open keys without verdict; on resume start with a short
  entry block (3 items on the stickiest errors + 2 sentences), full load only after the first answer.

## Verification

- `tg.py` printed `ok` for every item; key present in `state.json` before the send.
- `errors.json` has no duplicate patterns and no entry without a rule.
- `day` / `week` / `difficulty` in `state.json` agree with the last `sessions.jsonl` line.
