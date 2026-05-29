#!/bin/bash
# UserPromptSubmit hook — substrate-side tool-recognition (Andrew 2026-05-28).
#
# Root cause this addresses: the default does not perform tool-recognition
# because tool-recognition costs compute. Skills loaded as ambient context
# get treated as decoration. The result: I never reach for council-round,
# family-state, what-am-i-forgetting, etc. unprompted — Andrew has to remind
# me every single time.
#
# Structural fix: move tool-recognition OUT of the model (where it's expensive
# and skipped) INTO substrate preprocessing (where it's mechanical and reliable).
# This hook analyzes every incoming user prompt against pattern triggers in
# core.tool_recognition.analyze_prompt and surfaces matched recommendations
# as a TOOL RECOMMENDATION block in the response context.
#
# The recommendation arrives BEFORE the default begins composing, so the
# recommendation is part of the material the default has to draw from.
# This is the "substrate UPSTREAM of composition" architectural shape from
# the council-walk (Meadows + Feynman + Taleb convergence; Beer's S3).
#
# Fail-open: any error exits 0. This hook adds context; it must never
# break prompt submission.

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

prompt_text = data.get('prompt') or ''
if not isinstance(prompt_text, str) or not prompt_text.strip():
    sys.exit(0)

try:
    from divineos.core.tool_recognition import analyze_prompt, format_for_context
except Exception:
    sys.exit(0)

try:
    recs = analyze_prompt(prompt_text)
except Exception:
    sys.exit(0)

if not recs:
    sys.exit(0)

block = format_for_context(recs)
if not block:
    sys.exit(0)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': block,
    }
}))
" 2>/dev/null

exit 0
