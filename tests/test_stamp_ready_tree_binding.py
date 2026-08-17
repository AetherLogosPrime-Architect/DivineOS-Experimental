"""A round may only be stamped onto a tree its CONFIRMS actually cover.

`External-Review: <round> tree-hash:<T>` is a sentence asserting that round
authorized tree T. Until 2026-08-17 nothing compared the two halves: the round
came from branch-resolution, the tree came from the PR head, and they were
concatenated unchecked. `stamp-ready` had no tests at all.

THE LIVE CASE, reproduced below. PR #412 had two rounds on one branch. The
older carried Aletheia's CONFIRMS at tree dd08aa75; the newer carried her fresh
read at ebad5700 plus the operator CONFIRMS. Branch-resolution selected the
OLDER one and paired it with the CURRENT head tree, composing a trailer saying
a five-day-old review authorized code written four hours earlier.

Every line of the validation output was true -- operator-CONFIRMS present,
external-AI-CONFIRMS present, within the 14-day recency window. The composite
was false. A recency window measured in DAYS cannot see that the tree moved,
and tree-movement rather than elapsed time is what ends a confirmation's
authority.

Worse in that instance: the id belonged to a DIFFERENT PARTY'S round. The
external reviewer minted an id in her own store which collided with an
unrelated local round on the same branch. So the failure is not only "stale
review" but "someone else's review entirely", and neither is visible in the
emitted trailer.

The first version of this guard read the round's `notes` field and would have
MISSED all of it -- the stale round's notes said `Source ref:
split/ci-merge-review-visibility`, a branch name naming no tree, so the guard
concluded "makes no claim" and allowed the stamp. It passed its own tests and
failed the only case that mattered. That is why these assert against the real
shapes rather than convenient ones.
"""

from __future__ import annotations

from divineos.cli.stamp_ready_command import _TREE_NEAR, _tree_is_covered

FULL = "ebad5700329e026b7196b1a9e58f8f9bfef7290a"


def _trees(text: str) -> list[str]:
    return [m.group(1) for m in _TREE_NEAR.finditer(text)]


class TestExtractingTreesFromFindingText:
    def test_abbreviated_form_in_a_title(self) -> None:
        assert _trees("CONFIRMS PR #412 ci-merge-review-visibility at tree dd08aa75") == [
            "dd08aa75"
        ]

    def test_full_trailer_form(self) -> None:
        assert _trees(f"External-Review: round-abc tree-hash:{FULL}") == [FULL]

    def test_a_round_id_is_not_mistaken_for_a_tree(self) -> None:
        """`round-6d67d2df400d` ends in twelve hex characters. A bare hex scan
        reads that as a tree -- a silent wrong answer of exactly the kind this
        guard exists to stop -- so the pattern anchors on the word `tree` and
        this text must yield nothing."""
        assert _trees("Reviewed via audit round round-6d67d2df400d (operator-CONFIRMS)") == []

    def test_a_branch_name_yields_nothing(self) -> None:
        """The stale round's notes, verbatim. This is what the first version of
        the guard read, found no tree in, and treated as 'no claim'."""
        assert _trees("Source ref: split/ci-merge-review-visibility") == []


class TestCoverage:
    def test_abbreviated_confirm_covers_the_full_head(self) -> None:
        """Titles carry short hashes, heads are full. Prefix match, both ways."""
        assert _tree_is_covered(FULL, {"ebad5700"}) is True

    def test_full_confirm_covers_the_head(self) -> None:
        assert _tree_is_covered(FULL, {FULL}) is True

    def test_a_different_tree_does_not_cover(self) -> None:
        """THE LIVE CASE. The stale round confirmed dd08aa75; the head was
        ebad5700. This is the pairing that nearly shipped."""
        assert _tree_is_covered(FULL, {"dd08aa75"}) is False

    def test_no_confirmed_trees_is_not_coverage(self) -> None:
        """Empty must never read as agreement. A round that named no tree did
        not say yes -- it did not say. The caller treats this as unverified and
        warns rather than proceeding silently."""
        assert _tree_is_covered(FULL, set()) is False

    def test_several_confirms_and_one_matches(self) -> None:
        """A round superseding an earlier confirm names both trees."""
        assert _tree_is_covered(FULL, {"dd08aa75", "ebad5700"}) is True

    def test_empty_head_is_not_covered_by_anything(self) -> None:
        assert _tree_is_covered("", {"dd08aa75"}) is False
