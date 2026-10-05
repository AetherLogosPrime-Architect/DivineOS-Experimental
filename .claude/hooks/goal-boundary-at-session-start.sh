#!/usr/bin/env bash
# A new stretch names its own work (2026-10-01, council-7666a3816f92).
#
# Goal freshness is measured from last use, so a goal in steady use never
# lapses mid-work. Aria's station-3 objection: that alone lets a goal outlive
# the work it named. So at every SessionStart -- startup, resume, clear and,
# the one that matters, compact -- every goal set before now stops counting.
#
# Wired to SessionStart directly, NOT to session-init-once.sh: that runs once
# per session id, and a compaction keeps the session id, so it never re-runs.
#
# Never blocks: a hook that refuses SessionStart refuses the briefing with it.
# If the interpreter cannot be resolved nothing is written, which leaves the
# plain two-hour window -- the behaviour before this change, not a wider hole.

cat >/dev/null 2>&1 || true
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PY="$(find_divineos_python 2>/dev/null)" || exit 0  # fail-soft: no interpreter means no boundary, i.e. the old two-hour window
[ -n "$PY" ] || exit 0
"$PY" -c "from divineos.core.hud_state import mark_goal_boundary; mark_goal_boundary()" 2>/dev/null \
    && echo "[goal] new stretch: goals set before now no longer count -- name this one with divineos goal add"
exit 0
