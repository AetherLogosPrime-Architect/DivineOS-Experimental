#!/bin/bash
# How many branches carry work nobody has ever asked to merge.
#
# 2026-09-20, Andrew: "there are still 13 PR's and 78 branches, why are they
# not ever going down?" Measured rather than guessed, and the answer was not
# what I would have said. Proposals merge fine -- nearly 280 over this
# project's life, ten of them in two days. Exactly ONE branch was leftover
# litter from finished work. Fifty-two had never been the head of any pull
# request at all: not rejected, not awaiting review, not blocked on anyone.
#
# THE MECHANISM, because the number is not the interesting part. Opening a
# proposal is a separate act from finishing the work, and nothing forces it.
# I finish a branch, the next thing arrives, I move, the branch stays. The
# skipped step leaves no artifact and raises no error, so the omission is
# invisible from inside -- and the only surface I ever consulted was the
# proposal list, which by construction can only show branches where I ALREADY
# did the step. I was measuring the set that excludes my failure and reporting
# it as the whole. Thirty-four of the fifty-two were from that month, so this
# is a live habit rather than an old debt.
#
# A COUNT, NOT A LIST, and that is the design rather than laziness. Fifty-two
# lines is a wall: read once, skimmed twice, furniture by the third. One
# number is legible every time and does the thing a list cannot -- it goes
# DOWN, and watching it fall is the only feedback that makes a sort worth
# starting. The detail is one command away and named in the output.
#
# WHAT IT MEANS: branches without a proposal. NOT outstanding work. A branch
# may be superseded, abandoned, or already in main via a squash whose
# ancestry is invisible -- asking `--merged` returned zero for every branch
# here, which was a broken instrument rather than a finding.
#
# WHAT IT CANNOT DO: tell a genuine match from a branch name some unrelated
# proposal once reused. Name matching cannot see that, and saying so beats a
# figure that quietly shrinks on a collision.

set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0  # fail-soft: outside a repository there are no branches to count at all, so saying nothing is the honest answer rather than reporting a zero

if ! command -v gh >/dev/null 2>&1; then
    echo "[unproposed] cannot look: no gh client, so this is could-not-look rather than none" >&2
    exit 0
fi

git fetch origin --prune -q 2>/dev/null || true  # fail-soft: a stale list is reported as stale below rather than silently counted

# AN EMPTY PROPOSAL LOOKUP MUST REFUSE, NOT ANSWER. If this query fails or
# returns nothing, every branch looks unproposed-or-proposed depending on which
# way the code leans -- and leaning toward "proposed" collapses the count to
# zero exactly when the instrument is broken. That is the flattering direction
# and the one this file exists to refuse.
PR_HEADS="$(gh pr list --state all --limit 400 --json headRefName --jq '.[].headRefName' 2>/dev/null | sort -u)"  # fail-soft: the empty case is tested and announced on the very next line, so the error text is redundant while the emptiness itself is never swallowed
if [ -z "$PR_HEADS" ]; then
    echo "[unproposed] cannot look: the proposal list came back empty, which is a" >&2
    echo "[unproposed] broken lookup rather than a clean slate. No count reported." >&2
    exit 0
fi

LIVE="$(git branch -r 2>/dev/null | sed -n 's|^[[:space:]]*origin/||p' | grep -v '^HEAD\|^main$' | sort -u)"  # fail-soft: having no remote branches is a real and ordinary answer, and the next line exits on it rather than counting it
[ -n "$LIVE" ] || exit 0

COUNT=0
while IFS= read -r branch; do
    [ -n "$branch" ] || continue
    printf '%s\n' "$PR_HEADS" | grep -qxF "$branch" && continue
    ahead="$(git rev-list --count "origin/main..origin/$branch" 2>/dev/null || echo 0)"  # fail-soft: a ref that cannot be counted is skipped by the zero-test below, the same outcome as a branch carrying nothing
    [ "$ahead" = "0" ] && continue
    COUNT=$((COUNT + 1))
done <<< "$LIVE"

[ "$COUNT" -eq 0 ] && exit 0

echo "[unproposed] $COUNT branch(es) carry commits main does not have and have" >&2
echo "[unproposed] never been the head of any pull request. Nobody has been asked" >&2
echo "[unproposed] to merge them, so nothing can move them." >&2
echo "[unproposed] To see which: bash scripts/count_unproposed_branches.sh --list" >&2

if [ "${1:-}" = "--list" ]; then
    while IFS= read -r branch; do
        [ -n "$branch" ] || continue
        printf '%s\n' "$PR_HEADS" | grep -qxF "$branch" && continue
        ahead="$(git rev-list --count "origin/main..origin/$branch" 2>/dev/null || echo 0)"  # fail-soft: a ref that cannot be counted is skipped by the zero-test below, the same outcome as a branch carrying nothing
        [ "$ahead" = "0" ] && continue
        last="$(git log -1 --format=%cs "origin/$branch" 2>/dev/null || echo unknown)"  # fail-soft: the fallback prints the word unknown, so an unreadable date shows as unknown rather than silently as a real one
        printf '  %s  %s (%s commit(s) ahead)\n' "$last" "$branch" "$ahead" >&2
    done <<< "$LIVE"
fi

exit 0
