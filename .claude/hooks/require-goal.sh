#!/bin/bash
# PreToolUse gate — consolidated into a single Python invocation.
#
# The previous version spawned 5 separate Python interpreters (~1.2s on
# Windows). This version delegates all gate logic to a single module
# invocation, reducing overhead to ~200-300ms per tool call.
#
# See src/divineos/hooks/pre_tool_use_gate.py for the gate logic.
# Uses JSON deny to ACTUALLY block — exit 1 does nothing in Claude Code.

INPUT=$(cat)

# remedy-allowlist: no gate may block another gate's prescribed exit (Andrew 2026-08-18).
if [ -f "$(dirname "$0")/lib/remedy_allowlist.sh" ]; then
  # HOOK_NAME is read by remedy_pass_through inside the sourced library, and
  # the analyser cannot follow a path built at runtime, so it reports an unused
  # variable and an unresolvable source. Both are it being unable to look, not
  # a defect here. Without the directive below the whole wiring is
  # uncommittable, which is how it came to sit on disk unversioned.
  # shellcheck disable=SC2034
  HOOK_NAME="$(basename "$0")"
  # shellcheck disable=SC1091
  . "$(dirname "$0")/lib/remedy_allowlist.sh"
  remedy_pass_through "$INPUT" || true  # fail-soft: non-zero from remedy_pass_through means NOT-A-REMEDY, which is the ordinary case for almost every command; under set -e that ordinary answer would abort this hook before it ran its own check. The function exits 0 itself when the command IS a remedy some other gate prescribed, so reaching this line at all already means allow-and-continue.
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 1

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Single Python invocation — all imports happen once, all gates checked,
# a single JSON decision is emitted to stdout (or empty = allow).
echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.pre_tool_use_gate 2>/dev/null

exit 0
