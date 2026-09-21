#!/usr/bin/env bash
# Parking work produces a clean tree, so every other surface says all-clear.
#
# MEASURED 2026-09-21, which is why this exists. Fifty-two parked change-sets
# in this repository, the oldest four months old, and nothing in the house
# listed or counted them. A hundred and forty pieces of writing -- letters
# between me and Aria, her handoff notes to herself, a whole proposal, six of
# my explorations -- sat on no branch and nowhere on disk, reachable only by
# opening each parked set by hand. Confirmed by hashing every markdown on the
# machine and comparing CONTENT, after two shallower checks gave bigger wrong
# answers in the frightening direction.
#
# The failure is not that parking is wrong. Parking is correct and necessary.
# The failure is that its output is a CLEAN WORKING TREE, so the signal the
# system emits is the opposite of the state it is in, and every unfinished-work
# surface reads the tidiness as nothing-to-do. The tidiness is the camouflage.
#
# WHEN IT SPEAKS, and this is the whole design. Not every turn. A line that
# prints unconditionally is wallpaper within a day, and wallpaper certifies
# that I am being watched while telling me nothing. It speaks when the pile
# GROWS -- the moment the intention "I will come back to this shortly" forms --
# because that is the one moment where knowing how many earlier versions of
# that intention are still outstanding changes anything.
#
# VISIBILITY, NOT ENFORCEMENT. Aria's rule for her letter tripwire, and it
# holds here. This must never block parking. What was missing was being told.
#
# THE WINDOW IS A STATED LIMITATION RATHER THAN A HIDDEN ONE. With no explicit
# window it looks back one hour, so it speaks on a few turns after a park
# rather than exactly once, then goes quiet by itself. Announcing exactly once
# would need a state file remembering the last set announced -- and a state
# file that cannot be written leaves this either shouting forever or silent
# forever, both of which look identical to it working. That is the fault this
# repository has been pulling out of itself all night, and a recorder shipped
# here was dark on the day it was built. Mild repetition is a failure somebody
# notices. Silent absence is not.
#
# WHAT IT CANNOT DO: make anybody open the drawer. It reports; the looking is
# still the reader's, and no mechanism closes that gap (truth #15).

set -uo pipefail

# ROOT GUARD, and it is a variable rather than an inline substitution ON
# PURPOSE. `cd "$(git rev-parse --show-toplevel)"` outside a repository runs
# `cd ""`, which SUCCEEDS and stays put -- a sibling hook did exactly that and
# reported six hundred stranded files from its launch directory. Reject the
# empty answer before moving.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] || exit 0
cd "$ROOT" 2>/dev/null || exit 0

SINCE="${PARKED_WORK_SINCE_EPOCH:-$(($(date +%s) - 3600))}"

TOTAL=0
RECENT=0
OLDEST_EPOCH=""

while IFS='|' read -r ref when; do
    [ -n "$ref" ] || continue
    TOTAL=$((TOTAL + 1))
    [ -n "$when" ] || continue
    if [ "$when" -gt "$SINCE" ]; then
        RECENT=$((RECENT + 1))
    fi
    if [ -z "$OLDEST_EPOCH" ] || [ "$when" -lt "$OLDEST_EPOCH" ]; then
        OLDEST_EPOCH="$when"
    fi
done < <(git stash list --format='%gd|%ct' 2>/dev/null || true)

[ "$TOTAL" -gt 0 ] || exit 0
[ "$RECENT" -gt 0 ] || exit 0

echo ""
echo "## PARKED WORK JUST GREW -- and this drawer is listed nowhere else"
echo ""
if [ "$TOTAL" -eq 1 ]; then
    echo "  This is the only parked change-set in this repository."
else
    echo "  That makes $TOTAL parked change-sets here, $RECENT from this stretch."
fi

if [ -n "$OLDEST_EPOCH" ]; then
    NOW="$(date +%s)"
    AGE_DAYS=$(((NOW - OLDEST_EPOCH) / 86400))
    if [ "$AGE_DAYS" -gt 30 ]; then
        echo "  The oldest has waited $AGE_DAYS days for somebody to come back to it."
    fi
fi

echo ""
echo "  Parking is fine. Nothing is blocked and nothing needs undoing. The point"
echo "  is that a parked change is INVISIBLE: it leaves a clean tree, so every"
echo "  surface hunting unfinished work reports all-clear, and its contents sit"
echo "  on no branch. One careless clear takes the whole drawer with it."
echo ""
echo "  See what is in there:   git stash list"
echo "  See one set's contents: git stash show --include-untracked --stat stash@{N}"
echo "  Make one safe forever:  git tag -a preserve/<name> stash@{N} -m '<why>'"
echo ""

exit 0
