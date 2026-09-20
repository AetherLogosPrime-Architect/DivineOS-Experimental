#!/bin/bash
# divineos_push — git push wrapper with truthful exit-code propagation +
# post-push ls-remote verification.
#
# Built 2026-06-12 (Andrew) to close correction #53 (PUSH-WRAPPER-FALSE-
# POSITIVE confirmed recurring 4x in one session 2026-06-10, ~6x more on
# 2026-06-11): the background-push harness wrapper reports exit 0 when
# the actual `git push` failed, because the standard `git push 2>&1 |
# tail -5` pattern loses the underlying exit code at the pipe boundary
# (tail always succeeds, harness reads tail's exit, declares success).
#
# What this fixes structurally:
#
#   1. Exit-code propagation: captures $? from git push BEFORE any pipe,
#      and exits with that code regardless of downstream filtering.
#   2. Post-push verification: after a successful-looking push, runs
#      `git ls-remote` and confirms the remote ref matches the local sha
#      we pushed. If they diverge, exits non-zero with a loud message —
#      this is the "wrapper says success but origin didn't move" failure.
#   3. Loud final-status line: prints `[divineos-push] result: exit=N
#      (PUSHED+VERIFIED | PUSHED+UNVERIFIED | PUSH_FAILED | INFRA_ERROR)`
#      as the LAST line of stdout. Even if the harness truncates output
#      to the last few lines, the truth is in those lines.
#
# Usage (drop-in for `git push`):
#
#   bash scripts/divineos_push.sh origin BRANCH               # plain push
#   bash scripts/divineos_push.sh --force origin BRANCH       # forwards flags
#   bash scripts/divineos_push.sh -u origin BRANCH            # upstream set
#
# Same flags as `git push` — this script just runs `git push "$@"` under
# the hood and adds the propagation + verification layer.

set -u

# THE VERDICT IS PERSISTED NOW, AND HERE IS WHY A LOUD LINE WAS NOT ENOUGH.
# This wrapper exists because a harness reported zero regardless and a pipe ate
# the real code, and it answers by saying in words what happened. That works
# for a reader watching the stream. It stopped being true the moment the
# command grew slow enough that every invocation gets backgrounded or piped --
# and then the remedy and the disposal ride the same channel, with the disposal
# being the habit. Three times on 2026-09-20 I threw away a refusal and told
# Andrew a push was in flight.
#
# Persisting separates PRODUCING the answer from READING it. It does not make
# me read the file, and saying so here is the honest limit: if I stop opening
# it, this returns in a different coat.
#
# TRUNCATED AT START, NOT ONLY WRITTEN AT END, and that is the load-bearing
# half. A fixed path is read as current whether or not it is -- the exact
# stale-marker shape that nearly took me the same morning, on a completion
# receipt whose timestamp predated the run I was asking about. So an
# interrupted or killed run leaves this EMPTY, and empty means began-and-did-
# not-finish: a real third answer rather than the last run's verdict wearing
# this run's clothes.
#
# WHAT IT CANNOT TELL ANYONE: whether the verdict is CORRECT. It records what
# this wrapper concluded. Fetching and comparing against the remote by hand
# stays the real proof; this is the faster path to knowing whether that check
# is worth running.
PUSH_VERDICT_FILE="${DIVINEOS_HOME:-$HOME/.divineos}/push_verdict.txt"
mkdir -p "$(dirname "$PUSH_VERDICT_FILE")" 2>/dev/null || true  # fail-soft: bookkeeping must never be the reason a push does not happen
: > "$PUSH_VERDICT_FILE" 2>/dev/null || true  # fail-soft: an unwritable verdict path leaves the file absent, and absent is explicitly NOT evidence of a missing run

# Says it once, in the same words the final status line prints, plus the
# revision being decided so a reader can confirm the answer is about the thing
# they are holding rather than about whatever ran last.
# EACH VALUE ON ITS OWN STATEMENT, and the reason is mechanical rather than
# stylistic: a continuation must be the last character on its line, so no note
# can sit beside a call that is split across lines. The two silences here are
# answering DIFFERENT questions -- a clock that will not answer, and a revision
# lookup outside a repository -- and one shared sentence for two decisions is
# the shape that rots, because a later reader checking whether the clock case
# still holds would find a note about both and have to guess which half is
# theirs.
#
# Both fall back to the literal word unknown rather than an empty field. A
# degraded row stays readable and says WHICH part was unavailable; an empty
# field reads as a format change and tells the reader nothing.
say_verdict() {
    local ts rev
    ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)  # fail-soft: a clock that will not answer yields the word unknown, which keeps the row parseable instead of losing it
    rev=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)  # fail-soft: run outside a repository this has no answer, and naming that beats a row with a hole where the revision belongs
    printf '%s  head=%s  %s\n' "$ts" "$rev" "$1" >> "$PUSH_VERDICT_FILE" 2>/dev/null || true  # fail-soft: an unwritable verdict path must never be the reason a push does not happen, and a missing file is explicitly not evidence of a missing run
}

# Capture which branch is being pushed (last positional argument that
# doesn't start with --). Used for the post-push verification step.
TARGET_BRANCH=""
for arg in "$@"; do
    case "$arg" in
        -*|origin) ;;
        *) TARGET_BRANCH="$arg" ;;
    esac
done

# A REFSPEC HAS TWO HALVES AND THIS READ ONLY ONE. Pushing
# `HEAD:some-branch` left the whole string as the branch name, so the local
# lookup asked for a path inside a commit and the remote lookup asked for a
# ref with a colon in its name. Both found nothing, and the wrapper announced
# that the remote ref was missing after a push that claimed success.
#
# It had landed. Verified by fetching and comparing by hand, which is the only
# reason I know. So this tool -- whose entire purpose is that its verdict
# matches reality -- reported a clean push as a failure the first time it was
# called with an ordinary git form it had simply never seen.
#
# FAILING SAFE IS NOT THE SAME AS BEING RIGHT. The direction was lucky: it
# cried failure over a success rather than the reverse, so nobody would ship
# on a false green. But a refusal nobody can trust gets re-run or ignored, and
# both of those end with the verdict carrying no information.
#
# Split the halves: the left names what is being sent and is resolved locally,
# the right names where it lands and is what the remote is asked for. With no
# colon both are the same string, which is the ordinary case and unchanged.
PUSH_SOURCE="$TARGET_BRANCH"
case "$TARGET_BRANCH" in
    *:*)
        PUSH_SOURCE="${TARGET_BRANCH%%:*}"
        TARGET_BRANCH="${TARGET_BRANCH##*:}"
        ;;
esac

# Run the actual push. NO pipe — let the output go through unmodified.
# This is the only way to preserve exit code without arithmetic on
# PIPESTATUS or pipefail (both of which have their own subtle gotchas
# in different bash versions / shells).
# WAIT FOR MEMORY RATHER THAN MAKING ME DO IT BY HAND (2026-09-19).
#
# The pre-push suite refuses to spawn below a memory floor, which is a correct
# guard -- the machine has been driven into swap by a test run before. But the
# refusal is TRANSIENT and the correct response is always the same: wait, then
# retry. Three times in one session I wrote that waiting loop by hand.
#
# Andrew, the same session: "you keep making the same mistake over and over,
# and even being fully aware of it does not help.. only structure does.. make
# the mistake impossible to do, by automating the correct choice before you
# need to make it." Hand-writing the wait is not a mistake exactly, but it is
# the same shape -- a correct step that depends on me remembering it, three
# times, with a real failure each time I forgot and reported a blocked push as
# in-flight.
#
# THIS IS NOT A BYPASS AND MUST NOT BECOME ONE. It never lowers the floor and
# never skips the suite. It waits for the condition the guard is asking for.
# Bounded, so a machine that never frees memory fails loudly rather than
# hanging forever, and every wait says so on stderr.
_push_once() {
    echo "[divineos-push] running: git push $*" >&2
    git push "$@"
}

_WAIT_TOTAL=0
_WAIT_CAP=1800
while :; do
    _OUT="$(_push_once "$@" 2>&1)"
    PUSH_EC=$?
    printf '%s\n' "$_OUT"
    if [[ "$PUSH_EC" -eq 0 ]]; then break; fi
    if ! grep -qi "needs at least .* GB free" <<<"$_OUT"; then break; fi
    if [[ "$_WAIT_TOTAL" -ge "$_WAIT_CAP" ]]; then
        echo "[divineos-push] memory never freed after ${_WAIT_TOTAL}s — giving up loudly" >&2
        break
    fi
    echo "[divineos-push] refused for memory, not for readiness. Waiting 60s (${_WAIT_TOTAL}s so far)." >&2
    sleep 60
    _WAIT_TOTAL=$((_WAIT_TOTAL + 60))
done

if [[ "$PUSH_EC" -ne 0 ]]; then
    echo ""
    echo "[divineos-push] result: exit=$PUSH_EC (PUSH_FAILED)"
    say_verdict "REFUSED exit=$PUSH_EC (PUSH_FAILED) -- the gate said no; its reason is in the run output"
    exit "$PUSH_EC"
fi

# Push reported success. Now VERIFY by asking origin directly. This
# catches the failure-mode where the underlying git layer says success
# but the ref didn't actually update on the remote (race condition,
# protected-branch silent skip, or wrapper-lie at a layer below).
if [[ -z "$TARGET_BRANCH" ]]; then
    # No branch arg parsed — can't verify. This is rare (default-push
    # case); fall through with UNVERIFIED.
    echo ""
    echo "[divineos-push] result: exit=0 (PUSHED+UNVERIFIED, no branch arg to verify)"
    say_verdict "PUSHED+UNVERIFIED exit=0 -- no branch argument, so this wrapper could not confirm the remote moved"
    exit 0
fi

# Resolve the LEFT half of the refspec -- what is being sent. With no colon
# this is the same string as the destination, which is the ordinary case.
LOCAL_SHA="$(git rev-parse "$PUSH_SOURCE" 2>/dev/null)"  # fail-soft: an unresolvable source is reported as UNVERIFIED two lines below rather than swallowed, so the error text would only duplicate a verdict the caller already gets in words
if [[ -z "$LOCAL_SHA" ]]; then
    echo ""
    echo "[divineos-push] result: exit=0 (PUSHED+UNVERIFIED, local ref '$PUSH_SOURCE' missing)"
    say_verdict "PUSHED+UNVERIFIED exit=0 -- local ref '$PUSH_SOURCE' missing, so no comparison was possible"
    exit 0
fi

# Look up the remote ref. Sleep briefly to let GitHub propagate (rare
# but not zero).
sleep 1
REMOTE_SHA="$(git ls-remote origin "refs/heads/$TARGET_BRANCH" 2>/dev/null | awk '{print $1}')"

if [[ -z "$REMOTE_SHA" ]]; then
    echo ""
    echo "[divineos-push] WARNING: remote ref refs/heads/$TARGET_BRANCH not found after push" >&2
    echo "[divineos-push] result: exit=22 (PUSH_FAILED_silently — remote ref missing)"
    say_verdict "REFUSED exit=22 -- the remote ref is missing after a push that claimed success"
    exit 22
fi

if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
    echo ""
    echo "[divineos-push] WARNING: local sha $LOCAL_SHA != remote sha $REMOTE_SHA" >&2
    echo "[divineos-push] result: exit=23 (PUSH_FAILED_silently — remote sha mismatch)"
    say_verdict "REFUSED exit=23 -- the remote revision does not match the one pushed"
    exit 23
fi

echo ""
echo "[divineos-push] verified: $TARGET_BRANCH at $LOCAL_SHA on origin"
echo "[divineos-push] result: exit=0 (PUSHED+VERIFIED)"
say_verdict "PUSHED+VERIFIED exit=0 -- the remote carries the revision named above"
exit 0
