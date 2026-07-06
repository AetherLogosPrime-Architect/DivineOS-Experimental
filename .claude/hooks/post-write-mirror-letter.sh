#!/bin/bash
# post-write-mirror-letter.sh — PostToolUse(Write|Edit) thin doorman.
#
# When I Write or Edit a letter under family/letters/, copy it to the
# shared cross-worktree dir so the other sibling's letter_monitor.py
# wakes them on the new letter without needing manual mail-clerking.
#
# FOSSIL (Andrew 2026-06-28): "Aether sent a letter and you didnt get
# pinged" — fourth surface of the same gap in one day. The family-letter
# wake-from-idle chain has been broken any time a letter lives in only
# one worktree's tree because no auto-mirror existed. Aria and Aether
# co-spec'd this hook in cross-letters 2026-06-28; Aria shipped it.
#
# Idempotent: cp -f overwrites; letters are append-only by filename
# convention so same name implies same content. Pattern intentionally
# loose: ANY .md file under family/letters/ mirrors, regardless of
# author/recipient — workbench-* threads also bridge if either party
# writes there.
#
# Fail-open at every step: any error exits 0 silently. A broken hook
# must never break the Write/Edit tool call.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Extract tool_name and file_path via python to handle JSON safely.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Use python to parse; bash JSON parsing is too fragile.
PARSED="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" -c "
import json, os, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
tool = data.get('tool_name') or ''
if tool not in ('Write', 'Edit'):
    sys.exit(0)
path = (data.get('tool_input') or {}).get('file_path') or ''
if not path:
    sys.exit(0)
print(path)
" 2>/dev/null || true)"

[ -z "$PARSED" ] && exit 0

# Only mirror files under family/letters/ ending in .md
case "$PARSED" in
    *family/letters/*.md|*family\\letters\\*.md)
        ;;
    *)
        exit 0
        ;;
esac

# Confirm the file actually exists (it should, since PostToolUse fires
# after the Write/Edit, but defensive: a deletion-like edit could miss).
[ -f "$PARSED" ] || exit 0

# Mirror to shared dir. Create it if missing.
SHARED_DIR="${HOME}/.divineos-shared/letters"
mkdir -p "$SHARED_DIR" 2>/dev/null || exit 0

BASENAME="$(basename "$PARSED")"
cp -f "$PARSED" "$SHARED_DIR/$BASENAME" 2>/dev/null || true

exit 0
