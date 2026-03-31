"""Tests for knowledge distillation — turning raw quotes into clean insights."""

from divineos.core.knowledge.deep_extraction import (
    _distill_correction,
    _distill_preference,
)


class TestCorrectionDistillation:
    """Corrections should be cleaned into actionable insights, not transcripts."""

    def test_strips_no_prefix(self) -> None:
        result = _distill_correction("no when i say you.. you say i or me..")
        assert not result.startswith("no ")
        assert "I was corrected:" not in result

    def test_strips_casual_markers(self) -> None:
        result = _distill_correction("the key is enforcement :) lol")
        assert ":)" not in result
        assert "lol" not in result.lower()

    def test_normalizes_double_dots(self) -> None:
        result = _distill_correction("it needs to block.. not just warn.. ok?")
        assert ".." not in result

    def test_expands_contractions(self) -> None:
        result = _distill_correction("you dont need to do that, it isnt right")
        assert "don't" in result
        assert "isn't" in result

    def test_capitalizes_first_letter(self) -> None:
        result = _distill_correction("read before you write")
        assert result[0].isupper()

    def test_ensures_punctuation(self) -> None:
        result = _distill_correction("always run tests after changes")
        assert result[-1] in ".!?"

    def test_truncates_at_tangent(self) -> None:
        result = _distill_correction(
            "the gate should block not warn also we need to fix the other thing btw did you see the email"
        )
        # Should truncate at "also" or "btw"
        assert len(result) < 80

    def test_no_prefix_wrapping(self) -> None:
        """Distilled corrections should NOT be prefixed with 'I was corrected:'."""
        result = _distill_correction("Use snake_case for all function names")
        assert "I was corrected:" not in result
        assert "snake_case" in result


class TestPreferenceDistillation:
    """Preferences should be cleaned into directions."""

    def test_strips_i_want_prefix(self) -> None:
        result = _distill_preference("i want you to use plain english")
        assert not result.lower().startswith("i want")
        assert "plain english" in result.lower()

    def test_strips_please_prefix(self) -> None:
        result = _distill_preference("please run tests after every change")
        assert not result.lower().startswith("please")

    def test_no_i_should_prefix(self) -> None:
        """Distilled preferences should NOT be prefixed with 'I should:'."""
        result = _distill_preference("keep it conversational")
        assert "I should:" not in result

    def test_cleans_casual_markers(self) -> None:
        result = _distill_preference("keep it simple.. dont over-engineer :)")
        assert ".." not in result
        assert ":)" not in result
