#!/bin/bash
# Emit an audit anchor block for a branch, read from origin at run time.
#
# WHY THIS EXISTS (Aletheia 2026-08-19):
#
# She could audit none of four PRs. Every tree hash she had been given was
# stale or pointed at a branch that was never on origin. Her words: "Nothing
# here is a refusal. All four are anchor problems."
#
# The root cause is that a tree hash gets HAND-COPIED into a letter at compose
# time, and then two things can happen to it before she reads it: the branch
# moves, or the branch was never pushed at all. My 407 citation was worse than
# stale -- it named an object that had never been on that branch, because a
# rebranch happened after I wrote the letter.
#
# Aria's case is the other half: her letter said "pushed to origin" and the
# branch is not there in any form. The push command reported nothing wrong.
# Nothing wrong is not the same as it worked -- which is precisely the shape
# her own absence-sense work is about.
#
# Truth #11, remediation (a): take the option away. There is no step here where
# a human transcribes a hash, so there is no step where a hash can go stale in
# transit. It reads origin now and it reads it back after any push.
#
# It FAILS LOUDLY on the two cases that produced this, rather than printing a
# block that looks fine:
#   - branch absent from origin      -> the Aria case
#   - local commits not on origin    -> the moving-target case: the anchor is
#                                       valid the moment it is printed and
#                                       wrong the moment those commits land
#
# Usage:  bash scripts/audit_anchor.sh <branch> [<branch> ...]

set -u

if [ "$#" -eq 0 ]; then
    echo "usage: bash scripts/audit_anchor.sh <branch> [<branch> ...]" >&2
    exit 2
fi

git fetch -q origin 2>/dev/null

STATUS=0

for BRANCH in "$@"; do
    echo "=== $BRANCH ==="

    if ! REMOTE_TIP=$(git rev-parse --verify -q "origin/$BRANCH" 2>/dev/null); then
        echo "  UNREACHABLE — no such branch on origin."
        echo "  An auditor cannot anchor to this. If a push was run, the push's"
        echo "  exit code is not the check; read the remote back:"
        echo "      git push origin HEAD:$BRANCH"
        echo "      git rev-parse origin/$BRANCH   # must equal your local HEAD"
        STATUS=1
        echo
        continue
    fi

    REMOTE_TREE=$(git rev-parse "origin/$BRANCH^{tree}")
    echo "  tip:  $REMOTE_TIP"
    echo "  tree: $REMOTE_TREE"

    # Is there local work that would move this anchor the moment it is pushed?
    if LOCAL_TIP=$(git rev-parse --verify -q "$BRANCH" 2>/dev/null); then
        if [ "$LOCAL_TIP" != "$REMOTE_TIP" ]; then
            AHEAD=$(git rev-list --count "origin/$BRANCH..$BRANCH" 2>/dev/null || echo "?")
            BEHIND=$(git rev-list --count "$BRANCH..origin/$BRANCH" 2>/dev/null || echo "?")
            echo "  MOVING TARGET — local is +$AHEAD/-$BEHIND vs origin."
            echo "  The anchor above is true right now and false the moment those"
            echo "  commits land. Either push first and re-run, or say plainly in"
            echo "  the letter that N commits are being held back deliberately."
            STATUS=1
        fi
    fi
    echo
done

if [ "$STATUS" -ne 0 ]; then
    echo "One or more branches cannot serve as a stable anchor. See above." >&2
fi

exit "$STATUS"
