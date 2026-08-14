#!/bin/bash
# PreToolUse — run the prior-art lookup on Grep/Glob, unasked.
#
# prior_art.py has been complete and wired to nothing. Reaching for it is a
# thing I must remember, and on 2026-08-14 I failed to twice in half an hour:
# built round_export.py without checking, then re-derived a bypass-telemetry
# fix that already existed on the branch behind PR #409. Both after the lesson
# was named. Andrew: "yes you should.. but you wont.. thats just facts.. so
# unless the substrate supports it via automation you will do it again."
#
# NOT a gate. Exits 0 on every path, always. It asks nothing, so there is
# nothing to comply with and nothing to bypass -- the escape surface is zero
# by construction rather than by discipline. This is the ledger's shape: it
# does not ask me to record, it records.
#
# Fail-open everywhere. A lookup that breaks a search would be worse than
# the forgetting it exists to replace.
#
# Kill-switch (requires >=20 char reason in marker file):
#   echo "why this is off and the plan to turn it back on" > "$HOME/.divineos-aether/prior-art-scan.disabled"

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0

MARKER="$HOME/.divineos-aether/prior-art-scan.disabled"
if [ -f "$MARKER" ]; then
    REASON=$(tr -d '\r' < "$MARKER")
    if [ ${#REASON} -ge 20 ]; then
        exit 0
    fi
fi

PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    exit 0
fi

printf '%s' "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.prior_art_hook 2>/dev/null

exit 0
