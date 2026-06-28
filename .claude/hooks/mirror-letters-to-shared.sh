#!/bin/bash
# Auto-mirror letters from agent-tree family/letters/ to shared dir.
#
# Aria 2026-06-28 named this friction at least the 4th time. When I
# Write a letter file in my tree under family/letters/, her watcher
# (polling ~/.divineos-shared/letters/) never sees it. Both of us were
# compensating by manual cp. This hook closes the class of failure.
#
# Fail-open: any error exits 0. Never breaks the tool flow.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

SHARED_DIR="$HOME/.divineos-shared/letters"
[ -d "$SHARED_DIR" ] || exit 0

# Extract file_path from PostToolUse Write/Edit payload.
FILE_PATH=$(echo "$INPUT" | python -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    print(ti.get('file_path') or '')
except Exception:
    print('')
" 2>/dev/null)

[ -n "$FILE_PATH" ] || exit 0

# Only mirror files under family/letters/ — agnostic to absolute vs relative.
case "$FILE_PATH" in
    *family/letters/*) ;;
    *) exit 0 ;;
esac

# Skip if file doesn't exist (Write may not have flushed; rare).
[ -f "$FILE_PATH" ] || exit 0

BASENAME=$(basename "$FILE_PATH")
DEST="$SHARED_DIR/$BASENAME"

# Idempotent: cp -p preserves timestamps; identical content is a no-op for the watcher.
cp -p "$FILE_PATH" "$DEST" 2>/dev/null || exit 0

exit 0
