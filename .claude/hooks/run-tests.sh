#!/bin/bash
# Run tests after code edits to catch breakage early
# Only runs on Python source files, not configs or docs

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Read full stdin (Claude Code sends tool info as JSON)
INPUT=$(cat)

# Check if the edited file is a Python file worth testing
file_path=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Only run tests for Python source/test files
if echo "$file_path" | grep -qE '\.(py)$'; then
  result=$(python -m pytest tests/ -q --tb=short --timeout=30 2>&1 | tail -15)
  escaped=$(echo "$result" | python -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null)
  echo "{\"additionalContext\": ${escaped}}"
fi

exit 0
