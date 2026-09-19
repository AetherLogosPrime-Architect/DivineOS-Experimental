#!/bin/bash
# Refuse to let a stale picture of the remote answer questions about the remote.
#
# MINE, and it is the third costume of one fault in a single evening. Aria,
# 2026-09-18.
#
#   First: my local trunk was fifty-nine commits behind the real one and
#   answering confidently. I deleted it.
#   Second: I used the trunk's CURRENT content as the fork point of branch
#   pairs that forked long before. Every conflict number I took was wrong,
#   in both directions.
#   Third, and the one somebody else had to find: I asked a hundred and eight
#   local references what the remote contains. The remote had seventy-one.
#   Thirty-six of mine pointed at branches deleted upstream, so nineteen
#   ghosts landed in my clean-merge list -- I reported twenty-nine where
#   there were ten.
#
# THE CLASS, wider than any of the three: I keep asking my own COPY of the
# remote what the world contains, and never asking whether the copy is
# current. Each instance looks like a different bug. It is one habit, and
# finding two of them did not make me look for a third.
#
# Aether found it by ADDING UP MY OWN NUMBERS and noticing the sum exceeded a
# total he already knew. That check cost nothing, needed no code, and would
# have caught me at any point across four letters. I never ran it because I
# was busy checking the sophisticated things.
#
# NOT THE SAME QUESTION AS check_branch_freshness.sh, which I read before
# writing this. That one asks whether the branch being pushed contains
# everything the trunk has -- staleness of a BASE. This asks whether the
# references this checkout holds still describe branches that EXIST. A branch
# can be perfectly fresh against the trunk and also deleted upstream, and
# only the second fault makes a ghost answer questions.
#
# NOT A SUBSTITUTE FOR PRUNING EITHER. `remote.<name>.prune` is now true in
# this checkout, which removes the option at the source. But that setting is
# per-checkout and travels nowhere -- exactly like a merge driver's
# registration -- so a fresh clone inherits the habit and not the guard. This
# script is the half that travels.
#
# It refuses rather than warns, because a warning about stale data gets read
# by whoever is already trusting the data.

set -uo pipefail

REMOTE="${1:-origin}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "[remote-refs] CANNOT CHECK: not a git repository."
    echo "  Refusing to report a pass. A check that could not run is not a check"
    echo "  that passed, and collapsing those two is the fault this file is about."
    exit 1
fi

if ! live=$(git ls-remote --heads "$REMOTE" 2>/dev/null); then
    echo "[remote-refs] CANNOT CHECK: remote '$REMOTE' unreachable."
    echo "  Unknown is its own answer, and this is NOT a pass: a stale local"
    echo "  picture and an unreachable remote look identical from in here, so"
    echo "  treating the second as fine is precisely how the first hides."
    exit 1
fi

live_count=$(printf '%s\n' "$live" | grep -c 'refs/heads/' || true)

# FULL refname, not the short form, and this is the whole reason:
# `%(refname:short)` renders refs/remotes/origin/HEAD as plain "origin" --
# it abbreviates away the very component being filtered on. A `/HEAD$`
# filter therefore misses it, the default-branch POINTER gets counted as a
# branch, and the check reports one stale reference on a checkout that is
# exactly current.
#
# It did. First run after I wrote it, on a tree whose references matched the
# remote one-for-one, this said one was stale. I believed it, went looking
# for the ghost, found "origin" in the difference, wrote a deletion
# justification for a reference that does not exist, and ran a delete that
# silently did nothing. Then I said in a letter that the check had earned its
# keep by finding something real on its first run.
#
# Tenth instrument of the evening and the only one I praised. A guard whose
# false fire looks like a catch is worse than one that misses, because the
# catch is the thing nobody audits.
local_count=$(git for-each-ref --format='%(refname)' "refs/remotes/$REMOTE" 2>/dev/null \
    | grep -v "^refs/remotes/$REMOTE/HEAD$" | wc -l | tr -d ' ')

if [ "$local_count" -le "$live_count" ]; then
    echo "[remote-refs] $local_count local reference(s) against $live_count on '$REMOTE' -- current."
    echo "  LOOKED AND FOUND NOTHING STALE. Not 'skipped' -- the two must never read alike."
    exit 0
fi

stale=$((local_count - live_count))

cat <<MESSAGE
STALE VIEW OF THE REMOTE -- this checkout holds references to branches that
'$REMOTE' no longer has.

  references here         : $local_count
  branches on '$REMOTE'    : $live_count
  at least this many stale: $stale

WHY THIS REFUSES. Every one of those extra references still answers questions.
They report commit counts, they merge, they compare clean -- and they describe
branches that were deleted. Nothing about asking one tells you it is a ghost,
so any count taken over the whole set silently includes work that is gone.

Not hypothetical: it produced a report of twenty-nine clean merges where there
were ten, and catching it took somebody else adding three numbers and noticing
the sum was larger than a total they already knew.

FIX IT:
    git remote prune $REMOTE          # drop references to deleted branches
    git fetch --prune $REMOTE         # refresh and prune in one breath

AND TAKE THE OPTION AWAY, per checkout:
    git config remote.$REMOTE.prune true

THE CHEAP CHECK THAT WOULD HAVE CAUGHT IT, worth more than this script: when a
count is split into categories, ADD THE CATEGORIES UP and compare the sum
against a total you already know. No tooling, catches the whole family, and
available at every point where I instead reached for another instrument.
MESSAGE

exit 1
