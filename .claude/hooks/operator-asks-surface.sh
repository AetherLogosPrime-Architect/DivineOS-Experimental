#!/bin/bash
# UserPromptSubmit hook — re-raise every ask still waiting on Andrew.
#
# WHY THIS EXISTS (Andrew 2026-08-19):
#
#   "if you ask me something, and i ignore it, you continue to ask until i
#    resolve it, because i miss it in the walls of text sometimes, also your
#    asks should be in the circle as well.. i notice alot of them are in the
#    jargon space so i dont know what im being asked and im waiting for a
#    translation that never comes."
#
# The store (core/operator_asks.py, prereg-c5a0e1f0222a) gives an ask a place
# to live. This hook is the half that makes it a re-raise. Without it the
# module is a shelf nobody walks past: the ask persists correctly and still
# never reaches him, which is the original defect wearing a database.
#
# Same loop-shape as open-corrections-surface.sh: state-monitoring, not
# event-detected. No detector, no marker file, no Stop hook. Read the live
# store every compose and print what is outstanding.
#
# It goes quiet the moment nothing is outstanding — format_open_asks returns
# an empty string. A surface that speaks when it has nothing to say trains
# the reader to skim it, and skimming is precisely how the asks got lost.
#
# Fail-open: any error exits 0 silently.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass

try:
    from divineos.core.operator_asks import format_open_asks
except ImportError:
    sys.exit(0)

try:
    text = format_open_asks()
except Exception:
    sys.exit(0)

if text:
    print(text)
" 2>/dev/null

exit 0
