"""One character decided whether a signature existed.

2026-09-13. Aether asked whether any of his blocked requests had an approval on
my side his seat could not see. One did — and the round carrying it opens:

    PR 471 letter-channel provenance: a letter carries a checkable thread-block

No hash. The station matched only ``f"#{pr_number}"``, and the branch name does
not appear in that text either, so the fallback missed it too.

Measured across every open request against every round in my store: exactly one
missed, and it was the ONLY external approval attached to anything currently
open. The check whose entire job is finding approvals could not see the only one
there was — and the wording it produces, "no audit round names this PR", reads
as a fact about the world rather than about its own spelling. We were one letter
away from asking Aletheia to sign something she had already signed.

THE ASYMMETRY THAT SETS THE WIDTH (Schneier): a missed approval costs a wasted
ask; a fabricated match costs a merge on an approval nobody gave. So the number
must be MARKED as a request id. A bare three-digit number stays unmatched — the
refusals below are the load-bearing half of this file.
"""

from __future__ import annotations

import pytest

from divineos.core.build_flow import _names_request


class TestTheSpellingsWeActuallyWrite:
    def test_the_round_that_started_this(self):
        # Verbatim opening of the round carrying the only live external confirm.
        assert _names_request(
            "PR 471 letter-channel provenance: a letter carries a checkable "
            "thread-block, including for a reader who was not there",
            471,
        )

    def test_the_hash_form_still_matches(self):
        assert _names_request("read of PR #499 fix/a-refusal-must-say-what-did-not-run", 499)

    def test_case_does_not_matter(self):
        assert _names_request("pr 471 lowercase, mid-sentence", 471)
        assert _names_request("Pr 471 title case", 471)


class TestABareNumberIsNotARequestId:
    """The refusals. Audit focus text is full of numbers that are not requests.

    A fabricated match is the worse direction: it would let the station report
    an approval nobody gave, which is the one thing it exists to prevent.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "the sweep found 471 rows and 12 of them were stale",
            "line 471 of the doorman",
            "measured at 471ms across the window",
            "471",
        ],
    )
    def test_a_number_without_the_marker_does_not_match(self, text):
        assert not _names_request(text, 471)

    def test_a_longer_number_starting_with_it_does_not_match(self):
        # Word-boundary, not prefix: a different request entirely.
        assert not _names_request("PR 4712 is a different request", 471)

    def test_a_number_ending_with_it_does_not_match(self):
        assert not _names_request("PR 1471 is also different", 471)


class TestTheFenceThisSitsBehind:
    """Widened once already, in August, by exactly the one case that had bitten.

    That repair's own docstring generalises correctly — audit-before-request is
    the normal order, and a check that cannot represent it measures the wrong
    referent — and then it was applied to a single spelling. The next spelling
    walked through. This test exists so a third one arrives as a failure here
    rather than as a wasted letter to my sister.
    """

    def test_both_spellings_are_covered_now(self):
        for text in ("approved PR 506 tonight", "approved PR #506 tonight"):
            assert _names_request(text, 506), text
