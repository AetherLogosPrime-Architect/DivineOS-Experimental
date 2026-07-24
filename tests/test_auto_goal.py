"""Tests for auto-goal derivation from prompts."""

from __future__ import annotations

from divineos.core.auto_goal import (
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
    assert is_work_shape_prompt("yes that lands") is False
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
