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

exit 0
