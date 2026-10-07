"""His answer releases the question hold AND closes the ask it filed.

arm() files the question in operator_asks, and an-open-ask-holds-the-work.sh
reads that store. release() used to delete only its own state, so his answer
released one hold and the other held the work again -- twice on 2026-10-01,
each cleared by hand with his words (council-5bd771ef0891).

test_question_hold.py fakes ask_andrew, so it could not see this. These use the
real store, in the per-test database conftest gives every test.
"""

from __future__ import annotations

import pytest

from divineos.core import operator_asks

CIRCLE = "work\n\n## INNER CIRCLE\n\nDad, it is done. Shall I start the next box?"


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    return mod


def _open_ids() -> set[str]:
    return {a["question_id"] for a in operator_asks.open_asks()}


def test_the_control_arming_files_a_real_open_ask(qh):
    state = qh.arm(CIRCLE)
    assert state and state["ask_id"] in _open_ids()


def test_his_message_closes_the_ask_as_well_as_the_hold(qh):
    ask_id = qh.arm(CIRCLE)["ask_id"]
    assert qh.release("his message")
    assert qh.is_open() is None
    assert ask_id not in _open_ids()


def test_his_answer_typed_mid_turn_closes_it_too(qh):
    ask_id = qh.arm(CIRCLE)["ask_id"]
    assert qh.release("his message, mid-turn")
    assert ask_id not in _open_ids()


def test_an_escape_leaves_the_ask_open_because_he_has_not_answered(qh):
    ask_id = qh.arm(CIRCLE)["ask_id"]
    assert qh.release("escape", reason="a half-landed push that cannot wait for him")
    assert qh.is_open() is None
    assert ask_id in _open_ids()


def test_a_store_that_fails_is_logged_and_never_raises(qh, monkeypatch):
    qh.arm(CIRCLE)

    def broken(question_id, resolution):
        raise RuntimeError("store unreachable")

    monkeypatch.setattr(operator_asks, "resolve_ask", broken)
    assert qh.release("his message")  # must not raise inside his hook
    assert "resolve_failed" in qh.HOLD_LOG.read_text(encoding="utf-8")
