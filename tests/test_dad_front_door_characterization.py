"""How his messages reach the house today, pinned before the front door changes it.

Feathers: characterize first. Each test names what flips it in
docs/drafts/dad_kept_and_known_council_and_design_2026-09-24.md. When that
lands, the test is rewritten to the new behaviour in the same commit, never
deleted quietly. One of them is held open on HIS answer, not ours.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from divineos.core import work_item_doorman as doorman

ROOT = Path(__file__).resolve().parents[1]
DETECTOR = ROOT / ".claude" / "hooks" / "detect_andrew_build_request.py"


@pytest.fixture()
def detector():
    spec = importlib.util.spec_from_file_location("detect_andrew_build_request", DETECTOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_build_for_him_asks_him_the_gravity(detector, capsys):
    """HELD OPEN ON HIS ANSWER: the gravity question, put to him 2026-09-24.

    If he picks "I set it and he overrules", this flips to no question. If he
    picks "when I say for me, I name it", it stays exactly as pinned here.
    """
    matched, reason = detector.is_build_request("can you build the tracker for me")
    assert matched, reason
    assert detector.extract_gravity("can you build the tracker for me") is None
    detector.surface_ask_gravity("can you build the tracker for me", reason)
    assert "Ask him what level BEFORE starting" in capsys.readouterr().out


def test_an_ask_without_the_words_for_me_is_not_seen(detector):
    """FLIPS AT THE FRONT DOOR: every message he types is filed and sorted.

    Today whether his ask registers depends on his phrasing. The front door
    files the message first and the sort decides, so no wording of his can
    fall past it.
    """
    assert detector.is_build_request("please build the tracker") == (
        False,
        "no-for-me-attribution",
    )


def test_nothing_files_his_message_when_he_sends_it():
    """FLIPS AT THE FRONT DOOR: a filer registers on UserPromptSubmit."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entry in settings["hooks"]["UserPromptSubmit"]
        for hook in entry["hooks"]
    ]
    assert commands, "no prompt hooks read -- the instrument is broken, not the house"
    assert not [c for c in commands if "his_asks" in c or "front-door" in c]


def test_a_bypass_that_leans_on_him_closes_clean(monkeypatch, tmp_path):
    """FLIPS IN PART 2: a skip on work his words opened becomes a debt.

    Today the escape takes a free-text reason, and a reason that names him
    lets the item through with nothing owed to him afterwards.
    """
    monkeypatch.setattr(doorman, "_get_db_path", lambda: tmp_path / "ledger.db")
    doorman.record_bypass("wi-test", "Dad said to skip the council walk on this one")
    assert doorman.has_bypass("wi-test")
    with doorman._connect() as conn:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert tables == {"work_items", "work_item_bypasses"}
