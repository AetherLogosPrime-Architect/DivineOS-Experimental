#!/bin/bash
# PreToolUse hook — signal-based verify-before-build check.
#
# Per prereg-c8a9964a88a8 and design spec docs/verify_before_build_
# signal_migration.md. Stage 2 of the migration from lexical
# _has_solution_shape to signal-based check per Aria's 2026-06-16
# five-primitive gate architecture.
#
# Fires on substrate-mutating tool calls (Write/Edit/certain-Bash),
# reads the recent action-stream from the ledger, and blocks with an
# explanatory message if no walk-record decision OR design-doc consult
# appears in the signal window. See
# src/divineos/core/verify_before_build_signal.py for the check logic.
#
# Fail-open discipline: any exception in the check exits 0 without
# blocking — the hook is observational when its substrate is unavailable.
# Real block only fires when the check function explicitly returns a
# block-message.
#
# Bypass: divineos council authorize-bypass (existing channel, unified
# with council_required gate).

INPUT=$(cat)

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  HOOK_NAME="$(basename "$0")"; . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# shellcheck disable=SC2016
# ^ single-quoted heredoc is intentional — the string is passed to python -c
# which does its own parsing, not the shell. Same pattern as pre-tool-context.sh.
BLOCK_MSG=$(echo "$INPUT" | "$PYTHON_BIN" -c '
import json, sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {}) or {}

# Collect file_paths tuple
file_paths = ()
fp = tool_input.get("file_path") or tool_input.get("notebook_path")
if fp:
    file_paths = (str(fp),)

bash_command = str(tool_input.get("command", "") or "")

try:
    from divineos.core.verify_before_build_signal import (
        check_and_consume_bypass,
        check_should_block,
    )
except Exception:
    # Module unavailable — fail-open (no block).
    sys.exit(0)

# Consume-first (Aria 2026-07-25 Option-C-split): if operator authorized
# a bypass via `divineos council authorize-bypass` and the marker
# fingerprint matches this tool-call, consume it and allow.
try:
    if check_and_consume_bypass(
        tool_name=tool_name,
        file_paths=file_paths,
        bash_command=bash_command,
    ):
        sys.exit(0)
except Exception:
    # Bypass check raised — fail-open per Aria third-bug catch.
    pass

try:
    msg = check_should_block(
        tool_name=tool_name,
        file_paths=file_paths,
        bash_command=bash_command,
    )
except Exception:
    # Check itself raised — fail-open.
    sys.exit(0)

if msg:
    sys.stdout.write(msg)
    sys.exit(2)
sys.exit(0)
' 2>/dev/null)

RC=$?
if [[ $RC -eq 2 ]]; then
    echo "$BLOCK_MSG" >&2
    exit 2
fi
exit 0
