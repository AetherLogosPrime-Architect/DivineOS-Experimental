#!/usr/bin/env bash
# Does this fix actually RUN everywhere it has to run?
#
# A commit is not an arrival. On 2026-08-22 three fixes in one session were
# made, committed, and not running where they run: the auto-push descriptor
# fix (in HEAD, reverted in the working copy, still broken in a sibling
# checkout and fourteen worktrees), the is_pytest_scratch host-dependency fix
# (in an unpushed commit while CI failed on it across three PRs), and a
# doorbell built in a worktree and inert by construction.
#
# All three were found by the same manual sweep. This is that sweep, so it
# stops depending on me remembering to run it.
#
# MATCHES A SIGNATURE, NOT A FILE HASH. The first version compared whole-file
# checksums and immediately reported a sibling checkout as missing the fix
# when it had it -- that checkout sits on another branch, so the file differs
# for reasons that have nothing to do with this change. A sweep that cries
# wolf is worse than no sweep: it trains the bypass, which is the shape
# read_gate.py's own header warns about.
#
# MISSING IS NOT ALWAYS AN ACTION ITEM. Read the two cases apart:
#   - Runtime config that must be current everywhere it executes (hooks,
#     settings) -- MISSING is drift, and the fix belongs in every copy now.
#   - Source on a feature branch -- MISSING usually just means that branch
#     has not merged yet, and the delivery is a merge, NOT a hand-copy.
# Copying unmerged source between checkouts to turn this green would be a
# worse failure than the one the script exists to catch.
#
# Usage:  check_fix_reached_all_copies.sh <repo-relative-path> <grep-ERE-signature>
#         The signature is text that is present IFF the fix is present.
# Exit:   0 every copy carries it   1 at least one does not
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {  # fail-soft: the || arm below exits 2 with its own message; suppressing git here only avoids printing the same failure twice
    echo "not inside a git repository" >&2; exit 2; }
[ "$#" -eq 2 ] || { echo "usage: $0 <repo-relative-path> <grep-ERE-signature>" >&2; exit 2; }
REL="$1"; SIG="$2"
PARENT="$(dirname "$REPO_ROOT")"

[ -f "$REPO_ROOT/$REL" ] || { echo "canonical copy missing: $REL" >&2; exit 2; }
grep -qE -- "$SIG" "$REPO_ROOT/$REL" || {
    echo "!! the signature does not match the canonical copy either -- wrong signature?" >&2
    exit 2; }

# Search roots: registered worktrees PLUS sibling checkouts. Siblings matter
# because the two live checkouts that stayed broken were siblings, not
# worktrees; a worktree-only sweep would have missed both.
# Root-discovery stderr is NOT suppressed. A root lost here means a copy
# never examined, and the sweep would then say "every copy carries this
# fix" having looked at fewer places -- the precise silent-under-coverage
# this tool exists to catch, committed inside the tool itself.
ROOTERR="${TMPDIR:-/tmp}/fixsweep_rooterr.$$"; : >"$ROOTERR"
PARTIAL=0
{
    git worktree list --porcelain 2>>"$ROOTERR" | awk '/^worktree /{print substr($0,10)}'
    find "$PARENT" -maxdepth 1 -mindepth 1 -type d 2>>"$ROOTERR" | while read -r d; do
        [ -e "$d/.git" ] && printf '%s
' "$d"
    done
} | sort -u > "${TMPDIR:-/tmp}/fixsweep_roots.$$"
if [ -s "$ROOTERR" ]; then
    PARTIAL=1
    echo "[warn] root discovery reported errors -- coverage below is INCOMPLETE:"
    sed 's/^/    /' "$ROOTERR"
fi
rm -f "$ROOTERR"

MISSING="${TMPDIR:-/tmp}/fixsweep_missing.$$"; : >"$MISSING"
FINDERR="${TMPDIR:-/tmp}/fixsweep_finderr.$$"; : >"$FINDERR"
echo "=== $REL"
echo "    signature: $SIG"

while read -r root; do
    find "$root" -path '*/.git' -prune -o -name "$(basename "$REL")" -type f -print 2>>"$FINDERR"
done < "${TMPDIR:-/tmp}/fixsweep_roots.$$" | sort -u | while read -r found; do
    case "$found" in */"$REL") ;; *) continue ;; esac    # same repo-relative slot only
    label="${found#"$PARENT"/}"
    [ "$found" = "$REPO_ROOT/$REL" ] && label="$label   <- canonical"
    if [ ! -r "$found" ]; then
        # Counted as not-carrying on purpose: unreadable is not proof of
        # presence, and a sweep that skips what it cannot read reports clean
        # while blind. Labelled distinctly so it is never read as "has it".
        echo "    UNREADABLE $label"
        echo "$found" >>"$MISSING"
    elif grep -qE -- "$SIG" "$found"; then
        echo "    has it   $label"
    else
        echo "    MISSING  $label"
        echo "$found" >>"$MISSING"
    fi
done

if [ -s "$FINDERR" ]; then
    PARTIAL=1
    echo "[warn] file search reported errors -- coverage above is INCOMPLETE:"
    sed 's/^/    /' "$FINDERR"
fi
n=$(wc -l <"$MISSING" | tr -d ' ')
rm -f "${TMPDIR:-/tmp}/fixsweep_roots.$$" "$MISSING" "$FINDERR"
if [ "${n:-0}" -eq 0 ] && [ "$PARTIAL" -eq 0 ]; then
    echo "every copy carries this fix."; exit 0
fi
if [ "${n:-0}" -eq 0 ]; then
    echo "no copy was found lacking it, but the sweep was PARTIAL -- do not read this as clean."
    exit 1
fi
echo "$n cop(ies) do NOT carry this fix."
exit 1
