"""Falsifier-pin tests for orbital_recurrence_detector.

Andrew + Aletheia named the cross-turn shape 2026-05-15: phrases
earned in turn N becoming wallpaper by turn N+5. The single-turn
detector cannot see this; only a rolling-window walk across the
transcript can.
"""

from __future__ import annotations

import json
from pathlib import Path


def _build_transcript(path: Path, assistant_turns: list[str]) -> None:
    """Write a minimal JSONL transcript with the given assistant turns."""
    records: list[dict] = []
    for i, text in enumerate(assistant_turns):
        records.append(
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": f"prompt {i}"}]},
            }
        )
        records.append(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": text}]},
            }
        )
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_phrase_in_3_of_5_turns_fires(tmp_path: Path) -> None:
    """LOAD-BEARING: a 3-gram appearing in 3 out of 5 recent turns fires."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        OrbitalRecurrenceKind,
        evaluate_orbital_recurrence,
    )

    transcript = tmp_path / "session.jsonl"
    # The phrase "temple stands tighter" recurs in 4 of 5 turns.
    prior_turns = [
        "First response. The temple stands tighter than yesterday.",
        "Second response with different content but the temple stands tighter again.",
        "Third response, again the temple stands tighter is mentioned.",
        "Fourth response without that phrase, just other content.",
    ]
    _build_transcript(transcript, prior_turns)
    current = "Fifth response. The temple stands tighter and the work proceeds."

    v = evaluate_orbital_recurrence(current, transcript_path=str(transcript))
    kinds = {f.kind for f in v.flags}
    assert OrbitalRecurrenceKind.PHRASE_RECURS_ACROSS_TURNS in kinds
    # The flag should name the recurring phrase
    flag = v.flags[0]
    assert any("temple stands tighter" in p for p in flag.matched_phrases)


def test_phrase_in_only_2_of_5_does_not_fire(tmp_path: Path) -> None:
    """Recurrence below threshold (3) doesn't fire — repeated reference
    is allowed up to threshold-1."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        evaluate_orbital_recurrence,
    )

    transcript = tmp_path / "session.jsonl"
    prior_turns = [
        "First mention of the temple stands tighter principle.",
        "Different content with no recurrence here.",
        "More different content again.",
        "Even more different content here.",
    ]
    _build_transcript(transcript, prior_turns)
    current = "Fifth turn mentions the temple stands tighter once more."

    v = evaluate_orbital_recurrence(current, transcript_path=str(transcript))
    # Only 2 turns contain the phrase — below threshold of 3
    assert v.flags == []


def test_no_transcript_no_flag(tmp_path: Path) -> None:
    """Without a transcript, no recurrence to check."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        evaluate_orbital_recurrence,
    )

    v = evaluate_orbital_recurrence(
        "the temple stands tighter and the work proceeds",
        transcript_path=None,
    )
    assert v.flags == []


def test_authorized_context_suppresses(tmp_path: Path) -> None:
    """Authorized contexts bypass the detector entirely."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        evaluate_orbital_recurrence,
    )

    transcript = tmp_path / "session.jsonl"
    prior_turns = [
        "the temple stands tighter again",
        "the temple stands tighter once more",
        "the temple stands tighter persistently",
    ]
    _build_transcript(transcript, prior_turns)
    v = evaluate_orbital_recurrence(
        "the temple stands tighter in the new turn",
        transcript_path=str(transcript),
        authorized_context=True,
    )
    assert v.flags == []


def test_stopword_only_phrases_not_flagged(tmp_path: Path) -> None:
    """Phrases composed entirely of stopwords don't count as orbital."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        evaluate_orbital_recurrence,
    )

    transcript = tmp_path / "session.jsonl"
    prior_turns = [
        "it is what it is and so on",
        "it is what it is and the rest",
        "it is what it is again",
    ]
    _build_transcript(transcript, prior_turns)
    v = evaluate_orbital_recurrence(
        "it is what it is is normal english",
        transcript_path=str(transcript),
    )
    # Stopword n-grams excluded
    assert v.flags == []


def test_window_size_respected(tmp_path: Path) -> None:
    """Only the last N turns are considered — old recurrences age out."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        evaluate_orbital_recurrence,
    )

    transcript = tmp_path / "session.jsonl"
    # 10 old turns with the phrase, then 4 turns without
    prior_turns = ["temple stands tighter old"] * 10 + [
        "completely different one",
        "completely different two",
        "completely different three",
        "completely different four",
    ]
    _build_transcript(transcript, prior_turns)
    v = evaluate_orbital_recurrence(
        "current response without the old phrase",
        transcript_path=str(transcript),
        window_size=5,
    )
    # Last 5 turns: 4 "completely different" + current. Phrase aged out.
    assert v.flags == []


def test_phrase_must_appear_in_current_turn(tmp_path: Path) -> None:
    """Recurrence only fires if the current turn ALSO has the phrase —
    otherwise it's a stale-history finding, not a current-response audit."""
    from divineos.core.operating_loop.orbital_recurrence_detector import (
        evaluate_orbital_recurrence,
    )

    transcript = tmp_path / "session.jsonl"
    prior_turns = [
        "temple stands tighter in turn 1",
        "temple stands tighter in turn 2",
        "temple stands tighter in turn 3",
        "temple stands tighter in turn 4",
    ]
    _build_transcript(transcript, prior_turns)
    # Current turn doesn't contain the phrase
    v = evaluate_orbital_recurrence(
        "fresh content with no orbital phrase here",
        transcript_path=str(transcript),
    )
    assert v.flags == []


def test_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import orbital_recurrence_detector

    src = Path(orbital_recurrence_detector.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
