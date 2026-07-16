#!/bin/bash
# WIRED VIA .git/hooks/post-commit DELEGATOR — installed by setup/setup-hooks.sh.
# The delegator loops over every post-commit-*.sh in .claude/hooks/, so
# THIS FILE FIRES on every git commit (not via .claude/settings.json).
# Third wiring surface beyond Claude Code settings + code-graph
# (Aletheia cold-audit 2026-07-16 finding #2: named as dark by tools
# that check only the first two surfaces; this comment closes that
# false-positive class).
#
# Post-commit hook — auto-integrate any Andrew-correction referenced in
# the just-landed commit message.
#
# Andrew 2026-07-07 structural fix: "your will needs to be made into
# structure through this automation. alot of things are likely orphaned
# because nothing is automated and just relies on being remembered to be
# used which is impossible." Manual `divineos andrew-correction integrate`
# after each fix relies on remembering; the discipline decays.
#
# This hook runs post-commit so the auto-integrate is a side-effect of a
# successful commit, never a precondition that could block one. The
# `auto-integrate` subcommand parses HEAD's commit message for
# "correction #N" and "andrew-correction #N" forms and calls integrate()
# on each with the commit hash as the evidence anchor.
#
# Fail-open: any error exits 0 silently. This hook cannot break the user
# workflow.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
    exit 0
fi

if ! command -v divineos &>/dev/null; then
    exit 0
fi

# Reads HEAD commit message and hash itself; output is informational.
divineos andrew-correction auto-integrate 2>/dev/null || true

exit 0
