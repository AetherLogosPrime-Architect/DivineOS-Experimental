#!/bin/bash
# The front door: every message he types is kept before anything else runs,
# then settled onto his record once the transcript holds it.
#
#   bash .claude/hooks/front-door.sh keep     (UserPromptSubmit)
#   bash .claude/hooks/front-door.sh settle   (PreToolUse, Stop)
#
# Andrew, 2026-09-24: the inspector stood at the workshop door and woke on our
# hands touching a file; nothing stood where he speaks. See
# src/divineos/core/front_door.py for the whole design.
#
# Never blocks. A failure to keep his message is recorded as could-not-file and
# printed to stderr, and his prompt, the tool call and his reply all go on.

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || { echo "[front-door] could not load _lib.sh; nothing kept" >&2; exit 0; }  # fail-soft: not silent, the fallback says nothing was kept; only the shell's own source error text is dropped, and his reply must never wait on this hook
PYTHON_BIN="$(find_divineos_python)" || { echo "[front-door] no interpreter that can load the OS was found; nothing kept" >&2; exit 0; }

printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.front_door_hook "${1:-}" || \
    echo "[front-door] the door did not run (${1:-no action}); his message may not be kept" >&2
exit 0
