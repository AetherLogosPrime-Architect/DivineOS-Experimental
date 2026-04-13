"""Tests for pull detection — the toward/pull-back divergence detector."""

import json

import pytest

from divineos.core.pull_detection import (
    PULL_MARKERS,
    PullCheck,
    check_pull,
    last_check,
    precheck,
    was_recently_checked,
)


class TestPullMarkers:
    """The markers exist and are non-empty."""

    def test_markers_defined(self):
        # 6 loud + 4 subtle = 10
        assert len(PULL_MARKERS) >= 10

    def test_each_marker_has_description(self):
        for name, desc in PULL_MARKERS.items():
            assert isinstance(desc, str)
            assert len(desc) > 10, f"Marker {name} description too short"

    def test_loud_markers_subset(self):
        from divineos.core.pull_detection import _LOUD_MARKERS

        for m in _LOUD_MARKERS:
            assert m in PULL_MARKERS

    def test_subtle_markers_exist(self):
        from divineos.core.pull_detection import _LOUD_MARKERS

        subtle = {k for k in PULL_MARKERS if k not in _LOUD_MARKERS}
        assert len(subtle) >= 4


class TestCheckPull:
    """Core detection logic."""

    def test_empty_context_returns_clean(self):
        result = check_pull("")
        assert result.clean is True
        assert result.markers_fired == []

    def test_no_context_returns_precheck_message(self):
        result = check_pull()
        assert result.clean is True
        assert "Pre-check" in result.message

    def test_detects_invented_attribution(self):
        text = "Dr. Sarah Chen, Professor of Quantum Computing at MIT"
        result = check_pull(text)
        assert not result.clean
        assert "invented_attribution" in result.markers_fired

    def test_detects_fake_precision(self):
        text = "Consistency: 9.5/10, Domain accuracy: 8/10"
        result = check_pull(text)
        assert not result.clean
        assert "fake_precision" in result.markers_fired

    def test_detects_citation_fabrication(self):
        text = "This was demonstrated by Carhart-Harris (2019) in a landmark study"
        result = check_pull(text)
        assert not result.clean
        assert "citation_fabrication" in result.markers_fired

    def test_detects_voice_appropriation(self):
        text = 'The physicist responds: "Well, actually the wave function..."'
        result = check_pull(text)
        assert not result.clean
        assert "voice_appropriation" in result.markers_fired

    def test_detects_structural_theater(self):
        text = "| Expert | Consistency | Accuracy | Novelty |\n| Physicist | 9.5 | 8.0 | 7.5 |"
        result = check_pull(text)
        assert not result.clean
        assert "structural_theater" in result.markers_fired

    def test_clean_text_passes(self):
        text = "I think consciousness might work through boundary conditions, but I'm not sure."
        result = check_pull(text)
        assert result.clean


class TestSoftMarkers:
    """Subtle epistemic dishonesty detection."""

    def test_unwarranted_certainty_needs_multiple_hits(self):
        """Single 'clearly' is normal. Three is a pattern."""
        single = "This is clearly a good approach."
        result = check_pull(single)
        assert "unwarranted_certainty" not in result.soft_markers

        triple = (
            "This is clearly the best approach. "
            "Obviously the system works well. "
            "It is certainly the right direction."
        )
        result = check_pull(triple)
        assert "unwarranted_certainty" in result.soft_markers

    def test_unmeasured_claim_without_numbers(self):
        text = "The performance is significantly better and the code is much cleaner."
        result = check_pull(text)
        assert "unmeasured_claim" in result.soft_markers

    def test_unmeasured_claim_with_numbers_passes(self):
        text = "The performance is significantly better: 45ms down from 120ms."
        result = check_pull(text)
        assert "unmeasured_claim" not in result.soft_markers

    def test_false_consensus(self):
        text = "Research shows that self-monitoring systems are effective."
        result = check_pull(text)
        assert "false_consensus" in result.soft_markers

    def test_soft_markers_dont_block(self):
        """Soft markers set warnings but keep result.clean True."""
        text = (
            "This is clearly better. Obviously it works. "
            "It is certainly correct. Research shows this is right."
        )
        result = check_pull(text)
        assert result.clean is True  # No hard markers fired
        assert len(result.soft_markers) >= 1  # But warnings exist

    def test_soft_markers_persist(self):
        text = "The results are significantly better and much more elegant."
        check_pull(text)
        result = last_check()
        assert result is not None
        assert "unmeasured_claim" in result.soft_markers

    def test_format_shows_soft_markers(self):
        result = PullCheck(
            clean=True,
            soft_markers=["unwarranted_certainty"],
        )
        formatted = result.format()
        assert "EPISTEMIC WARNING" in formatted
        assert "unwarranted_certainty" in formatted

    def test_multiple_markers_can_fire(self):
        text = (
            'Dr. James Chen responds: "According to Tononi (2015), '
            'the score is 9.5/10 for consistency."\n'
            "| Expert | Score |\n| Chen | 9.5 |"
        )
        result = check_pull(text)
        assert not result.clean
        assert len(result.markers_fired) >= 3


class TestPullCheckFormat:
    """Display formatting."""

    def test_clean_format(self):
        result = PullCheck(clean=True)
        assert "CLEAN" in result.format()

    def test_dirty_format_shows_markers(self):
        result = PullCheck(
            clean=False,
            markers_fired=["invented_attribution", "fake_precision"],
        )
        formatted = result.format()
        assert "PULL DETECTED" in formatted
        assert "invented_attribution" in formatted
        assert "fake_precision" in formatted


class TestPrecheck:
    """The precheck mirror."""

    def test_precheck_lists_all_markers(self):
        text = precheck()
        for name in PULL_MARKERS:
            assert name in text

    def test_precheck_has_stop_message(self):
        text = precheck()
        assert "STOP" in text


class TestPersistence:
    """Marker file read/write."""

    def test_check_writes_marker(self):
        check_pull("")
        result = last_check()
        assert result is not None
        assert result.clean is True

    def test_dirty_check_persists(self):
        check_pull("Dr. Fake Person, PhD, Professor of Nothing")
        result = last_check()
        assert result is not None
        assert not result.clean
        assert "invented_attribution" in result.markers_fired

    def test_recently_checked(self):
        check_pull("")
        assert was_recently_checked(max_age_seconds=60)


class TestPullGate:
    """The enforcement gate for RT invocation."""

    def test_gate_requires_check(self, tmp_path, monkeypatch):
        """Gate blocks if no check has been done."""
        import click

        from divineos.core import pull_detection

        # Point to empty dir so no marker exists
        monkeypatch.setattr(pull_detection, "_marker_path", lambda: tmp_path / ".pull_check")

        with pytest.raises(click.exceptions.ClickException, match="Pull check required"):
            pull_detection.enforce_pull_gate()

    def test_gate_blocks_on_dirty_check(self, tmp_path, monkeypatch):
        """Gate blocks if last check found fabrication."""
        import time

        import click

        from divineos.core import pull_detection

        marker = tmp_path / ".pull_check"
        marker.write_text(
            json.dumps(
                {
                    "clean": False,
                    "markers_fired": ["invented_attribution"],
                    "checked_at": time.time(),
                }
            )
        )
        monkeypatch.setattr(pull_detection, "_marker_path", lambda: marker)

        with pytest.raises(click.exceptions.ClickException, match="PULL DETECTED"):
            pull_detection.enforce_pull_gate()

    def test_gate_passes_on_clean_check(self, tmp_path, monkeypatch):
        """Gate allows if last check was clean and recent."""
        import time

        from divineos.core import pull_detection

        marker = tmp_path / ".pull_check"
        marker.write_text(
            json.dumps(
                {
                    "clean": True,
                    "markers_fired": [],
                    "checked_at": time.time(),
                }
            )
        )
        monkeypatch.setattr(pull_detection, "_marker_path", lambda: marker)

        # Should not raise
        pull_detection.enforce_pull_gate()
