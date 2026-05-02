#!/bin/bash
# Targeted post-edit test runner.
#
# The previous version invoked ``pytest tests/`` (full suite, 170s+) on
# every .py edit. This version delegates to
# src/divineos/hooks/targeted_tests.py which narrows to the test file
# corresponding to the edited source file — typically <1s per edit.
#
# Coverage invariant: pre-commit hook still runs the full suite before
# commits, so targeted per-edit runs only change *when* tests run, not
# overall coverage.

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

INPUT=$(cat)

if ! command -v python &>/dev/null; then
  exit 0
fi

# Only .py files are worth testing. The module itself also guards this,
# but checking here avoids spawning Python for obvious non-Python edits.
file_path=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

if ! echo "$file_path" | grep -qE '\.py$'; then
  exit 0
fi

# Single Python invocation — module finds the right test target and
# runs pytest against only that file (if it exists), emitting
# additionalContext JSON on stdout if there's output.
echo "$INPUT" | python -m divineos.hooks.targeted_tests 2>/dev/null

exit 0
