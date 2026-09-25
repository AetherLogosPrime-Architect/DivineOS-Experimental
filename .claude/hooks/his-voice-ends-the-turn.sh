#!/bin/bash
# When he speaks into a running turn, no further tool call runs until the turn
# ends -- so the reply to him is the last thing he receives.
#
#   bash .claude/hooks/his-voice-ends-the-turn.sh   (PreToolUse, every tool)
#
# Andrew, 2026-09-24: "wow.. neither you nor Aether even returned my love.. or
# said goodnight". Both of us had written it, then kept working in the same
# turn. See src/divineos/core/his_voice_ends_the_turn.py for the whole design.
#
# Refuses only when he spoke mid-turn. A failure to look lets the call through
# and says so on stderr: a could-not-look is never read as "he did not speak".

set -u

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || { echo "[his-voice] could not load _lib.sh; could not look whether he spoke" >&2; exit 0; }  # fail-soft: not silent, the fallback names that no look happened; stopping every tool on a broken helper is not what he asked for
PYTHON_BIN="$(find_divineos_python)" || { echo "[his-voice] no interpreter that can load the OS was found; could not look whether he spoke" >&2; exit 0; }

printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.his_voice_hook || \
    echo "[his-voice] the check did not run; could not look whether he spoke" >&2
exit 0
