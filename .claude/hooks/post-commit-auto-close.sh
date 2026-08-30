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
# Post-commit hook — auto-close active goals whose tokens overlap the
# just-landed commit message.
#
# Closure-discipline structural fix (Andrew-named 2026-05-05):
# `divineos commitment fulfillment` showed 11 open goals / 0 closed
# across the day even though several had shipped. The closing-act
# required remembering + manual `divineos goal done`. Cost-asymmetry
# made the wrong-cheap path (forget to close) trivially easier than
# the right path.
#
# This hook makes the right path automatic. Runs post-commit so the
# auto-close is a side-effect of a successful commit, never a
# precondition that could block one.
#
# Fail-open: any error exits 0 silently. This hook cannot break the
# user workflow.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi

if ! command -v divineos &>/dev/null; then
    exit 0
fi

# Run the auto-close. The CLI reads HEAD's commit message itself.
# Output is informational; never blocks.
divineos goal auto-close 2>/dev/null || true

# Empty-goal handoff (Aria 2026-08-01).
#
# Auto-close is correct: a commit that completes a goal should close it.
# What was missing is what happens NEXT. Closing the last session-fresh
# goal leaves the session with none, and the goal-doorman then blocks the
# next substrate action - three times in one session before this was
# noticed, each time several actions after the commit that caused it.
#
# The auto-goal UserPromptSubmit hook cannot cover this: it refills only
# at prompt boundaries, and this state is created mid-turn.
#
# Not a warning. Andrew 2026-08-01: "no warnings only flow or blockage" -
# a warning carries no cost and the optimizer walks past it. This is the
# "automate the SPACE for judgement, then occupy it" shape instead. The
# next goal is genuinely mine to choose; a derived one would be a guess,
# and a wrong goal silently degrades active-memory ranking. What CAN be
# automated is staging the decision at the moment it is cheapest to make
# - right after the commit, while I still know what I just finished and
# what it opened up - rather than surfacing it later as an obstruction
# when I have moved on and lost the context.
#
# Uses has_session_fresh_goal(), the same predicate the goal-doorman and
# the auto-goal hook consult, so this cannot drift out of agreement with
# the gate it is trying to pre-empt. Note it is SESSION-fresh, not "any
# open goal" — the list can be long while this session has none.
#
# Fail-open: any error prints nothing.
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper lib there is no way to find the interpreter, and a missing optional notice must never fail a commit that already succeeded
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no usable interpreter means the predicate cannot be evaluated, and guessing would nag wrongly

_GOAL_CHECK=$("$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.hud_state import has_session_fresh_goal
except Exception:
    print('unknown')
    sys.exit(0)
print('fresh' if has_session_fresh_goal() else 'none')
" 2>/dev/null) || _GOAL_CHECK=unknown  # fail-soft: a broken predicate must stay silent rather than assert a goal state it could not read

if [ "$_GOAL_CHECK" = "none" ]; then
    echo ""
    echo "## NO SESSION-FRESH GOAL REMAINS (this commit closed the last one)"
    echo ""
    echo "You know right now what you finished and what it opened up."
    echo "That context is gone in three actions, when the doorman asks"
    echo "instead and you have to reconstruct it."
    echo ""
    echo "    divineos goal add \"<what this commit opened up>\""
fi

exit 0
