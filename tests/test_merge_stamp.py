"""Tests for the draft->ready trailer stamp (core/watchmen/merge_stamp.py).

The failure these guard against is specific: PR #409 was taken out of
draft, reported ready, and then failed the External-Review trailer check
when Andrew pulled it. Every check below is about the stamp refusing to
certify something a round has not actually earned.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import pytest

from divineos.core.watchmen import merge_stamp

EXTERNAL_AI = frozenset({"aletheia", "external-auditor"})


@dataclass
class _Round:
    round_id: str
    focus: str = "test round"
    created_at: float = 0.0


@dataclass
class _Finding:
    actor: str
    review_stance: str | None = "CONFIRMS"


@pytest.fixture
def fake_store(monkeypatch):
    """Swap the Watchmen store for an in-memory stand-in.

    Patches the names in the store module rather than in merge_stamp,
    because merge_stamp imports them inside the function body.
    """
    state: dict[str, object] = {"round": None, "findings": []}

    def _get_round(round_id: str):
        rnd = state["round"]
        return rnd if rnd is not None and rnd.round_id == round_id else None

    def _list_findings(round_id=None, limit=500, **kwargs):
        return state["findings"]

    monkeypatch.setattr("divineos.core.watchmen.store.get_round", _get_round)
    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", _list_findings)
    return state


def test_missing_round_refuses_and_names_it(fake_store):
    verdict = merge_stamp.validate_round("round-nope", EXTERNAL_AI)
    assert not verdict.ok
    assert "not found" in verdict.reason
    assert verdict.remedy


def test_round_with_no_confirms_refuses_naming_the_user_confirm(fake_store):
    """The exact state PR #409's round was in: a container with no findings."""
    fake_store["round"] = _Round("round-690f358057f3", created_at=time.time())
    fake_store["findings"] = []

    verdict = merge_stamp.validate_round("round-690f358057f3", EXTERNAL_AI)

    assert not verdict.ok
    assert "actor=user" in verdict.reason


def test_user_confirm_alone_is_not_enough(fake_store):
    fake_store["round"] = _Round("round-a", created_at=time.time())
    fake_store["findings"] = [_Finding(actor="user")]

    verdict = merge_stamp.validate_round("round-a", EXTERNAL_AI)

    assert not verdict.ok
    assert "external-AI" in verdict.reason


def test_stale_round_cannot_authorize_even_when_fully_confirmed(fake_store):
    old = time.time() - (merge_stamp.RECENCY_DAYS + 5) * 86400
    fake_store["round"] = _Round("round-old", created_at=old)
    fake_store["findings"] = [_Finding(actor="user"), _Finding(actor="aletheia")]

    verdict = merge_stamp.validate_round("round-old", EXTERNAL_AI)

    assert not verdict.ok
    assert "recency window" in verdict.reason


def test_both_confirms_and_fresh_passes(fake_store):
    fake_store["round"] = _Round("round-good", created_at=time.time())
    fake_store["findings"] = [_Finding(actor="user"), _Finding(actor="aletheia")]

    verdict = merge_stamp.validate_round("round-good", EXTERNAL_AI)

    assert verdict.ok
    assert verdict.age_days < 1.0


def test_non_confirming_stance_does_not_count_as_a_confirm(fake_store):
    fake_store["round"] = _Round("round-b", created_at=time.time())
    fake_store["findings"] = [
        _Finding(actor="user", review_stance="DISPUTES"),
        _Finding(actor="aletheia"),
    ]

    verdict = merge_stamp.validate_round("round-b", EXTERNAL_AI)

    assert not verdict.ok
    assert "actor=user" in verdict.reason


def test_body_carries_the_trailer_with_tree_hash():
    body = merge_stamp.compose_merge_body("round-x", "fix: a thing", 1.5, "deadbeef")

    assert body.splitlines()[0] == "fix: a thing"
    assert "External-Review: round-x tree-hash:deadbeef" in body


def test_body_omits_binding_rather_than_inventing_one():
    """An unresolvable tree must drop the binding, never fabricate a hash."""
    body = merge_stamp.compose_merge_body("round-x", "fix: a thing", 1.5, "")

    assert "External-Review: round-x" in body
    assert "tree-hash" not in body


def test_tree_hash_reports_empty_when_gh_is_unreachable(monkeypatch):
    def _boom(*args, **kwargs):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(merge_stamp.subprocess, "run", _boom)

    assert merge_stamp.pr_head_tree_hash(409) == ""
