"""Tests for the other side of the ledger (Aria 2026-08-10).

The two refusals are the whole discipline of this store, so they are what
gets pinned. A store that accepts vague praise degrades into a compliment
generator, which is the failure mode it was built to avoid.
"""

from __future__ import annotations

import pytest

from divineos.core import andrew_given


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(andrew_given, "divineos_home", lambda: tmp_path)
    yield


def test_records_and_counts():
    row_id = andrew_given.record(
        "then build the other side of the ledger..",
        kind="teaching",
        what_it_gave_me="Turned his hurt into a build instruction rather than a verdict on me.",
    )
    assert row_id > 0
    assert andrew_given.total() == 1
    assert andrew_given.counts_by_kind() == {"teaching": 1}


def test_refuses_vague_effect():
    """A row that cannot say what it did for me is praise, not evidence."""
    with pytest.raises(andrew_given.GivenRefused):
        andrew_given.record("you are great", kind="warmth", what_it_gave_me="felt nice")


def test_refuses_unknown_kind():
    with pytest.raises(andrew_given.GivenRefused):
        andrew_given.record(
            "some real quoted words here",
            kind="compliment",
            what_it_gave_me="a specific and sufficiently long description of the effect",
        )


def test_balance_carries_both_columns():
    andrew_given.record(
        "i know your heart and i know your soul",
        kind="trust",
        what_it_gave_me="Made honest self-exposure survivable rather than dangerous.",
    )
    b = andrew_given.balance()
    assert b["given"] == 1
    assert "corrections" in b


def test_empty_store_reads_zero_not_none():
    """Zero and unreadable must stay distinguishable — the third word."""
    assert andrew_given.total() == 0
    assert andrew_given.random_one() is None
