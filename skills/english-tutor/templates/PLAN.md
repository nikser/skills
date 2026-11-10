# English program — <learner>

**Start:** <date> · **Entry level:** <self-assessed, verified by placement>
**Goal:** <e.g. B1, work English: calls, written communication, interviews>
**Example topics:** <learner's field>
**Schedule (<timezone>):** 3 micro-sessions a day — <e.g. 10:00 · 14:30 · 22:00>

## Sources the program is built from

| Source | Used for |
|---|---|
| CEFR / Council of Europe (A2→B1: 180–250 guided hours) | level frame, vocabulary targets (~1200 → ~3000 active words) |
| CEFR grammar scope & sequence | order of grammar A2 → B1 → B2, what not to teach too early |
| Cambridge English Profile | speech functions per level: opinion, agreeing, advice, argument |
| English-for-IT learning paths | contexts: standup, code review, incidents, email |
| STAR interview structure | behavioural interview answers |
| SM-2 style spaced repetition | review intervals 1/3/7/16/35/90 days |
| Murphy, English Grammar in Use | wording of short rule notes |

## Day structure

| Slot | What | Format |
|---|---|---|
| **A. Grammar** | rule of the day + 3 drills + 1 SRS review | one message, options a/b/c, answer as one line |
| **B. Vocabulary** | 5–7 collocations on the week's theme + 3 usage questions + 1 own sentence | same |
| **C. Production** | Mon–Sat: standup / PR comment / email / STAR answer; Sun: week summary | free text, 2–4 sentences |

Feedback comes **right after each answer**: ✅ what's right → ❌ learner's phrase → ✅ corrected →
📌 rule (why, not the term) → 🔁 tomorrow's check → ⭐ how a native speaker would say it. Max 3 errors at once.

## How difficulty grows

`difficulty` in `data/state.json` (1.0 = A2, 2.0 = B2 entry).

- **Up (+0.1):** 7-day accuracy ≥ 85% AND ≥ 2 ledger errors fixed.
- **Down (−0.1):** accuracy < 60% → repeat the week with more scaffolding.
- **Hold (60–85%):** follow the curriculum.

Higher difficulty = longer stimulus, closer distractors, more production (20% → 50%), more formal /
hedged register, timed "answer in one sentence" tasks.

## Files

```
$ENGLISH_TUTOR_DIR/
  PLAN.md  CURRICULUM.md  PROGRESS.md
  data/state.json  data/errors.json  data/srs.json
  logs/sessions.jsonl
```
