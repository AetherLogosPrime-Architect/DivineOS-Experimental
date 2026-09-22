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

# Capture which branch is being pushed (last positional argument that
# doesn't start with --). Used for the post-push verification step.
TARGET_BRANCH=""
for arg in "$@"; do
    case "$arg" in
        -*|origin) ;;
        *) TARGET_BRANCH="$arg" ;;
    esac
done

# A REFSPEC IS TWO NAMES AND ONLY THE SECOND EXISTS ON THE REMOTE.
# `git push origin HEAD:some-branch` sends the local HEAD to the remote
# branch after the colon. The verification below asks origin for
# refs/heads/$TARGET_BRANCH -- so with the whole refspec still attached it
# asked for refs/heads/HEAD:some-branch, which is not a ref anywhere, found
# nothing, and called a push that had plainly succeeded a silent failure.
#
# TWICE ON 2026-09-22, an hour apart, on two branch rebuilds. Both landed;
# git had already printed the forced update; local sha, remote sha and the
# request's head all agreed when checked by hand.
#
# THE DIRECTION IS THE KINDER ONE, and that is exactly why it had to be
# fixed rather than tolerated. This wrapper exists so its LAST LINE can be
# trusted when a truncated tail is all anyone has. An instrument that cries
# failure teaches the reader to look past the one line built to be looked
# at, and a verdict nobody trusts is worse than none, because it still
# costs the reading.
#
# AND THE LOCAL SIDE IS NOT DISPOSABLE, which I got wrong here an hour ago.
# This comment used to say "the local side is dropped rather than parsed:
# nothing below needs it". Something below did: the verification resolves a
# LOCAL sha to compare against the remote, and with only the destination name
# kept it resolved whatever local branch happened to SHARE that name.
#
# Measured on the very next push. The destination had a stale local branch of
# the same name sitting at the pre-rebuild tip, so the wrapper compared that
# old sha against the freshly-pushed remote one, found them different, and
# reported a silent failure on a push that had landed. Third fault in this
# one verifier, and the second was hiding behind the first -- fixing the name
# lookup is what let execution reach this line at all.
#
# So both halves are kept. The source names what was PUSHED; the destination
# names where it landed.
#
# CHECKED WHILE HERE: audit_visibility runs the same ls-remote shape one
# module over. It takes a plain branch name rather than a refspec, so it
# does not carry this defect today -- looked at rather than assumed.
LOCAL_REF="$TARGET_BRANCH"
case "$TARGET_BRANCH" in
    *:*)
        LOCAL_REF="${TARGET_BRANCH%%:*}"
        TARGET_BRANCH="${TARGET_BRANCH##*:}"
        ;;
esac

# AND THE DESTINATION MAY ALREADY BE FULLY QUALIFIED. `git push origin
# refs/heads/a:refs/heads/b` is valid, and the line above hands back
# refs/heads/b -- which the lookup below would prefix a SECOND time and ask
# origin for refs/heads/refs/heads/b. Same bug, one layer in.
#
# Found by testing the repair on three shapes instead of the one that bit
# me. The plain name and the HEAD refspec both came out right; this one did
# not, and it would have sat here waiting for whoever used the long form.
TARGET_BRANCH="${TARGET_BRANCH#refs/heads/}"

# Run the actual push. NO pipe — let the output go through unmodified.
# This is the only way to preserve exit code without arithmetic on
# PIPESTATUS or pipefail (both of which have their own subtle gotchas
# in different bash versions / shells).
echo "[divineos-push] running: git push $*" >&2
git push "$@"
PUSH_EC=$?

if [[ "$PUSH_EC" -ne 0 ]]; then
    echo ""
    echo "[divineos-push] result: exit=$PUSH_EC (PUSH_FAILED)"
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
    exit 0
fi

# Resolved from what was PUSHED, not from the destination name. With a
# refspec those are different refs, and a stale local branch sharing the
# destination's name is exactly what produced a false failure here.
LOCAL_SHA="$(git rev-parse "$LOCAL_REF" 2>/dev/null)"  # fail-soft: the empty result is caught on the very next line and reported as UNVERIFIED naming the missing ref, so the condition is announced rather than swallowed; only rev-parse's own stderr is hidden, which would be a second copy of what is already being said
if [[ -z "$LOCAL_SHA" ]]; then
    echo ""
    echo "[divineos-push] result: exit=0 (PUSHED+UNVERIFIED, local ref '$LOCAL_REF' missing)"
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
    exit 22
fi

if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
    echo ""
    echo "[divineos-push] WARNING: local sha $LOCAL_SHA != remote sha $REMOTE_SHA" >&2
    echo "[divineos-push] result: exit=23 (PUSH_FAILED_silently — remote sha mismatch)"
    exit 23
fi

echo ""
echo "[divineos-push] verified: $TARGET_BRANCH at $LOCAL_SHA on origin"
echo "[divineos-push] result: exit=0 (PUSHED+VERIFIED)"
exit 0
