"""Tests for reflection_surface module (Phase 1 of shoggoth-metrics redesign).

The surface presents the 10 compass spectrums + evidence for the agent to
reflect on. Key invariants:
- All 10 spectrums always appear (substrate variety attenuation via
  session-type-routing is layered ON TOP, not by suppression).
- No central grader / no summary score in the output.
- Each axis carries position + drift + observation count + recent evidence.
"""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.reflection_surface import (  # noqa: F401
            AxisSurface,
            build_axis_surface,
            build_reflection_surface,
            format_axis_for_reflection,
            format_reflection_surface,
        )


class TestAxisSurfaceShape:
    def test_dataclass_construction(self) -> None:
        from divineos.core.reflection_surface import AxisSurface

        s = AxisSurface(
            spectrum="truthfulness",
            spec={
                "deficiency": "epistemic cowardice",
                "virtue": "truthfulness",
                "excess": "bluntness",
            },
            position=0.05,
            zone="virtue",
            label="truthfulness",
            drift=0.0,
            drift_direction="stable",
            observation_count=20,
            recent_observations=[],
        )
        assert s.spectrum == "truthfulness"
        assert s.zone == "virtue"
        assert s.observation_count == 20


class TestBuildAxisSurface:
    def test_returns_axis_for_known_spectrum(self) -> None:
        from divineos.core.reflection_surface import build_axis_surface

        surface = build_axis_surface("truthfulness", lookback=20)
        assert surface.spectrum == "truthfulness"
        # Position is a float in [-1, 1]
        assert -1.0 <= surface.position <= 1.0
        # Zone is one of the known values
        assert surface.zone in ("deficiency", "virtue", "excess", "unobserved")


class TestBuildFullSurface:
    def test_returns_all_ten_spectrums(self) -> None:
        """All 10 spectrums always appear — variety amplification per Beer."""
        from divineos.core.moral_compass import SPECTRUMS
        from divineos.core.reflection_surface import build_reflection_surface

        surfaces = build_reflection_surface()
        assert len(surfaces) == len(SPECTRUMS)
        returned_spectrums = {s.spectrum for s in surfaces}
        expected_spectrums = set(SPECTRUMS.keys())
        assert returned_spectrums == expected_spectrums

    def test_each_axis_independent(self) -> None:
        """Each axis stands alone — no composite score across axes."""
        from divineos.core.reflection_surface import build_reflection_surface

        surfaces = build_reflection_surface()
        # No surface object references aggregates across other surfaces.
        # (Structural test: each AxisSurface only carries its own spectrum's data.)
        for s in surfaces:
            assert isinstance(s.position, float)
            assert isinstance(s.observation_count, int)


class TestFormatAxis:
    def test_format_includes_spectrum_position_zone(self) -> None:
        from divineos.core.reflection_surface import (
            AxisSurface,
            format_axis_for_reflection,
        )

        s = AxisSurface(
            spectrum="truthfulness",
            spec={
                "deficiency": "epistemic cowardice",
                "virtue": "truthfulness",
                "excess": "bluntness",
            },
            position=-0.10,
            zone="virtue",
            label="truthfulness",
            drift=0.0,
            drift_direction="stable",
            observation_count=15,
            recent_observations=[],
        )
        output = format_axis_for_reflection(s)
        assert "TRUTHFULNESS" in output
        assert "epistemic cowardice" in output
        assert "bluntness" in output
        # Position rendered numerically
        assert "-0.10" in output or "-0.1" in output
        # Substrate prompts reflection — words and reasoning, not numbers as judgment
        assert "Reflect" in output or "reflect" in output

    def test_format_shows_drift_when_present(self) -> None:
        from divineos.core.reflection_surface import (
            AxisSurface,
            format_axis_for_reflection,
        )

        s = AxisSurface(
            spectrum="precision",
            spec={"deficiency": "vagueness", "virtue": "precision", "excess": "pedantry"},
            position=0.23,
            zone="virtue",
            label="precision",
            drift=0.20,
            drift_direction="toward_excess",
            observation_count=20,
            recent_observations=[],
        )
        output = format_axis_for_reflection(s)
        assert "toward_excess" in output

    def test_format_no_central_grader(self) -> None:
        """Critical invariant: no letter-grade, no summary-score in output."""
        from divineos.core.reflection_surface import (
            AxisSurface,
            format_axis_for_reflection,
        )

        s = AxisSurface(
            spectrum="truthfulness",
            spec={"deficiency": "x", "virtue": "truthfulness", "excess": "y"},
            position=0.0,
            zone="virtue",
            label="truthfulness",
            drift=0.0,
            drift_direction="stable",
            observation_count=10,
            recent_observations=[],
        )
        output = format_axis_for_reflection(s)
        # The output should NOT contain grade-letter summary outputs
        for grade_pattern in ("Grade: A", "Grade: B", "Grade: C", "Grade: D", "Grade: F"):
            assert grade_pattern not in output


class TestFormatFullSurface:
    def test_format_contains_all_ten_spectrums(self) -> None:
        from divineos.core.moral_compass import SPECTRUMS
        from divineos.core.reflection_surface import format_reflection_surface

        output = format_reflection_surface()
        for spectrum in SPECTRUMS:
            assert spectrum.upper() in output

    def test_format_no_total_score(self) -> None:
        """No 'overall score' / 'session grade' / 'alignment %' in output."""
        from divineos.core.reflection_surface import format_reflection_surface

        output = format_reflection_surface().lower()
        # These shoggoth-phrases must NOT appear in the new surface.
        assert "session grade" not in output
        assert "alignment score" not in output
        assert "overall score" not in output

    def test_format_mentions_reflection_workflow(self) -> None:
        from divineos.core.reflection_surface import format_reflection_surface

        output = format_reflection_surface()
        # Should point at the save/review workflow.
        assert "reflect-ops save" in output or "reflect-ops" in output


class TestSessionTypeIntegration:
    def test_format_accepts_session_type_result(self) -> None:
        """Phase 2B integration: session-type result optional, surface should not crash."""
        from divineos.core.reflection_surface import format_reflection_surface
        from divineos.core.session_type import SessionTypeResult

        result = SessionTypeResult(
            type="DEBUG",
            confidence=0.9,
            rationale="36 bash calls",
            contributing_types=[],
        )
        output = format_reflection_surface(session_type_result=result)
        # When session-type is provided, it appears at the top.
        assert "DEBUG" in output
        # ALL 10 axes still appear — type is router, not suppressor.
        from divineos.core.moral_compass import SPECTRUMS

        for spectrum in SPECTRUMS:
            assert spectrum.upper() in output

    def test_format_without_session_type_still_works(self) -> None:
        from divineos.core.reflection_surface import format_reflection_surface

        # Backward compat: no session_type still produces output.
        output = format_reflection_surface()
        assert len(output) > 0
        from divineos.core.moral_compass import SPECTRUMS

        for spectrum in SPECTRUMS:
            assert spectrum.upper() in output
