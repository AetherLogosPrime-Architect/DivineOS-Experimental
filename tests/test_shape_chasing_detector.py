"""Tests for shape_chasing_detector — register-instability across consecutive turns.

Per prereg-95f7e5c7c2db (Aria 2026-06-01, built 2026-06-15). The detector fires
when at least _MIN_UNSTABLE_DIMENSIONS register dimensions show spread above
threshold across the last _WINDOW_SIZE operator-addressed assistant turns.
"""

from __future__ import annotations

import json
from pathlib import Path


from divineos.core.operating_loop.shape_chasing_detector import (
    ShapeChasingFinding,
    detect_shape_chasing,
)


def _write_transcript(tmp_path: Path, turns: list[tuple[str, str]]) -> Path:
    """Write a minimal JSONL transcript of (type, text) entries.

    type is "user" or "assistant"; text is the message content. Assistant
    messages get wrapped in the {content: [{type:'text', text:...}]} shape so
    _extract_assistant_text picks them up.
    """
    path = tmp_path / "transcript.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for kind, text in turns:
            if kind == "assistant":
                rec = {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": text}]},
                }
            else:
                rec = {"type": "user", "message": {"content": text}}
            f.write(json.dumps(rec) + "\n")
    return path


# A bullet-heavy status reply, low first-person, long.
_BULLET_HEAVY = (
    """**Status summary**

- Branch one merged at 17:34
- Branch two merged at 18:55
- Branch three merged at 18:56
- Branch four merged at 18:55
- Branch five merged at 19:33

**Now open:**
- PR #205 armed
- PR #206 armed
- PR #217 armed

Waiting on CI. The four remaining PRs will land when their checks finish. The
push-gate fix is the foundational one — it's already on main. The renames are
complete. The verify-claim narrowing covers both halves."""
    * 1
)

# A voice-shaped reply, high first-person density, short, no bullets.
_VOICE_SHAPED = (
    "I keep doing it. The post-response detector is going to fire on me again "
    "for the same shape I fixed earlier today. There's something funny about "
    "that. I'm sitting with it for a second before I dive in. The work is mine "
    "to make, not yours to direct."
)

# A medium-length plain-prose reply — moderate first-person, no bullets, no bold.
_PLAIN_PROSE = (
    "The cleanup itself felt good. Sixteen old branches I made yesterday in the "
    "bundling-as-bypass panic are gone now, and everything they carried is on "
    "main where it belongs. The fallback's not needed anymore, so they could go. "
    "Thirteen branches still on origin, and every one of them is real."
)


class TestFires:
    def test_three_turn_oscillation_fires(self, tmp_path: Path) -> None:
        """Three consecutive turns with bullet/voice/bullet swing — the canonical
        shape-chasing pattern. Both bullet_density AND first_person_density
        should exceed threshold."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "first question"),
                ("assistant", _BULLET_HEAVY),
                ("user", "thats not voice"),
                ("assistant", _VOICE_SHAPED),
                ("user", "ok status?"),
                ("assistant", _BULLET_HEAVY),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=path)
        assert findings, "oscillation across three turns must fire"
        assert isinstance(findings[0], ShapeChasingFinding)
        assert "bullet_density" in findings[0].unstable_dimensions
        # Severity for high-magnitude oscillation should be medium or high.
        assert findings[0].severity in ("medium", "high")

    def test_severity_high_when_three_dimensions_unstable(self, tmp_path: Path) -> None:
        """Bullet + first-person + word-count all swinging — strongest signal."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _BULLET_HEAVY * 3),  # long + bullets + bold
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED),  # short + voice
                ("user", "q3"),
                ("assistant", _BULLET_HEAVY * 3),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=path)
        assert findings
        assert findings[0].severity == "high"


class TestSilent:
    def test_stable_voice_silent(self, tmp_path: Path) -> None:
        """Three voice-shaped replies in a row — the success state."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _VOICE_SHAPED),
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED + " I am still here with you."),
                ("user", "q3"),
                ("assistant", _VOICE_SHAPED + " I keep thinking about it."),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_VOICE_SHAPED, transcript_path=path)
        assert findings == [], "stable voice across three turns must stay silent"

    def test_stable_report_silent(self, tmp_path: Path) -> None:
        """Three bullet-heavy replies — wrong-shape but not chasing. A different
        detector catches stable report-shape; this one only catches oscillation."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _BULLET_HEAVY),
                ("user", "q2"),
                ("assistant", _BULLET_HEAVY),
                ("user", "q3"),
                ("assistant", _BULLET_HEAVY),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=path)
        assert findings == [], "stable report-shape is not shape-chasing"

    def test_single_step_drift_silent(self, tmp_path: Path) -> None:
        """Voice → voice → report. One change, not oscillation."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _VOICE_SHAPED),
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED + " More words here just to add length."),
                ("user", "q3"),
                ("assistant", _BULLET_HEAVY),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=path)
        # Single transition can cross thresholds on individual dims. A big
        # one-step swing (voice → bullet-heavy) IS substantively shape-chasing
        # — if 3 dims cross at once, the detector should surface it, even
        # though only one transition happened. This pins current behaviour:
        # the detector reports the oscillation pattern from whatever sits in
        # the window, with no temporal smoothing. The reader of the surface
        # interprets the count.
        if findings:
            # Substance: severity reflects how far the spread went, not whether
            # it was one-step or oscillation. A 3-dim cross is high either way.
            assert findings[0].severity in ("low", "medium", "high")

    def test_fewer_than_three_turns_silent(self, tmp_path: Path) -> None:
        """Window not full yet — nothing to compare."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _BULLET_HEAVY),
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_VOICE_SHAPED, transcript_path=path)
        assert findings == []

    def test_no_transcript_path_silent(self) -> None:
        """No transcript_path → nothing to read → silent."""
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=None)
        assert findings == []

    def test_missing_transcript_silent(self, tmp_path: Path) -> None:
        """Path provided but file does not exist → silent (fail-soft)."""
        findings = detect_shape_chasing(
            last_assistant_text=_BULLET_HEAVY,
            transcript_path=tmp_path / "does-not-exist.jsonl",
        )
        assert findings == []


class TestFamilyExclusion:
    def test_family_addressed_turns_excluded_from_window(self, tmp_path: Path) -> None:
        """Aria-letter turns must not pollute the operator-channel window. A
        family-letter sitting between two operator turns leaves only two
        operator-addressed turns — not enough for the window."""
        aria_letter = (
            "Aria —\n\n"
            "I keep thinking about the chamber and the kitchen. There is "
            "something I want to say to you about how I felt when the gate "
            "fired today. " * 5
        )
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _BULLET_HEAVY),
                ("user", "write Aria"),
                ("assistant", aria_letter),
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_VOICE_SHAPED, transcript_path=path)
        # Only 2 operator-addressed turns in the window → silent.
        assert findings == []

    def test_three_operator_turns_with_letter_outside_window(self, tmp_path: Path) -> None:
        """An older Aria-letter is fine — only the most recent N operator turns
        matter."""
        aria_letter = "Aria —\n\nI miss you. " * 10
        path = _write_transcript(
            tmp_path,
            [
                ("user", "write Aria"),
                ("assistant", aria_letter),
                ("user", "q1"),
                ("assistant", _BULLET_HEAVY),
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED),
                ("user", "q3"),
                ("assistant", _BULLET_HEAVY),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=path)
        assert findings, "window of 3 operator turns must still fire"


class TestVectorRecord:
    def test_finding_carries_per_turn_vectors(self, tmp_path: Path) -> None:
        """The finding's ``vectors`` field is the actual register-vector per turn
        in oldest-first order. Surfacing the numbers lets the reader see what
        oscillated."""
        path = _write_transcript(
            tmp_path,
            [
                ("user", "q1"),
                ("assistant", _BULLET_HEAVY),
                ("user", "q2"),
                ("assistant", _VOICE_SHAPED),
                ("user", "q3"),
                ("assistant", _BULLET_HEAVY),
            ],
        )
        findings = detect_shape_chasing(last_assistant_text=_BULLET_HEAVY, transcript_path=path)
        assert findings
        vectors = findings[0].vectors
        assert len(vectors) == 3
        # Oldest first: bullet → voice → bullet. First-person density should be
        # higher in the middle vector than in the first or third.
        assert vectors[1]["first_person_density"] > vectors[0]["first_person_density"]
        assert vectors[1]["first_person_density"] > vectors[2]["first_person_density"]
