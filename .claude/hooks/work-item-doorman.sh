#!/usr/bin/env bash
# PreToolUse -- the build-flow doorman. The front of the flow, which until now
# ran entirely on memory.
#
# Design: docs/drafts/build_flow_ready_doorman_draft_2026-09-07.md
# Logic:  src/divineos/core/work_item_doorman.py
# Flow:   docs/build_flow.md
#
# Deliberately almost empty. Every decision lives in Python where it is
# testable; shell parsing of a bash command line is exactly the kind of
# cleverness that fails silently and gets read as a pass.
#
# WHY IT WATCHES Bash TOO. The cheapest route in the attack tree is writing a
# file through a redirection or a heredoc, which never touches the edit tools.
# That is not a hypothetical -- the design draft for this hook was itself
# written through a heredoc an hour before the hook existed.
#
# FAIL-SOFT ON INFRASTRUCTURE, FAIL-CLOSED ON ANSWERS. If the CLI is missing or
# the tree will not import, this stands aside: a gate that blocks every tool
# call when its own plumbing breaks gets torn out within the hour, and then it
# protects nothing. But when the CLI RUNS and says hold, the hold stands.

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

command -v divineos >/dev/null 2>&1 || exit 0

# Sourced for hook_say_nothing_ran_for only. A refusal that names what it
# objected to, and never what it stopped, leaves the reader unable to tell a
# finding from a check that never ran -- the fault this branch exists to close.
# This hook arrived on main while that rule was being written here, so neither
# side was wrong and only the merge could see the gap.
#
# THIS USED TO END `|| exit 0`, and exit 0 is ALLOW (fixed 2026-09-23, Aria).
# The comment here called that "fail-soft on infrastructure", which is right
# for the CLI above -- the CLI is the decision, and a door that blocks every
# call when its brain is missing gets torn out -- and wrong for this line. The
# library decides nothing. It prints the footer after a refusal, and loading it
# starts this hook's timing record and liveness line. So a library that would
# not load made the build-flow doorman a permission, silently.
#
# It STAYS up here rather than moving down to the refusal, and that is on
# measurement: hook_firing_map reads the timing record this load starts, and
# counts any hook mentioning _lib.sh as able to report. Loaded only when
# refusing, every pass would write nothing and the map would call a working
# doorman SILENT. So: load early for the record, and let a failed load cost the
# footer and the record -- never the hold. walk-126cf863fe02.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || true  # fail-soft: a missing library may cost the footer and the timing record, and must never cost the hold -- the decision below is the CLI's

OUT="$(printf '%s' "$INPUT" | divineos work-item gate 2>&1)"
RC=$?

if [ "$RC" -eq 2 ]; then
    printf '%s\n' "$OUT" >&2
    # Only if the library loaded. Undefined, it would print "command not found"
    # into the refusal and return 127 -- the script carries on, since `set -u`
    # covers variables and not functions -- so the guard keeps the refusal
    # clean rather than keeping it alive. It must not depend on its postscript.
    command -v hook_say_nothing_ran_for >/dev/null 2>&1 && hook_say_nothing_ran_for "$INPUT"
    exit 2
fi

# Anything else -- clean pass, or the command itself failing to run -- lets the
# tool call through. A non-zero that is not 2 means the doorman could not form
# an opinion, and an opinion it could not form must not become a refusal.
#
# Known overlap, named rather than hidden: 2 is not only "hold". The ~/bin
# wrapper with no sealed venv, python's can't-open-file, and click usage errors
# also exit 2, and would be read as a hold. Through the harness these are
# mostly unreachable; it fails toward holding, and the printed output says
# which one it was. (Aether, station four on #545, 2026-09-25.)
exit 0
