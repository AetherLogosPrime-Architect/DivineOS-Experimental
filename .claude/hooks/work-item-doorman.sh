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

OUT="$(printf '%s' "$INPUT" | divineos work-item gate 2>&1)"
RC=$?

if [ "$RC" -eq 2 ]; then
    printf '%s\n' "$OUT" >&2
    exit 2
fi

# Anything else -- clean pass, or the command itself failing to run -- lets the
# tool call through. A non-zero that is not 2 means the doorman could not form
# an opinion, and an opinion it could not form must not become a refusal.
exit 0
