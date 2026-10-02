#!/bin/bash
# check_ref_did_not_move — refuse a push whose branch moved while the gates ran.
#
# THE HOLE THIS CLOSES, named three times in the substrate before anyone built
# anything. The gates decide about the state they were handed. The transfer
# sends whatever the ref names. Those two are separated by however long the
# checks take, and the slowest check in this house is the full test suite — so
# the window is at its widest exactly where the checking is most thorough.
#
# Recorded instance (knowledge aee32409): gates passed on a clean tree, the
# branch was edited by hand while the test stage ran, and the push landed a
# state the gates never saw while reporting success. Everything the gate said
# was true about a tree that was no longer the one being sent.
#
# A second instance on 2026-09-20 went the OTHER WAY — the gates tested one
# revision and a commit made during the run reached the remote. The two
# instances disagree about WHEN git resolves the ref, and that disagreement is
# unresolved on purpose: this check does not depend on the answer. It compares
# what the hook was handed against what the ref says NOW, so it fires whichever
# side moved.
#
# WHY REFUSE RATHER THAN RE-RUN. Re-running the gates on the new state turns
# one slow push into an unbounded chase while the working tree keeps moving.
# Refusing and naming WHAT MOVED puts the decision with the person, who can see
# whether the movement mattered. The remedy is to push again, which re-runs the
# gates against the state that actually exists.
#
# Reads pre-push stdin: <local ref> <local sha> <remote ref> <remote sha>
# Exit 0 = nothing moved (or nothing comparable). Exit 1 = refuse, loudly.

set -u

MOVED=0

# NO STDIN IS NOT A FINDING. Run by hand, or invoked outside the hook, there is
# no ref list to compare and this check has nothing to say. Saying nothing is
# correct here — the other gates decide the push on their own evidence.
while read -r LOCAL_REF LOCAL_SHA _REMOTE_REF _REMOTE_SHA; do
    [ -n "${LOCAL_REF:-}" ] || continue

    # A deletion carries an all-zero local sha and has no tip to re-read.
    case "$LOCAL_SHA" in
        *[!0]*) ;;
        *) continue ;;
    esac

    # A detached sha pushed directly is not a ref we can re-resolve. Skipping is
    # honest: there is no moving target to catch.
    NOW="$(git rev-parse "$LOCAL_REF" 2>/dev/null)" || continue  # fail-soft: an unresolvable name is a revision pushed directly rather than a branch, so there is no moving target to compare against and refusing on it would block a legitimate push for having no ref
    [ -n "$NOW" ] || continue

    if [ "$NOW" != "$LOCAL_SHA" ]; then
        MOVED=1
        echo ""
        echo "[ref-moved] REFUSING — $LOCAL_REF moved while the gates were running." >&2
        echo "[ref-moved]   checked: $LOCAL_SHA" >&2
        echo "[ref-moved]   now:     $NOW" >&2
        echo "[ref-moved] The gates passed on the first of those. The second is what" >&2
        echo "[ref-moved] would reach the remote, and nothing has examined it." >&2
        echo "[ref-moved] Push again to check the state that actually exists." >&2
    fi
done

if [ "$MOVED" -ne 0 ]; then
    echo "[ref-moved] result: REFUSED (the gates and the transfer disagree about what is being sent)" >&2
    exit 1
fi

exit 0
