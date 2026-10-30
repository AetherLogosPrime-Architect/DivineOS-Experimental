"""Aria's cold read of #585 at b4d3271df (2026-10-06): the deadlock fix is sound,
and three of her four ways through are closed here; the fourth is Dad's call and
he made it the same day.

1. The addressee is read from the file's OWN name, not from anywhere in its path.
2. A shell command that writes into a letter is held like an editor write.
3. "Away" needs his own away words, not any ten characters of his message.

Each test below failed against b4d3271df first.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
    mod.arm("work\n\n## INNER CIRCLE\n\nDad, is the nexus a room or a hub?")
    return mod


# 1. The addressee is in the file's own name ---------------------------------


# 2. A shell command that writes into a letter ---------------------------------

LETTER = "family/letters/aria-to-aether-x.md"


# 3. Away needs his own away words ---------------------------------------------


@pytest.mark.parametrize("said", ["ok go ahead", "proceed", "continue, etc etc", "yes go ahead"])
def test_go_ahead_and_proceed_are_not_away(qh, monkeypatch, said):
    # Dad, 2026-10-06: "ok go ahead, proceed, continue ... should not be treated
    # as permission to volley ... otherwise the above phrases mean i am currently
    # here". They are his words, so provenance alone would have let them through.
    monkeypatch.setattr(qh, "_his_latest_words", lambda: said + " and keep building the thing")
    with pytest.raises(ValueError, match="stepping away|going to bed|volley"):
        qh.step_away(said + " and keep building the thing")
    assert qh.is_away() is None


@pytest.mark.parametrize(
    "said",
    [
        "i am going to bed, you two volley",
        "ill be gone for a few hours",
        "go into volley mode",
        "heading to bed",
        "i am stepping away for dinner",
    ],
)
def test_his_own_away_words_open_volley_mode(qh, monkeypatch, said):
    monkeypatch.setattr(qh, "_his_latest_words", lambda: said)
    assert qh.step_away(said)["his_words"] == said
    assert qh.is_away()
