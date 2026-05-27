#!/bin/bash
# record-wisdom-read.sh — PostToolUse hook (matcher: Read|Grep|Glob).
#
# Keel-improvement (Andrew 2026-05-26, council decision 5d8bf472): reading a
# WISDOM file (my own accumulated teachings/corrections/explorations/letters)
# is genuine substrate-consultation, so it should reset the consultation gate
# the same way `divineos ask`/`recall` do. Without this, the gate false-fires
# SEVERE while I am deep in legitimate wisdom-reading.
#
# The scope decision (which paths count) lives in consultation_tracker.
# record_wisdom_read; this hook just forwards tool_name + path and lets the
# tracker double-check. Fail-soft and silent: a hook that errors must never
# break the tool call. Exits 0 always.

set -u

# Read the PostToolUse stdin JSON (tool_name + tool_input.{file_path,path}).
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Resolve the divineos-capable Python via _lib.sh (NOT bare `python`): a bare
# interpreter that lacks divineos's deps would fail-OPEN silently and never
# record the consult. Convention enforced by tests/test_hook_python_lookup.py.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Pass the JSON via env var, NOT a pipe: the heredoc below is itself the
# script on stdin, so piping INPUT would be overridden by the heredoc
# (shellcheck SC2259). Env var sidesteps the conflict cleanly.
HOOK_JSON="$INPUT" "$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
import json, os, sys
try:
    data = json.loads(os.environ.get("HOOK_JSON", "") or "{}")
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")
if tool not in ("Read", "Grep", "Glob"):
    sys.exit(0)

inp = data.get("tool_input", {}) or {}
path = inp.get("file_path") or inp.get("path") or ""
if not path:
    sys.exit(0)

try:
    from divineos.core.consultation_tracker import record_wisdom_read
    record_wisdom_read(path)
except Exception:
    pass
PYEOF
exit 0
