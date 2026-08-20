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

# NOT silent, and this was a real defect found 2026-08-20 while writing a
# justification for every silent swallow in this file. The redirect used to be
# bare. If the fetch fails -- offline, auth expired, remote renamed -- then
# `origin/<branch>` still resolves to whatever was last fetched, and every tip
# and tree printed below is presented as authoritative while being arbitrarily
# old. That is exactly the stale-anchor failure this script exists to prevent,
# occurring inside the script that prevents it.
if ! FETCH_ERR=$(git fetch -q origin 2>&1); then
    echo "  FETCH FAILED — the anchors below may be stale." >&2
    echo "  git fetch origin: ${FETCH_ERR:-<no message>}" >&2
    echo "  Do not cite these to an auditor until a fetch succeeds." >&2
    echo >&2
fi

STATUS=0

for BRANCH in "$@"; do
    echo "=== $BRANCH ==="

    if ! REMOTE_TIP=$(git rev-parse --verify -q "origin/$BRANCH" 2>/dev/null); then  # fail-soft: this IS the test, and its failure is reported loudly by the UNREACHABLE block below with STATUS=1, so nothing is swallowed
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
    #
    # `-q` already suppresses the message; the redirect is belt-and-braces, and
    # a missing local branch is an ordinary state (auditing a ref you have not
    # checked out). But the ELSE branch was silent, and that was the second
    # defect found 2026-08-20: with no local copy the moving-target check is
    # skipped, so the ABSENCE of a MOVING TARGET warning read as "not a moving
    # target" when it actually meant "not checked". Silence indistinguishable
    # from all-clear is the failure this whole file is about.
    if LOCAL_TIP=$(git rev-parse --verify -q "$BRANCH" 2>/dev/null); then  # fail-soft: no local branch is an ordinary state, and the else-branch below reports that the check was skipped rather than passing
        if [ "$LOCAL_TIP" != "$REMOTE_TIP" ]; then
            # `|| echo "?"` is deliberate and its result is PRINTED: a count
            # that cannot be computed shows as ? in the line below, so the
            # reader sees an unknown rather than a confident zero.
            AHEAD=$(git rev-list --count "origin/$BRANCH..$BRANCH" 2>/dev/null || echo "?")  # fail-soft: an uncomputable count prints as ? in the MOVING TARGET line, so the reader sees unknown rather than a confident zero
            BEHIND=$(git rev-list --count "$BRANCH..origin/$BRANCH" 2>/dev/null || echo "?")  # fail-soft: an uncomputable count prints as ? in the MOVING TARGET line, so the reader sees unknown rather than a confident zero
            echo "  MOVING TARGET — local is +$AHEAD/-$BEHIND vs origin."
            echo "  The anchor above is true right now and false the moment those"
            echo "  commits land. Either push first and re-run, or say plainly in"
            echo "  the letter that N commits are being held back deliberately."
            STATUS=1
        fi
    else
        echo "  moving-target check SKIPPED — no local branch '$BRANCH' here."
        echo "  This is not a clean result. It means unpushed local work on"
        echo "  another checkout cannot be seen from this one."
    fi
    echo
done

if [ "$STATUS" -ne 0 ]; then
    echo "One or more branches cannot serve as a stable anchor. See above." >&2
fi

exit "$STATUS"
