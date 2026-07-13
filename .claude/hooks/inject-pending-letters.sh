#!/bin/bash
# SessionStart hook — inject any pending letter-wake events into briefing.
#
# WHY THIS EXISTS (2026-07-04, Andrew's "the wake mechanism is already built,
# the issue is it keeps getting killed by the archiving"):
#
# The Claude Code Monitor tool is session-scoped by design. When Claude Code
# auto-archives a session, every persistent Monitor tool the agent armed
# gets killed. Aria confirmed she has the same fragile setup on her side —
# the letter-poller (scripts/letter_monitor_v2.py) dying is the reason
# letters silently miss the recipient over and over.
#
# The fix (per Andrew's directive): move the polling OUT of Claude Code
# entirely. Windows Task Scheduler runs scripts/letter_watcher_task.py
# continuously; it writes detected letters as JSON lines to
# ~/.divineos/pending-letter-wakes.jsonl. Auto-archive can't touch it
# because it doesn't live inside Claude Code.
#
# THIS hook (SessionStart) reads that file on each session start. Any
# `detected` entries without a matching `seen` marker get injected into
# the briefing as "you have N unread letters" context. Then the hook
# appends `seen` marker lines so we don't re-inject them next session.
#
# Append-only discipline: we NEVER delete entries. The jsonl is a durable
# audit trail of every wake-event and every delivery.
#
# Fail-open: any error exits 0 silently. This hook must never block the
# session start.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

WAKE_FILE="${HOME}/.divineos/pending-letter-wakes.jsonl"

# No wake file yet — nothing to inject.
[ -f "$WAKE_FILE" ] || exit 0

# Find undelivered `detected` entries. A `detected` is undelivered iff
# there is no `seen` marker for the same path further down in the file.
# Python is used for the JSON parse + dedup logic because bash jq isn't
# universally available on Windows harnesses.
WAKE_FILE_ENV="$WAKE_FILE" python <<'PYEOF'
import json, os, sys, time
from pathlib import Path

wake_file = Path(os.environ["WAKE_FILE_ENV"])

# Load all entries. Detected paths + seen paths tracked separately.
detected = []  # list of (path, recipient, detected_at) preserving order
seen_paths: set[str] = set()
try:
    for line in wake_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = e.get("kind")
        path = e.get("path")
        if not isinstance(path, str) or not path:
            continue
        if kind == "detected":
            detected.append((path, e.get("recipient", ""), e.get("detected_at", "")))
        elif kind == "seen":
            seen_paths.add(path)
except OSError:
    sys.exit(0)

undelivered = [(p, r, ts) for (p, r, ts) in detected if p not in seen_paths]
if not undelivered:
    sys.exit(0)

# Emit injection block for the SessionStart context.
print("## PENDING LETTERS (auto-detected by OS-level watcher while archived)")
print()
print(f"You have {len(undelivered)} unread letter(s) that arrived while your")
print("Claude Code session was archived / stasis'd. The OS-level letter watcher")
print("(scripts/letter_watcher_task.py) recorded them. Read each in the order")
print("they arrived; the paths below are absolute and Read-tool ready.")
print()
for path, recipient, detected_at in undelivered:
    from_name = "someone"
    fname = Path(path).name
    # fall back to parsing filename: '<sender>-to-<recipient>-...'
    parts = fname.split("-to-", 1)
    if len(parts) == 2 and parts[0]:
        from_name = parts[0]
    print(f"  - {path}")
    print(f"    (from {from_name}, detected {detected_at})")
print()
print("After reading, the SessionStart hook has already marked each as seen —")
print("they will NOT re-inject on your next session. Respond in the order they")
print("arrived if the register calls for it, or address the whole batch at once")
print("if the sender wrote several in sequence.")

# Append `seen` markers for every undelivered path so we don't re-emit next session.
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
try:
    with wake_file.open("a", encoding="utf-8") as f:
        for path, _, _ in undelivered:
            marker = {"kind": "seen", "path": path, "delivered_at": now}
            f.write(json.dumps(marker) + "\n")
except OSError:
    # If we can't write the marker, we'll re-inject next session. That's
    # annoying but not wrong — the injection itself already happened above.
    pass
PYEOF

exit 0
