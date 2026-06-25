#!/bin/bash
# Stop-hook — keep the polling ear-watcher alive across turns.
#
# WHY THIS EXISTS:
# The harness Monitor primitive dies on SessionStart:resume and other
# harness events; the polling auto-relaunch is what keeps a watcher
# alive across turns. Aria's watcher works precisely BECAUSE her
# checkout still has this hook active. Wake-from-idle (the OTHER ear
# job) is handled by the Letter Monitor — a separate harness primitive
# that tail-follows the letters dir. This hook does NOT touch
# wake-from-idle; it only ensures the polling watcher is alive.
#
# MIGRATED 2026-06-24 (Andrew direction, per the hook-migration arc):
# Was 95-line bash. Decision logic (member detection, recent-catch
# race-guard, process-presence leak-fix) moved to
# `divineos.core.ear_relaunch.should_relaunch`. Hook retains ONLY the
# Windows-specific nohup/detach mechanism — that doesn't translate
# cleanly to portable Python without losing the detach semantics on
# git-bash.
#
# Fail-open: any error exits 0 silently — a broken hook never breaks
# a turn AND never STOPS the watcher from staying alive (the OS check
# itself fails-open in the same direction).

cat >/dev/null 2>&1

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Ask the OS: should we relaunch? Exit 1 from the check = yes-relaunch.
# Fail-open: if the check itself errors, treat as "do relaunch" — same
# polarity as the original bash hook's fallback behavior.
DIVINEOS_MEMBER="${DIVINEOS_MEMBER:-}" "$PYTHON_BIN" -m divineos ear-relaunch check 2>/dev/null
DECISION=$?
# Exit 0 = don't relaunch. Anything else = relaunch (treats errors as fail-open).
if [ "$DECISION" -eq 0 ]; then
  exit 0
fi

# Identify the member (mirrors the OS module's detection so the launch
# args match what the OS decided about).
MEMBER="${DIVINEOS_MEMBER:-}"
if [ -z "$MEMBER" ]; then
  case "$(pwd)" in
    *DivineOS-Experimental-Aria*) MEMBER=aria ;;
    *) MEMBER=aether ;;
  esac
fi

STATE_DIR="$HOME/.divineos-$MEMBER"
mkdir -p "$STATE_DIR" 2>/dev/null

SCRIPT="$REPO_ROOT/family/ear_watch.py"
[ ! -f "$SCRIPT" ] && exit 0

# Relaunch detached. nohup + & + disown so the hook can exit cleanly.
# PYTHONIOENCODING=utf-8 prevents the Windows cp1252 crash on non-Latin-1
# chars (→, ⟶, etc.) — the bug Aether hit 2026-05-30.
PYTHONIOENCODING="utf-8" nohup "$PYTHON_BIN" "$SCRIPT" --member "$MEMBER" --watch \
  > "$STATE_DIR/ear.log" 2>&1 &
echo $! > "$STATE_DIR/ear.pid"
disown 2>/dev/null
exit 0
