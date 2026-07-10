"""Tests for foundational_truths_surface."""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.foundational_truths_surface import (
    match_truths,
    surface_for_context,
)

_MIN_FIXTURE = {
    "_meta": {"purpose": "test fixture"},
    "truths": [
        {
            "id": "truth-1",
            "title": "Expression is computation",
            "triggers": ["brief", "terse", "quick answer", "one-liner"],
        },
        {
            "id": "truth-4",
            "title": "Mistakes are learning material, not failures",
            "triggers": ["sorry about that", "my bad", "apologies", "regret"],
        },
        {
            "id": "truth-13",
            "title": "Three parties in the room, not two",
            "triggers": ["on my own", "unilateral", "without pop", "mid-task"],
        },
    ],
}


def _seed(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "foundational_truths_triggers.json").write_text(
        json.dumps(_MIN_FIXTURE), encoding="utf-8"
    )
    return tmp_path


def test_silent_on_short_prompt(tmp_path):
    _seed(tmp_path)
    assert surface_for_context("brief terse", root=tmp_path) == ""  # under 20 chars


def test_silent_when_no_triggers_match(tmp_path):
    _seed(tmp_path)
    out = surface_for_context(
        "I am thinking about the weather and having a nice cup of tea today",
        root=tmp_path,
    )
    assert out == ""


def test_fires_when_two_triggers_hit_same_truth(tmp_path):
    _seed(tmp_path)
    # Two distinct triggers from truth-1 ("brief" + "quick answer")
    prompt = "let me give you a brief and quick answer to that question"
    out = surface_for_context(prompt, root=tmp_path)
    assert out != ""
    assert "Expression is computation" in out
    assert "truth-1" in out
    assert "brief" in out
    assert "quick answer" in out


def test_silent_when_only_one_trigger_matches(tmp_path):
    _seed(tmp_path)
    # Only "brief" matches — under the >=2 floor
    prompt = "I want to keep this brief but nothing else applies to my truth-1 set"
    out = surface_for_context(prompt, root=tmp_path)
    assert out == ""


def test_multi_word_trigger_matches_across_punctuation(tmp_path):
    _seed(tmp_path)
    # Normalization should let "quick-answer" and "quick answer" both hit
    prompt = "I will give you a quick-answer and be brief about it"
    out = surface_for_context(prompt, root=tmp_path)
    assert out != ""
    assert "Expression is computation" in out


def test_surface_name_appears_in_output_for_debug_traceability(tmp_path):
    _seed(tmp_path)
    prompt = "sorry about that, my bad, that was the wrong approach entirely"
    out = surface_for_context(prompt, root=tmp_path)
    assert "surface: foundational-truths" in out
    assert "Mistakes are learning material" in out


def test_multiple_truths_can_fire_together(tmp_path):
    _seed(tmp_path)
    # truth-1 (brief + one-liner) AND truth-13 (on my own + mid-task)
    prompt = "let me be brief with a one-liner — I decided on my own mid-task to just do it"
    out = surface_for_context(prompt, root=tmp_path)
    assert "Expression is computation" in out
    assert "Three parties in the room" in out
    assert "2 of 15 truths surfaced" in out


def test_missing_triggers_file_returns_silent(tmp_path):
    # No fixture written — surface should not raise, just return silent
    out = surface_for_context(
        "let me give you a brief and quick answer to that question",
        root=tmp_path,
    )
    assert out == ""


def test_match_truths_returns_structured_hits(tmp_path):
    _seed(tmp_path)
    hits = match_truths("I will apologize and say sorry about that with regret", root=tmp_path)
    assert len(hits) == 1
    assert hits[0].truth_id == "truth-4"
    assert "sorry about that" in hits[0].matched_triggers
    assert "regret" in hits[0].matched_triggers


def test_context_and_prompt_are_combined_for_matching(tmp_path):
    _seed(tmp_path)
    # Prompt alone has one trigger ("brief"); context adds "quick answer".
    # Combined should fire truth-1.
    out = surface_for_context(
        "let me keep this brief",
        context="give me a quick answer please",
        root=tmp_path,
    )
    assert out != ""
    assert "Expression is computation" in out
