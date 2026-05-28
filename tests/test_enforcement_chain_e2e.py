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

    def test_theater_output_does_not_block_next_tool(
        self, tmp_path, gate_passthrough, monkeypatch
    ) -> None:
        # Theater detector reads registered family-members dynamically (post
        # clean-slate). Inject "aria" so the SUBAGENT_DIALOGUE detector has
        # something to match against on a fresh-install CI environment.
        from divineos.core.self_monitor import theater_monitor

        monkeypatch.setattr(theater_monitor, "_family_member_names", lambda: ("Aria",))

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
            # Step 1: both markers exist. compass-required (gate 1.47) runs
            # first in the gate order. Advisory fires (advised_count: 0 -> 1).
            # The advisory message contains the kind ("correction").
            decision = pre_tool_use_gate._check_gates()
            assert decision is not None
            assert "correction" in str(decision).lower()

            # Step 2: clear correction; compass-required still set with
            # advised_count=1 from step 1. Simulate a fresh turn by
            # patching dedup to return False (new turn = no per-turn
            # suppression). Gate fires again, still advisory (count
            # 1 -> 2 means next time will escalate).
            correction_marker.clear_marker()
            with patch.object(
                compass_required_marker, "should_dedup_within_turn", return_value=False
            ):
                decision = pre_tool_use_gate._check_gates()
                assert decision is not None
                assert "compass" in str(decision).lower()

    def test_compass_marker_escalates_after_threshold(
        self, tmp_path, allow_cascade, gate_passthrough
    ) -> None:
        """After ESCALATION_THRESHOLD advisory fires, gate hard-blocks."""
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test trigger")

            # Patch dedup to False so each call counts as a fresh turn.
            with patch.object(
                compass_required_marker, "should_dedup_within_turn", return_value=False
            ):
                # First fire: advisory (allow + additionalContext).
                d1 = pre_tool_use_gate._check_gates()
                assert d1 is not None
                assert d1["hookSpecificOutput"]["permissionDecision"] == "allow"
                assert "compass" in str(d1).lower()

                # Second fire: still advisory but with "still pending" prefix.
                d2 = pre_tool_use_gate._check_gates()
                assert d2 is not None
                assert d2["hookSpecificOutput"]["permissionDecision"] == "allow"
                assert "still pending" in str(d2).lower()

                # Third fire: ESCALATION_THRESHOLD reached, hard BLOCK.
                d3 = pre_tool_use_gate._check_gates()
                assert d3 is not None
                assert d3["hookSpecificOutput"]["permissionDecision"] == "deny"
                assert "blocked" in str(d3).lower()
                assert "dismiss" in str(d3).lower()  # dismiss path named in BLOCK

    def test_compass_per_turn_dedup_suppresses_re_firing(
        self, tmp_path, allow_cascade, gate_passthrough
    ) -> None:
        """Within PER_TURN_DEDUP_SECONDS, same marker does not re-fire."""
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test trigger")

            # First fire: advisory, count 0 -> 1, last_advised_ts = now.
            d1 = pre_tool_use_gate._check_gates()
            assert d1 is not None
            assert "compass" in str(d1).lower()

            # Second fire IMMEDIATELY: dedup window active, gate suppresses
            # the compass advisory. Some other gate may fire (or none).
            # The decision either does not contain compass, OR is None
            # (compass gate passed through).
            d2 = pre_tool_use_gate._check_gates()
            if d2 is not None:
                # If a gate fired, it is NOT compass-required.
                assert "compass-relevant" not in str(d2).lower()


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
