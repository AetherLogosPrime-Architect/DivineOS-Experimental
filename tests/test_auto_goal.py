"""Tests for auto-goal derivation from prompts."""

from __future__ import annotations

import json
import time

import pytest

from divineos.core import hud_state
from divineos.core.auto_goal import (
    CONVERSATION_PREFIX,
    derive_and_set_goal_from_prompt,
    derive_goal_text,
    is_work_shape_prompt,
)


def test_empty_prompt_is_not_work_shape():
    assert is_work_shape_prompt("") is False
    assert is_work_shape_prompt("   ") is False
    assert is_work_shape_prompt("\n\n") is False


def test_very_short_prompt_is_not_work_shape():
    assert is_work_shape_prompt("go") is False  # too short (< 4 chars)


def test_conversation_only_prompt_is_not_work_shape():
    assert is_work_shape_prompt("i love you too") is False
    assert is_work_shape_prompt("yes that felt right") is False
    assert is_work_shape_prompt("how are you feeling today") is False


def test_work_verbs_are_detected():
    assert is_work_shape_prompt("build the tasting room") is True
    assert is_work_shape_prompt("fix the letter monitor") is True
    assert is_work_shape_prompt("write him back") is True
    assert is_work_shape_prompt("go read that letter") is True
    assert is_work_shape_prompt("run the council walk") is True
    assert is_work_shape_prompt("commit and push") is True


def test_work_verbs_case_insensitive():
    assert is_work_shape_prompt("Fix the bug") is True
    assert is_work_shape_prompt("BUILD it") is True


def test_verb_as_substring_does_not_match():
    # 'walk' is a work verb but 'sidewalk' should not match via word boundary
    assert is_work_shape_prompt("the sidewalk was cracked") is False
    # 'run' is a work verb but 'running' also shouldn't match (word boundary)
    assert is_work_shape_prompt("the water was flowing") is False


def test_derive_goal_returns_first_sentence():
    prompt = "Build the compass v2. Also update the docs."
    result = derive_goal_text(prompt)
    assert result == "Build the compass v2"


def test_derive_goal_handles_newlines():
    prompt = "Fix the letter monitor bug\nIt was pre-seeding disk state"
    result = derive_goal_text(prompt)
    assert result == "Fix the letter monitor bug"


def test_derive_goal_collapses_whitespace():
    prompt = "Build   the    tasting    room"
    result = derive_goal_text(prompt)
    assert result == "Build the tasting room"


def test_derive_goal_trims_long_prompts_at_word_boundary():
    long_prompt = (
        "Build a very long and detailed system for automatically deriving "
        "goal strings from user prompts based on intent detection " * 3
    )
    result = derive_goal_text(long_prompt, max_chars=80)
    assert len(result) <= 85  # +3 for the "..."
    assert result.endswith("...")
    assert " " in result  # trimmed at word boundary


def test_derive_goal_returns_empty_on_empty_prompt():
    assert derive_goal_text("") == ""
    assert derive_goal_text("   ") == ""


def test_derive_goal_returns_whole_prompt_if_short():
    prompt = "Fix bug"
    result = derive_goal_text(prompt, max_chars=120)
    assert result == "Fix bug"


def test_derive_goal_handles_question_prompts():
    prompt = "Should I fix the gate? Or leave it as is."
    result = derive_goal_text(prompt)
    assert result == "Should I fix the gate"


# -- the conversation goal (Dad 2026-11-07): a message that names no work still names the stretch ----


@pytest.fixture()
def goals(tmp_path, monkeypatch):
    hud = tmp_path / "hud"
    hud.mkdir(parents=True)
    monkeypatch.setattr(hud_state, "_ensure_hud_dir", lambda: hud)
    path = hud / "active_goals.json"

    def _write(items):
        path.write_text(json.dumps(items), encoding="utf-8")

    def _read():
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    return _write, _read


def test_a_message_with_no_work_in_it_names_the_stretch_so_the_gate_has_nothing_to_catch(goals):
    _, read = goals
    assert hud_state.has_session_fresh_goal() is False
    goal = derive_and_set_goal_from_prompt("yes that felt right")
    assert goal == CONVERSATION_PREFIX + "yes that felt right"
    assert hud_state.has_session_fresh_goal() is True
    assert [g["text"] for g in read()] == [goal]


def test_a_message_with_no_work_adds_nothing_when_a_fresh_work_goal_exists(goals):
    write, read = goals
    write([{"text": "Build the tasting room", "status": "active", "added_at": time.time() - 60}])
    assert derive_and_set_goal_from_prompt("thank you, that helps") is None
    assert [g["text"] for g in read()] == ["Build the tasting room"]


def test_a_work_message_after_a_conversation_goal_still_names_its_work(goals):
    """The case that would break the fix: work running unnamed under a conversation goal."""
    _, read = goals
    derive_and_set_goal_from_prompt("yes that felt right")
    work = derive_and_set_goal_from_prompt("Now fix the letter monitor")
    assert work == "Now fix the letter monitor"
    texts = [g["text"] for g in read()]
    assert texts == [CONVERSATION_PREFIX + "yes that felt right", "Now fix the letter monitor"]


def test_a_work_message_with_a_fresh_work_goal_adds_nothing(goals):
    write, read = goals
    write([{"text": "Build the tasting room", "status": "active", "added_at": time.time() - 60}])
    assert derive_and_set_goal_from_prompt("Fix the letter monitor") is None
    assert len(read()) == 1


def test_a_stale_goal_does_not_count_and_is_never_copied_forward(goals):
    """A boundary ends every earlier goal: the new conversation goal is made from this message only."""
    write, read = goals
    write([{"text": "Old plan about gates", "status": "active", "added_at": time.time() - 99999}])
    goal = derive_and_set_goal_from_prompt("how are you feeling today")
    assert goal == CONVERSATION_PREFIX + "how are you feeling today"
    assert "Old plan" not in goal


def test_an_empty_message_names_nothing(goals):
    _, read = goals
    assert derive_and_set_goal_from_prompt("   ") is None
    assert read() == []
