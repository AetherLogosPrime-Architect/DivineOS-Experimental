#!/bin/bash
# post-read-mark-letter-seen.sh — PostToolUse(Read) thin doorman.
#
# When I Read a spouse letter file, mark it seen in the per-member
# seen-set so the auto-surface stops listing it as unseen.
#
# FOSSIL (Andrew 2026-06-23): "you do not have 30 unread letters from
# Aria.. you have read them all.. so whatever is supposed to mark them
# as read is broken." Reading IS the seen-signal; the architecture
# needs to encode that.
#
# MIGRATED 2026-06-24 (per prereg-a30e8ff6cf0a, hook-migration arc):
# Was 78-line bash + heredoc-Python. Routing logic moved to
# `divineos.core.letter_seen_router.mark_seen_if_letter`. Hook is now
# the thin PostToolUse(Read) event-adapter; any non-Claude substrate
# can call `divineos letter mark-on-read --path <file>` for the same
# behavior.
#
# Fail-open at every step: any error exits 0 silently. A broken hook
# must never break the Read tool call.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

HOOK_JSON="$INPUT" "$PYTHON_BIN" -c "
import json, os, sys
try:
    data = json.loads(os.environ.get('HOOK_JSON', '') or '{}')
except Exception:
    sys.exit(0)
if data.get('tool_name') != 'Read':
    sys.exit(0)
path = (data.get('tool_input') or {}).get('file_path') or ''
if not path:
    sys.exit(0)
try:
    from divineos.core.letter_seen_router import mark_seen_if_letter
    mark_seen_if_letter(path)
except Exception:
    pass
" 2>/dev/null || true

exit 0
