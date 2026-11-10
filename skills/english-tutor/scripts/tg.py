#!/usr/bin/env python3
"""Send Telegram messages / quiz polls into the learner's chat (or forum topic).

Usage:
    python3 tg.py payload.json          # file with a list of items
    echo '[{...}]' | python3 tg.py -    # stdin

Item shapes:
    {"type": "msg",  "text": "..."}
    {"type": "quiz", "q": "...", "options": ["a","b","c"], "correct": 0,
     "explain": "короткое правило (<=200 симв)"}
    {"type": "poll", "q": "...", "options": [...], "multiple": false}

Telegram hard limits (exceeded = HTTP 400):
    question <= 300 chars, option <= 100 chars, explanation <= 200 chars,
    2..10 options, quiz polls are always non-anonymous-safe in groups.
Exit code 1 if any item failed; prints per-item status + message_id/poll_id.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Config: TELEGRAM_BOT_TOKEN, TUTOR_CHAT_ID, optional TUTOR_THREAD_ID (forum topic) — from the
# process env, else from TUTOR_ENV_FILE (dotenv, default $HERMES_HOME/.env).
ENV_PATH = os.environ.get("TUTOR_ENV_FILE",
                          os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), ".env"))
API = "https://api.telegram.org/bot{token}/{method}"


def setting(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key].strip()
    try:
        with open(ENV_PATH) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return ""


CHAT_ID = setting("TUTOR_CHAT_ID")
THREAD_ID = setting("TUTOR_THREAD_ID")


def token() -> str:
    tok = setting("TELEGRAM_BOT_TOKEN")
    if not tok:
        raise SystemExit("TELEGRAM_BOT_TOKEN not found")
    return tok


def call(method: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API.format(token=token(), method=method),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": exc.read().decode()}


def check(item: dict) -> str | None:
    if item.get("type") == "msg":
        return None if item.get("text") else "empty text"
    q, opts = item.get("q", ""), item.get("options") or []
    if len(q) > 300:
        return f"question {len(q)} chars > 300"
    if not 2 <= len(opts) <= 10:
        return f"{len(opts)} options (need 2-10)"
    bad = [o for o in opts if len(o) > 100]
    if bad:
        return f"option too long: {bad[0][:40]}..."
    if len(item.get("explain", "")) > 200:
        return f"explanation {len(item['explain'])} chars > 200"
    if item.get("type") == "quiz" and not isinstance(item.get("correct"), int):
        return "quiz needs integer 'correct'"
    return None


def send(item: dict) -> dict:
    if not CHAT_ID:
        raise SystemExit("TUTOR_CHAT_ID is not set")
    base = {"chat_id": CHAT_ID}
    if THREAD_ID:
        base["message_thread_id"] = THREAD_ID
    kind = item.get("type", "quiz")
    if kind == "msg":
        return call("sendMessage", {**base, "text": item["text"],
                                    "parse_mode": item.get("parse_mode", "Markdown"),
                                    "disable_web_page_preview": True})
    poll = {**base, "question": item["q"], "options": item["options"],
            "is_anonymous": False}
    if kind == "quiz":
        poll.update(type="quiz", correct_option_id=item["correct"],
                    explanation=item.get("explain", ""),
                    explanation_parse_mode="Markdown")
    else:
        poll.update(type="regular",
                    allows_multiple_answers=bool(item.get("multiple")))
    return call("sendPoll", poll)


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.read() if src == "-" else open(src).read()
    items = json.loads(raw)
    if isinstance(items, dict):
        items = [items]
    failed = 0
    for i, item in enumerate(items, 1):
        err = check(item)
        if err:
            print(f"[{i}] SKIP invalid: {err}")
            failed += 1
            continue
        res = send(item)
        if res.get("ok"):
            r = res["result"]
            pid = (r.get("poll") or {}).get("id", "-")
            print(f"[{i}] ok msg_id={r.get('message_id')} poll_id={pid}")
        else:
            print(f"[{i}] FAIL {res.get('error') or res}")
            failed += 1
        time.sleep(0.8)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
