#!/bin/bash
# UserPromptSubmit hook — detect correction-shaped language in user input.
#
# If the user's latest message matches any CORRECTION_PATTERNS (imperative
# pushback: "no", "wrong", "don't do that", "you missed", etc.), write a
# marker file at ~/.divineos/correction_unlogged.json. The PreToolUse gate
# reads this marker and blocks non-bypass tools until the correction is
# logged via `divineos learn` or `divineos correction`.
#
# Closes the enforcement gap from ChatGPT audit claim-964493
# (theater-learning bypass) by converting "I should log corrections" from
# intent into structural requirement.
#
# Fail-open: any error here exits 0 without blocking, so a broken hook
# doesn't break the user's session.

INPUT=$(cat)

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 0

if ! command -v python &>/dev/null; then
  exit 0
fi

# Delegate to Python — regex matching + marker write in one interpreter call.
echo "$INPUT" | python -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

prompt = data.get('prompt', '') or ''
if not prompt:
    sys.exit(0)

try:
    from divineos.core.correction_marker import set_marker, should_mark
except Exception:
    sys.exit(0)

if should_mark(prompt):
    set_marker(prompt)
" 2>/dev/null

exit 0
