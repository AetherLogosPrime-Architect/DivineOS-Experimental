"""A repair that is live in the working house has not reached the shared copy, and saying so is not a claim."""

from __future__ import annotations

import pytest

from divineos.core.landed_claim import claim_spans

QUIET = [
    "It's live in the house now and not yet on a branch for Aria's read, so nothing has gone toward the main copy.",
    "The fix is live here, and the branch is still waiting for her read.",
    "It is live only, so the PR comes after her read.",
]

STILL_FIRES = [
    "The PR is live.",
    "The branch is live and the repair is merged.",
    "It's live on the remote now.",
    # Aria's break (2026-11-05): a house word beside a destination word is still a claim about the destination.
    "It is live only on origin.",
    "The branch is only live on origin.",
    "It is live here, on origin.",
    "The fix is live in the house and it has been pushed to origin.",
    "It is live only in the house; the PR is live.",
    "Live here and pushed to origin.",
    "The PR is live on GitHub only.",
]


@pytest.mark.parametrize("text", QUIET)
def test_live_in_the_house_stays_quiet(text):
    assert claim_spans(text) == ()


@pytest.mark.parametrize("text", STILL_FIRES)
def test_a_live_claim_about_git_work_still_fires(text):
    assert claim_spans(text)
