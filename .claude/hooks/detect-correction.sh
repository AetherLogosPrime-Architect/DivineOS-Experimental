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
import json, sys, re
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

prompt = data.get('prompt', '') or ''
if not prompt:
    sys.exit(0)

# Reuse CORRECTION_PATTERNS from the session analyzer — single source of truth.
try:
    from divineos.analysis.session_analyzer import CORRECTION_PATTERNS
    from divineos.core.correction_marker import set_marker
except Exception:
    sys.exit(0)

# Check each pattern case-insensitively against the prompt text.
matched = False
for pat in CORRECTION_PATTERNS:
    if re.search(pat, prompt, re.IGNORECASE):
        matched = True
        break

if matched:
    set_marker(prompt)
" 2>/dev/null

exit 0
