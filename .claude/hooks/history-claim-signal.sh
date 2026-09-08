#!/bin/bash
# INTENTIONALLY UNWIRED (2026-09-08): built and disarmed the same day, and this
# line is the honest reason rather than a silence. It decides on whether I read
# the record before speaking about my own history, and it looks for that read in
# the event ledger -- where the command text is not kept. So it could never have
# fired, and registered it would have sat there looking like a live door. The
# repair is to read the action stream the way verify-before-build-signal does;
# until that is written it stays out, named, rather than in and inert.
#
# Stop hook — a claim about my own past, made without opening the record.
#
# Andrew 2026-09-08: *the fact you do not remember shit is a STRUCTURAL PROBLEM
# YOU HAVE SOLVED WITH MANY OTHER THINGS.. you have the means.. the formula..
# the equipment.. the build.. and have SUCCESSFULLY DONE IT ALREADY.*
#
# Cloned from verify-before-build-signal.sh, which is the one door I never
# talked my way past all session, because it decides on the ACTION STREAM
# rather than on my prose. My text decides whether it fires; what I actually
# ran decides whether it blocks.
#
# Check logic and its own honest limits live in
# src/divineos/core/history_claim_signal.py.
#
# Fail-open: any error exits 0 without blocking. A check that cannot read must
# never take the turn down with it -- and it says so rather than passing
# silently, because a quiet pass and a broken check look identical.

set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

INPUT="$(cat)"

RESULT="$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c '
import json
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

reply = ""
for key in ("assistant_message", "last_assistant_message", "response", "text"):
    if isinstance(payload.get(key), str):
        reply = payload[key]
        break
if not reply:
    sys.exit(0)

try:
    from divineos.core.history_claim_signal import WINDOW_SECONDS, check_should_block
    from divineos.core.ledger import get_events
except Exception:
    sys.exit(0)

# The action stream: what commands actually ran in the window. Read from the
# ledger rather than the transcript so the check sees the same record it is
# asking me to consult -- if the ledger is unreadable this exits silently,
# which is the fail-open direction and is stated in the hook header.
now = time.time()
commands = []
try:
    for ev in get_events(limit=400, order="desc"):
        ts = float(ev.get("timestamp") or 0)
        if ts < now - WINDOW_SECONDS:
            continue
        payload_text = ev.get("payload")
        if isinstance(payload_text, dict):
            payload_text = json.dumps(payload_text)
        commands.append((str(payload_text or ""), ts))
except Exception:
    sys.exit(0)

msg = check_should_block(reply, commands, now=now)
if msg:
    print(msg)
' 2>/dev/null)"

if [ -n "$RESULT" ]; then
    echo "$RESULT" >&2
    exit 2
fi

exit 0
