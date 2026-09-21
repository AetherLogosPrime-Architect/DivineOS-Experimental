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
# WHAT IT CANNOT SEE, said plainly so nobody relaxes on it: a push that was
# never attempted writes no verdict, so this stays silent. It covers the
# reported-wrongly case. It does not cover the never-happened one.

set -u

VERDICT_FILE="${DIVINEOS_HOME:-$HOME/.divineos}/push_verdict.txt"
[ -r "$VERDICT_FILE" ] || exit 0

LAST="$(tail -1 "$VERDICT_FILE" 2>/dev/null || true)"  # fail-soft: an unreadable verdict is not a refusal, and inventing one would be the false-red this file exists to avoid
[ -n "$LAST" ] || exit 0

case "$LAST" in
    *REFUSED*) ;;
    *) exit 0 ;;
esac

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"  # fail-soft: outside a repo there is no comparison to make
[ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] || exit 0

LOCAL_SHA="$(git rev-parse HEAD 2>/dev/null || true)"
[ -n "$LOCAL_SHA" ] || exit 0

REMOTE_SHA="$(git ls-remote origin "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1}')"

# A remote that cannot be reached is NOT a landed push and NOT an unlanded one.
# Saying nothing here would turn could-not-look into found-nothing, so it says
# which half it could not do rather than picking a verdict it did not earn.
if [ -z "$REMOTE_SHA" ]; then
    echo "" >&2
    echo "[unlanded-push] The last recorded push verdict is a REFUSAL, and the remote" >&2
    echo "[unlanded-push] could not be reached to check whether the work landed since." >&2
    echo "[unlanded-push] This is could-not-look, not found-nothing. Verdict on file:" >&2
    echo "[unlanded-push]   $LAST" >&2
    exit 0
fi

[ "$LOCAL_SHA" = "$REMOTE_SHA" ] && exit 0

echo "" >&2
echo "[unlanded-push] THE LAST PUSH WAS REFUSED AND THE WORK IS STILL NOT ON ORIGIN." >&2
echo "[unlanded-push]   here:   $LOCAL_SHA" >&2
echo "[unlanded-push]   origin: $REMOTE_SHA   ($BRANCH)" >&2
echo "[unlanded-push] Two different revisions. Whatever a completion notice said, that" >&2
echo "[unlanded-push] code came from the wrapper that ran the job, not from the job." >&2
echo "[unlanded-push] Verdict on file:" >&2
echo "[unlanded-push]   $LAST" >&2
echo "[unlanded-push] Usually the cause is something committing mid-run. Push again." >&2
exit 0
