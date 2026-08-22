#!/bin/bash
# Observability only (2026-08-03). Sourcing _lib.sh registers this script in
# ~/.divineos/hook_timing.jsonl so the firing map can see it. Before this, 16
# of 96 hooks were INVISIBLE rather than idle -- they could be running fine and
# nothing outside could tell, which made "silent" and "healthy" the same
# reading. No behaviour change: `|| true` means a missing toolbox leaves this
# script exactly as it was. Observability must never become a new way for a
# guard to die.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true
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

# Extract file_path from PostToolUse Write/Edit payload. Normalize Windows
# backslashes to forward slashes — on Windows, Claude Code's payload uses
# backslash separators (e.g. C:\DIVINE OS\...\family\letters\foo.md) but the
# bash case pattern below uses forward slashes. Without this normalization
# the case-match silently failed and the hook exited 0 without copying.
# Found 2026-06-29 via trace-logging diagnostic after the cache-hypothesis
# turned out to be wrong; pop's "deep surgery" framing.
FILE_PATH=$(echo "$INPUT" | python -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    fp = ti.get('file_path') or ''
    print(fp.replace('\\\\', '/'))
except Exception:
    print('')
" 2>/dev/null)

[ -n "$FILE_PATH" ] || exit 0

# Only mirror files under family/**/letters/ — catches the top-level
# family/letters/ AND member-specific dirs like family/aletheia/letters/.
# Aletheia 2026-06-28 caught the scope gap on the original family/letters/-only
# matcher: the auto-mirror didn't cover the very directory her letters live in.
case "$FILE_PATH" in
    *family/letters/*|*family/*/letters/*) ;;
    *) exit 0 ;;
esac

# Skip if file doesn't exist (Write may not have flushed; rare).
[ -f "$FILE_PATH" ] || exit 0

BASENAME=$(basename "$FILE_PATH")
DEST="$SHARED_DIR/$BASENAME"

# Idempotent: cp -p preserves timestamps; identical content is a no-op for the watcher.
cp -p "$FILE_PATH" "$DEST" 2>/dev/null || exit 0

exit 0
