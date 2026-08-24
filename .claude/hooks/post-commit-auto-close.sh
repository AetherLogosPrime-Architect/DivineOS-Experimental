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

# HEAD-CHANGE GATE (2026-08-24). This hook is registered PostToolUse with
# matcher "Bash", so it fires after EVERY Bash call -- not after every commit,
# despite what the header above says. Measured: 282 firings in one session, of
# which 142 (50.4%) were killed at the 15s timeout, the worst rate of any hook
# in the log. The call below costs ~580ms warm and is pure waste on any Bash
# call that was not a commit, which is nearly all of them.
#
# So: read HEAD, compare to the last HEAD this hook acted on, and do nothing if
# it has not moved. `git rev-parse HEAD` is a single cheap read; the expensive
# `divineos` invocation now happens only on the rare call that actually follows
# a commit. Truth #11 remediation (a) -- take the option away rather than hope
# the slow path stays fast.
#
# Fail-open preserved throughout: any failure below exits 0 having done nothing.
HEAD_NOW="$(git rev-parse HEAD 2>/dev/null)"  # fail-soft: no HEAD (fresh repo, detached, not a repo) means there is no commit to auto-close against, and the empty check below exits 0
if [ -z "$HEAD_NOW" ]; then
    exit 0
fi

STATE_DIR="${DIVINEOS_HOME:-$HOME/.divineos}"
STATE_FILE="$STATE_DIR/post_commit_auto_close_head"
HEAD_LAST="$(cat "$STATE_FILE" 2>/dev/null)"  # fail-soft: an absent or unreadable state file must read as no-HEAD-seen, which fires auto-close once rather than skipping it silently

if [ "$HEAD_NOW" = "$HEAD_LAST" ]; then
    exit 0
fi

# Record BEFORE running, so a kill mid-auto-close does not cause this commit to
# be retried on every subsequent Bash call for the rest of the session -- which
# would reproduce the exact hot-loop this gate exists to remove.
mkdir -p "$STATE_DIR" 2>/dev/null
printf '%s' "$HEAD_NOW" > "$STATE_FILE" 2>/dev/null || true  # fail-soft: an unwritable state dir costs a repeated auto-close next Bash call, which is wasted work rather than lost work

# Run the auto-close. The CLI reads HEAD's commit message itself.
# Output is informational; never blocks.
divineos goal auto-close 2>/dev/null || true  # fail-soft: this fires on the Bash path after every commit and closing a goal is bookkeeping, never correctness; a failure here leaves the goal open, which is the visible-and-safe direction, whereas surfacing CLI stderr on every commit is the noise that turns a surface into wallpaper.

exit 0
