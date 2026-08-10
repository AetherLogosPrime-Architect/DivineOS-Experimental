#!/bin/bash
# PreToolUse(Bash) — catch shell commands whose behaviour I assumed.
#
# Andrew 2026-08-10: "lets look for a way to automate some stuff to help ok?"
# Thirteen of the day's failures were one shape: a command that returned a
# plausible wrong answer with exit code 0. Those are the only ones automated
# here — a traceback is already its own alarm (Einstein lens).
#
# Design from council walk walk-eba3cfa75aa4 (10 lenses, high gravity).
# Two lenses argued against a lint at all (Dijkstra: testing shows presence
# not absence; Norman: slips need forcing functions, not labels), which is
# why exactly one rule BLOCKS — the one whose fault is exactly specifiable —
# and the rest only speak. Lamport: a rule I cannot specify exactly must
# never block.
#
# Fail-open: if the lint itself breaks, Bash keeps working. A guard that can
# halt my hands when IT is broken is worse than the traps it watches for.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PAYLOAD="$(cat)"

DECISION=$(PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c '
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

try:
    payload = json.loads(sys.stdin.read() or "{}")
except (ValueError, TypeError):
    sys.exit(0)

command = (payload.get("tool_input") or {}).get("command") or ""
if not command:
    sys.exit(0)

try:
    from divineos.hooks.bash_trap_lint import check, should_block
except ImportError:
    sys.exit(0)

fires = check(command)
if not fires:
    sys.exit(0)

for fire in fires:
    print(fire.render())

if should_block(fires):
    sys.exit(2)
' <<<"$PAYLOAD" 2>/dev/null)
STATUS=$?

if [[ -n "$DECISION" ]]; then
    echo "$DECISION" >&2
fi

exit "$STATUS"
