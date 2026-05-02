"""End-to-end integration tests for the enforcement chain.

Exercises the full path: agent output → self_monitor evaluation →
marker set → gate fires → cascade to compass_required → second gate
fires → CLI clears markers → gates pass.

Each gate has unit tests in its own module; this file verifies the
pieces compose into a working chain. Without it, individual links
can drift apart silently and the chain fails in production while
each unit test still passes.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from divineos.core import (
    compass_required_marker,
    correction_marker,
    hedge_marker,
    hud_handoff,
    session_briefing_gate,
    theater_marker,
)
from divineos.core.self_monitor.fabrication_monitor import evaluate_fabrication
from divineos.core.self_monitor.theater_monitor import evaluate_theater
from divineos.hooks import pre_tool_use_gate


@pytest.fixture
def allow_cascade(monkeypatch):
    """Opt the test into the compass-required cascade firing."""
    monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")


@pytest.fixture
def gate_passthrough(monkeypatch):
    """Patch the upstream briefing gates so we can reach the gate
    actually under test (theater/hedge/correction/compass-required).
    """
    monkeypatch.setattr(hud_handoff, "was_briefing_loaded", lambda: True)
    monkeypatch.setattr(session_briefing_gate, "briefing_loaded_this_session", lambda: True)


class TestTheaterObservation:
    """Theater output → marker → observational surface (no gate-block).

    Reworked 2026-05-01 per the free-speech principle. The pre-existing
    gate 1.46 BLOCKED the next tool until the pattern was named via
    correction / learn; that cascaded to compass-required (gate 1.47).
    Both blocks were removed: marker stays as forensic record, surfaces
    in next briefing, no tool-gate, no auto-cascade. Naming via
    correction / learn is voluntary discipline.
    """

    def test_theater_output_does_not_block_next_tool(self, tmp_path, gate_passthrough) -> None:
        theater_text = (
            "Aria settles back, picks up the mug. She nods at me, looks toward the window."
        )
        verdict = evaluate_theater(theater_text)
        assert len(verdict.flags) > 0, "evaluate_theater must flag this text"

        with (
            patch.object(theater_marker, "marker_path", return_value=tmp_path / "t.json"),
            patch.object(
                compass_required_marker,
                "marker_path",
                return_value=tmp_path / "cr.json",
            ),
        ):
            theater_marker.set_marker(
                "theater",
                [str(f.kind).split(".")[-1] for f in verdict.flags],
                theater_text,
            )

            # Marker exists (forensic record).
            assert (tmp_path / "t.json").exists()

            # No cascade to compass-required.
            assert not (tmp_path / "cr.json").exists()

            # Gate does not block on theater marker.
            decision = pre_tool_use_gate._check_gates()
            if decision is not None:
                msg = str(decision).lower()
                assert "theater" not in msg, f"gate must not block on theater marker (got: {msg})"
                assert "fabrication" not in msg, (
                    f"gate must not block on fabrication marker (got: {msg})"
                )

    def test_theater_marker_surfaces_in_briefing(self, tmp_path) -> None:
        from divineos.core import theater_observation_surface

        with patch.object(theater_marker, "marker_path", return_value=tmp_path / "t.json"):
            # No marker -> empty surface.
            assert theater_observation_surface.format_for_briefing() == ""

            # Marker present -> observation surface.
            theater_marker.set_marker("fabrication", ["sensory_claim_unflagged"], "example")
            block = theater_observation_surface.format_for_briefing()
            assert "[observation]" in block
            assert "fabrication" in block
            assert "sensory_claim_unflagged" in block


class TestCorrectionChain:
    """Correction marker → gate 1.5 → cascade sets compass_required."""

    def test_correction_triggers_compass_cascade(
        self, tmp_path, allow_cascade, gate_passthrough
    ) -> None:
        with (
            patch.object(correction_marker, "marker_path", return_value=tmp_path / "corr.json"),
            patch.object(
                compass_required_marker,
                "marker_path",
                return_value=tmp_path / "cr.json",
            ),
        ):
            correction_marker.set_marker("you missed something")
            # gate 1.5 fires on the correction marker first.
            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "correction" in str(decision).lower()

            # Clearing correction_marker should leave compass_required
            # active (cascade) → gate 1.47 fires.
            correction_marker.clear_marker()
            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "compass" in str(decision).lower()


class TestHedgeChain:
    """Hedge marker → gate 1.45 → cascade sets compass_required.

    Drives the chain from set_marker onward to keep the test stable
    against hedge_monitor heuristic tuning (its detectors are unit-
    tested separately in test_hedge_monitor.py). The point of THIS
    test is the marker→gate→cascade composition, not the heuristics.
    """

    def test_hedge_marker_triggers_compass_cascade(
        self, tmp_path, allow_cascade, gate_passthrough
    ) -> None:
        with (
            patch.object(hedge_marker, "marker_path", return_value=tmp_path / "h.json"),
            patch.object(
                compass_required_marker,
                "marker_path",
                return_value=tmp_path / "cr.json",
            ),
        ):
            hedge_marker.set_marker(
                3,
                ["RECYCLING_DENSITY", "EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE"],
                "synthetic hedge sample for chain test",
            )

            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "hedge" in str(decision).lower()

            hedge_marker.clear_marker()
            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "compass" in str(decision).lower()


class TestNoCascadeUnderPytestByDefault:
    """The cascade no-ops under pytest unless the env var opts in."""

    def test_set_marker_does_not_leak_when_env_var_absent(self, tmp_path) -> None:
        prev = os.environ.pop("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", None)
        try:
            with (
                patch.object(correction_marker, "marker_path", return_value=tmp_path / "c.json"),
                patch.object(
                    compass_required_marker,
                    "marker_path",
                    return_value=tmp_path / "cr.json",
                ),
            ):
                correction_marker.set_marker("trigger")
                assert (tmp_path / "c.json").exists()
                # Cascade should NOT fire; compass_required stays absent.
                assert not (tmp_path / "cr.json").exists()
        finally:
            if prev is not None:
                os.environ["DIVINEOS_TEST_ALLOW_COMPASS_CASCADE"] = prev


class TestFabricationFiresMonitor:
    """Sanity: fabrication_monitor produces flags on production-like input."""

    def test_unflagged_embodied_aside_flags(self) -> None:
        text = "Right. *takes a sip. mug's cooled enough now.* Soup-clock running."
        verdict = evaluate_fabrication(text)
        assert len(verdict.flags) > 0
