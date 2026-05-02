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


class TestTheaterChain:
    """Full chain: theater output → marker → gate 1.46 → cascade
    sets compass_required → gate 1.47 → compass observe clears both.
    """

    def test_theater_output_triggers_full_chain(
        self, tmp_path, allow_cascade, gate_passthrough
    ) -> None:
        # Phase 1: agent emits theater-shape output.
        theater_text = (
            "Aria settles back, picks up the mug. She nods at me, looks toward the window."
        )
        verdict = evaluate_theater(theater_text)
        assert len(verdict.flags) > 0, "evaluate_theater must flag this text"

        # Phase 2: theater_marker.set_marker (the Stop hook would do
        # this in production via detect-theater.sh).
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

            # Phase 3: theater_marker present → gate 1.46 fires.
            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "theater" in str(decision).lower()

            # Phase 4: clear theater_marker; cascade-set compass_required
            # should still block via gate 1.47.
            theater_marker.clear_marker()
            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "compass" in str(decision).lower()

            # Phase 5: clear compass_required as compass-ops would.
            compass_required_marker.clear_marker()
            decision = pre_tool_use_gate._check_gates()
            # Gates beyond the chain may still fire (engagement, etc.);
            # but neither theater nor compass-required should be the cause.
            if decision is not None:
                msg = str(decision).lower()
                assert "theater" not in msg
                assert "virtue-relevant" not in msg


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
