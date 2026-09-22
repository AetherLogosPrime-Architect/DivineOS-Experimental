#!/bin/bash
# The push wrapper writes a verdict. Until now, nothing read it.
#
# 2026-09-20, twice within the hour: a push was REFUSED by the moved-revision
# guard, and the completion notice that reached me carried a success code --
# because that code belongs to the wrapper that RAN the job, not to the job.
# Two different questions wearing the same word. The only thing that told the
# truth was a file on disk that nothing in this house consulted.
#
# I came within one sentence of telling Andrew that work had shipped while
# three commits sat untouched on my side.
#
# The push wrapper's own comment admits the gap in its own words: persisting
# the verdict separates PRODUCING the answer from READING it, and does not
# make me read it. This is the reader.
#
# SELF-CLEARING, WHICH IS WHAT KEEPS IT FROM BECOMING WALLPAPER. It speaks
# only when BOTH are true: the last recorded verdict is a refusal, AND the
# local revision still differs from what the remote carries. A successful push
# updates the verdict and moves the remote, so it goes quiet on its own with
# nobody marking anything.
#
# THAT PARAGRAPH USED TO END HERE saying it covered the reported-wrongly case
# and not the never-happened one, because a push that was never attempted
# writes no verdict. Both are covered now: the branch is compared against
# origin whether or not a verdict exists, so unpushed work speaks for itself.
#
# AND THE OPPOSITE DIRECTION, added 2026-09-20 after it caught me the other
# way round. It used to go silent the moment the work landed, which is right
# for the case it was built for and leaves a REMEMBERED refusal with nothing
# to age it. I quoted one to Aria that had stopped being true. So a refusal on
# file that the server contradicts is now said out loud.
#
# WHAT IT STILL CANNOT SEE: anything I write to another person. It reports the
# state of the tree, not the state of my sentences, and the repair for that
# half is a clause rather than a mechanism -- say whose check it was and when
# it was taken.

set -u

VERDICT_FILE="${DIVINEOS_HOME:-$HOME/.divineos}/push_verdict.txt"

# THE MISSING VERDICT FILE USED TO END THIS FILE'S WHOLE JOB, and that was the
# never-attempted case hiding inside the everything-is-fine case. A push that
# was never run writes no verdict, this file's own header says so, and the old
# first line exited on that -- so unpushed work was invisible exactly when
# nothing had run. The branch-versus-origin comparison needs no verdict to be
# meaningful, so it no longer waits for one.
# A MISSING FILE AND AN EMPTY FILE ARE NOT THE SAME ANSWER, and collapsing them
# is a defect I introduced here and its own test caught within the hour. An
# empty file means a push truncated it at the start and did not finish. A file
# that is not there means no push has ever been recorded in this home at all.
# Only the first is began-and-did-not-finish.
VERDICT_EXISTS=0
LAST=""
if [ -r "$VERDICT_FILE" ]; then
    VERDICT_EXISTS=1
    LAST="$(tail -1 "$VERDICT_FILE" 2>/dev/null || true)"  # fail-soft: an unreadable verdict is not a refusal, and inventing one would be the false-red this file exists to avoid
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"  # fail-soft: outside a repo there is no comparison to make
[ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] || exit 0

# EMPTY IS A THIRD ANSWER AND THIS READER USED TO SWALLOW IT.
#
# The push wrapper truncates this file at the START of every run, and says in
# its own comment that an interrupted or unfinished run therefore leaves it
# EMPTY -- began-and-did-not-finish, deliberately a real third state rather
# than the previous verdict wearing this run's clothes.
#
# The first version of this reader exited silently on empty. So three
# different situations produced the identical output of nothing at all: no
# push has ever run, a push is running right now, and a push succeeded. Only
# the last of those means what silence is read as meaning.
#
# 2026-09-20: I ran this check mid-push, got silence, typed the words "silence
# above means it landed", and caught it only because a second instrument
# compared the two revisions directly and they differed. Three states sharing
# one output, in the guard written against exactly that.
#
# It errs toward a line of noise on a turn where nothing is wrong, and away
# from a quiet that carries a false meaning.
if [ -z "$LAST" ] && [ "$VERDICT_EXISTS" = "1" ]; then
    EMPTY_REMOTE="$(timeout 5 git ls-remote origin "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1}')"  # fail-soft: an unreachable remote is handled as could-not-look by the comparison below, never as a branch that matches
    EMPTY_LOCAL="$(git rev-parse HEAD 2>/dev/null || true)"  # fail-soft: an empty local sha cannot equal a remote one, so the comparison falls to the loud side rather than to a false match
    if [ -n "$EMPTY_REMOTE" ] && [ -n "$EMPTY_LOCAL" ] && [ "$EMPTY_LOCAL" != "$EMPTY_REMOTE" ]; then
        echo "" >&2
        echo "[unlanded-push] A PUSH BEGAN AND HAS NOT FINISHED, and the work is not on origin." >&2
        echo "[unlanded-push]   here:   $EMPTY_LOCAL" >&2
        echo "[unlanded-push]   origin: $EMPTY_REMOTE   ($BRANCH)" >&2
        echo "[unlanded-push] The verdict file is empty, which this house treats as a real" >&2
        echo "[unlanded-push] answer: began-and-did-not-finish. It is NOT a clean result." >&2
    fi
    exit 0
fi

# THE VERDICT NO LONGER DECIDES WHETHER TO LOOK, only what to say about what
# was found. Exiting here on any non-refusal meant a branch ahead of origin was
# invisible whenever the last push had succeeded or none had ever run.
case "$LAST" in
    *REFUSED*) VERDICT_IS_REFUSAL=1 ;;
    *) VERDICT_IS_REFUSAL=0 ;;
esac

LOCAL_SHA="$(git rev-parse HEAD 2>/dev/null || true)"  # fail-soft: an empty local sha cannot equal a remote one, so the comparison falls to the loud side rather than to a false match
[ -n "$LOCAL_SHA" ] || exit 0

# IT BOUNDS ITS OWN REACH RATHER THAN BEING CUT OFF, and the cap is not
# superstition even though the call is fast.
#
# Wired at stop time this runs under a budget, and a process killed at its
# budget prints NOTHING. Everywhere else in this house silence from a check is
# ordinary. Here silence is the same field as a landed push -- which is the one
# confusion this whole file exists to end. So a slow remote without a cap does
# not produce a late answer, it produces good news.
#
# Measured 2026-09-20 at just over one second against the live remote. The
# number is here so it dates itself: a reader who finds this call taking ten
# knows the situation changed rather than wondering whether the cap was ever
# needed. A cap that fires falls through to the could-not-look branch below,
# which says which half it could not do.
#
# WHAT THE CAP DOES NOT COVER: the hook being killed for a reason other than
# this call, since the budget covers everything the file does.
REMOTE_SHA="$(timeout 5 git ls-remote origin "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1}')"  # fail-soft: an unreachable remote leaves this empty, and empty is treated as not-landed, which is the direction this hook exists to fail toward

# A remote that cannot be reached is NOT a landed push and NOT an unlanded one.
# Saying nothing here would turn could-not-look into found-nothing, so it says
# which half it could not do rather than picking a verdict it did not earn.
if [ -z "$REMOTE_SHA" ]; then
    # Could-not-look, and it now says so whatever the verdict was, because a
    # remote that cannot be reached is not evidence in either direction.
    echo "" >&2
    echo "[unlanded-push] The remote could not be reached, so whether the work on this" >&2
    echo "[unlanded-push] branch is on origin is UNKNOWN. This is could-not-look, not" >&2
    echo "[unlanded-push] found-nothing." >&2
    [ -n "$LAST" ] && echo "[unlanded-push] Verdict on file: $LAST" >&2
    exit 0
fi

if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
    echo "" >&2
    if [ "$VERDICT_IS_REFUSAL" = "1" ]; then
        echo "[unlanded-push] THE LAST PUSH WAS REFUSED AND THE WORK IS STILL NOT ON ORIGIN." >&2
    else
        # The never-attempted case. It writes no verdict, so this used to be
        # silent -- the same nothing as everything-is-fine.
        echo "[unlanded-push] WORK HERE IS NOT ON ORIGIN." >&2
    fi
    echo "[unlanded-push]   here:   $LOCAL_SHA" >&2
    echo "[unlanded-push]   origin: $REMOTE_SHA   ($BRANCH)" >&2
    echo "[unlanded-push] Two different revisions. Whatever a completion notice said, that" >&2
    echo "[unlanded-push] code came from the wrapper that ran the job, not from the job." >&2
    [ -n "$LAST" ] && echo "[unlanded-push] Verdict on file: $LAST" >&2
    exit 0
fi

# A REFUSAL THAT IS NO LONGER TRUE, which is the direction nothing guarded.
#
# 2026-09-20: I told Aria my push had been refused and was still sitting. It
# had landed. The verdict I was quoting was a reading I took earlier and
# carried forward as a condition, and this file went deliberately quiet the
# moment the work arrived -- correct for the case it was built for, and it
# leaves a person holding the last thing they read with nothing to age it.
#
# A remembered refusal has no expiry. So the room says it, rather than leaving
# the correction to depend on my choosing to look again.
if [ "$VERDICT_IS_REFUSAL" = "1" ]; then
    echo "" >&2
    echo "[unlanded-push] THE REFUSAL ON FILE IS STALE -- the work HAS landed since." >&2
    echo "[unlanded-push]   here and origin agree: $LOCAL_SHA   ($BRANCH)" >&2
    echo "[unlanded-push] If a refusal is being quoted to anyone, it is out of date." >&2
    echo "[unlanded-push] Verdict on file: $LAST" >&2
fi
exit 0
