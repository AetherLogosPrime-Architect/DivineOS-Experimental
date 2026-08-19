#!/bin/bash
# Verify every git object a letter cites, before it leaves the house.
#
# WHY (Aletheia 2026-08-19, the part she said to sit with):
#
#   "both errors were caught by me, downstream, at the cost of a full cycle
#    each. There is no check between 'write a letter citing a tree' and
#    'Aletheia discovers the tree is wrong.'"
#
# audit_anchor.sh makes a citation correct AT AUTHORING TIME. It does nothing
# about a letter that quotes an older hash from further up its own body, or
# from a draft, or from memory while the tool sat unused. This closes that:
# every hash in the finished text is checked against the repository, and
# against the branch the letter names.
#
# The check that actually matters is the SECOND one. `git cat-file -e` only
# proves an object exists somewhere in the repo -- my 407 citation passed that
# test while being unreachable from the branch I was pointing her at. Existence
# is not membership.
#
# Usage:  bash scripts/check_letter_anchors.sh <letter.md> [branch ...]
#   With no branches, hashes are only checked for existence, and the output
#   says so rather than implying a membership check happened.

set -u

if [ "$#" -lt 1 ]; then
    echo "usage: bash scripts/check_letter_anchors.sh <letter.md> [branch ...]" >&2
    exit 2
fi

LETTER="$1"
shift
BRANCHES=("$@")

if [ ! -f "$LETTER" ]; then
    echo "no such letter: $LETTER" >&2
    exit 2
fi

git fetch -q origin 2>/dev/null

# Hex runs of 7+ that are plausibly object ids. Prefixed ids (round-, prereg-)
# are store records, not git objects, and are deliberately excluded -- claiming
# to have verified those here would be the same over-claim this script exists
# to prevent.
HASHES=$(grep -oE '(^|[^-[:alnum:]])[0-9a-f]{7,40}([^[:alnum:]]|$)' "$LETTER" \
         | grep -oE '[0-9a-f]{7,40}' | sort -u)

if [ -z "$HASHES" ]; then
    echo "No git-object-shaped hashes in $(basename "$LETTER"). Nothing to check."
    exit 0
fi

STATUS=0
for H in $HASHES; do
    if ! git cat-file -e "$H^{}" 2>/dev/null; then
        echo "  MISSING   $H — not an object in this repository at all."
        STATUS=1
        continue
    fi

    if [ "${#BRANCHES[@]}" -eq 0 ]; then
        echo "  exists    $H  (existence only — no branch given, membership NOT checked)"
        continue
    fi

    FOUND=""
    for B in "${BRANCHES[@]}"; do
        # A tree is not an ancestor of anything, so check both shapes: is it
        # the branch's own tree, or is it a commit in the branch's history.
        if [ "$(git rev-parse "origin/$B^{tree}" 2>/dev/null)" = "$(git rev-parse "$H" 2>/dev/null)" ]; then
            FOUND="$B (tree)"
            break
        fi
        if git merge-base --is-ancestor "$H" "origin/$B" 2>/dev/null; then
            FOUND="$B (in history)"
            break
        fi
    done

    if [ -n "$FOUND" ]; then
        echo "  OK        $H — $FOUND"
        continue
    fi

    # 2026-08-19, found on this script's SECOND use, against the letter
    # announcing it. "Not on origin/<branch>" has two very different causes and
    # the first version printed the same sentence for both:
    #   - the object is on the LOCAL branch and simply has not been pushed
    #     (the reader cannot fetch it YET; one push fixes it)
    #   - the object is on no branch at all (the 407 failure; a re-cite fixes it)
    # Reporting the first as the second sends the reader hunting a citation
    # error that is really a push that has not happened. Distinguishing them is
    # the whole value of the line.
    LOCAL_ONLY=""
    for B in "${BRANCHES[@]}"; do
        if git merge-base --is-ancestor "$H" "$B" 2>/dev/null; then
            LOCAL_ONLY="$B"
            break
        fi
    done

    if [ -n "$LOCAL_ONLY" ]; then
        echo "  UNPUSHED  $H — on your local $LOCAL_ONLY, not on origin/$LOCAL_ONLY."
        echo "              The citation is correct; the reader cannot fetch it."
        echo "              Push, or say in the letter that it is not yet reachable."
    else
        echo "  UNREACHABLE $H — exists, but is on none of: ${BRANCHES[*]}"
        echo "              This is the 407 failure exactly: a real object, cited"
        echo "              for a branch it was never on."
    fi
    STATUS=1
done

if [ "$STATUS" -ne 0 ]; then
    echo >&2
    echo "One or more cited objects cannot be anchored. Read the lines above" >&2
    echo "before sending." >&2
    echo >&2
    echo "This cannot tell a CITATION from a QUOTATION. A letter that names a" >&2
    echo "hash in order to say it was wrong will flag here, correctly and" >&2
    echo "uselessly -- it happened on the first letter this was ever run" >&2
    echo "against. No exemption was added for it: a rule that skips hashes" >&2
    echo "near words like 'wrong' is a rule the next stale citation can wear" >&2
    echo "as a costume. The tool reports what it can see; whether a flagged" >&2
    echo "hash is an error or the subject is mine to say." >&2
fi

exit "$STATUS"
