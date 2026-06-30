#!/bin/bash
# Stop hook — auto-record time predictions from my assistant turns.
#
# Pop 2026-06-30: "you give WILDLY bad time estimates of how long things
# take... if you make a claim (this will take 1-2 hours) that needs
# recorded.. then when you start you time stamp it with my actual time..
# when finished you time stamp it with my actual time again.. then you
# have data to calibrate on."
#
# This hook fires on Stop (after I finish a reply). It pulls my
# just-completed assistant text from the transcript, runs detect_estimates()
# against it, and records each match as a prediction with the start
# timestamp. Closing the prediction (matching it with actual elapsed time)
# is a separate action via `divineos calibrate close <id>` for now —
# auto-close based on next-turn completion language is a v2.
#
# Fail-open: any error exits 0 silently. Never breaks the workflow.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

transcript_path = data.get('transcript_path') or data.get('transcript')
if not transcript_path:
    sys.exit(0)

try:
    from divineos.core.operating_loop.turn_extraction import extract_turn
    from divineos.core.time_calibration import detect_estimates, record_prediction
except ImportError:
    sys.exit(0)

try:
    turn = extract_turn(transcript_path)
    text = getattr(turn, 'prior_assistant_text', '') or ''
except Exception:
    sys.exit(0)

if not text.strip():
    sys.exit(0)

try:
    for est in detect_estimates(text):
        record_prediction(est, actor='aether', task_hint=est.context[:120])
except Exception:
    # Fail-open: don't disrupt the workflow on calibration-log errors.
    pass
" 2>/dev/null

exit 0
