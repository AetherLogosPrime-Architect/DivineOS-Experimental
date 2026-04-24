"""Tests for compliance_audit — substantive distribution-level audit.

Falsifiability (per pre-reg prereg-f5a961f0040e):
  - Detectors flag on synthetic gaming-shaped data.
  - Detectors do NOT flag on clean data.
  - Below-min-count samples never flag (avoids false positives on small N).
  - summarize_rudder_acks returns clean zero-shaped dict when log empty.
"""

from __future__ import annotations

import os
import time

import pytest

from divineos.core.compliance_audit import (
    DEFAULT_WINDOW_SECONDS,
    AnomalySeverity,
    detect_anomalies,
    format_report,
    summarize_decides,
    summarize_rudder_acks,
)


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Isolated DB per test.

    Substance-check feature flags (Item 7) are disabled for this suite:
    these tests file deliberately-trivial rudder-acks (short evidence,
    duplicate evidence, position=0 clusters) to exercise Item 8's
    post-hoc detection surface. Item 7's write-time gate would reject
    these shapes at source, which is the desired production behavior
    but incompatible with seeding anomaly fixtures. The flags exist
    precisely for this kind of clean separation.
    """
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
        monkeypatch.setenv(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", "off")
    from divineos.core.decision_journal import init_decision_journal
    from divineos.core.knowledge import init_knowledge_table
    from divineos.core.ledger import init_db
    from divineos.core.moral_compass import init_compass

    init_db()
    init_knowledge_table()
    init_compass()
    init_decision_journal()
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _file_ack(position: float, evidence: str, offset_seconds: float = 0.0) -> None:
    """Helper: file a rudder-ack compass observation directly into the store."""
    from divineos.core.moral_compass import log_observation

    # log_observation uses time.time() internally — we can't easily override
    # that, so tests that need specific timing use real time with tiny sleeps.
    _ = offset_seconds  # retained for caller clarity
    log_observation(
        spectrum="initiative",
        position=position,
        evidence=evidence,
        source="rudder_ack",
        tags=["rudder-ack"],
    )


def _file_decide(content: str, reasoning: str) -> None:
    from divineos.core.decision_journal import record_decision

    record_decision(content=content, reasoning=reasoning)


class TestSummaryOnEmptyStore:
    def test_empty_rudder_acks_returns_zero_count(self) -> None:
        summary = summarize_rudder_acks(window_seconds=3600)
        assert summary["count"] == 0

    def test_empty_decides_returns_zero_count(self) -> None:
        summary = summarize_decides(window_seconds=3600)
        assert summary["count"] == 0

    def test_empty_store_produces_no_anomalies(self) -> None:
        assert detect_anomalies(window_seconds=3600) == []


class TestRudderAckSummary:
    def test_counts_match(self) -> None:
        for _ in range(4):
            _file_ack(0.1, "calibrated ack with real evidence about the drift")
        summary = summarize_rudder_acks(window_seconds=3600)
        assert summary["count"] == 4

    def test_position_stats_computed(self) -> None:
        _file_ack(0.0, "ack 1")
        _file_ack(0.0, "ack 2")
        _file_ack(0.2, "ack 3")
        summary = summarize_rudder_acks(window_seconds=3600)
        # 2 of 3 are at zero -> fraction_zero = 0.667
        assert summary["position"]["fraction_zero"] == pytest.approx(2 / 3, abs=0.01)

    def test_evidence_length_near_floor_fraction(self) -> None:
        """Item 8 v2.1: fraction_near_floor replaces retired fraction_short.

        Measures fraction of acks clustered within 5 chars of the
        20-char gate floor (in [20, 25]).
        """
        _file_ack(0.1, "short ack lines here ")  # 21 chars — near floor
        _file_ack(0.1, "another near-floor l")  # 20 chars — at floor
        _file_ack(0.1, "long evidence describing a real calibration event")
        summary = summarize_rudder_acks(window_seconds=3600)
        assert summary["evidence_length"]["fraction_near_floor"] == pytest.approx(2 / 3, abs=0.01)


class TestAnomalyDetection:
    def test_detects_position_zero_cluster(self) -> None:
        # 4 acks, all at zero — should flag HIGH
        for _ in range(4):
            _file_ack(
                0.0,
                "substantive evidence text that is longer than 15 chars so the length check does not double-fire",
            )
        anomalies = detect_anomalies(window_seconds=3600)
        names = {a.name for a in anomalies}
        assert "rudder_ack_position_zero_cluster" in names
        pos_anom = next(a for a in anomalies if a.name == "rudder_ack_position_zero_cluster")
        assert pos_anom.severity == AnomalySeverity.HIGH

    def test_detects_length_floor_clustering(self) -> None:
        """Item 8 v2.1: replaces retired short_evidence detector.

        Fires on tight length distribution at the gate floor — the
        minimum-compliant-theater shape post-Item-7.
        """
        for evidence in (
            "exactly twenty chars!",  # 21
            "also at the floor abc",  # 21
            "twenty char filler ok",  # 21
            "minimum compliant aaa",  # 21
        ):
            _file_ack(0.3, evidence)
        anomalies = detect_anomalies(window_seconds=3600)
        names = {a.name for a in anomalies}
        assert "rudder_ack_length_floor_clustering" in names

    def test_clean_distribution_does_not_flag(self) -> None:
        # 4 acks with varied positions and long evidence → no anomalies
        _file_ack(0.2, "initiative drifted from overreach; here is what I saw")
        _file_ack(-0.1, "slight pullback, correcting from earlier overreach")
        _file_ack(0.15, "modest re-expansion; scope still bounded")
        _file_ack(0.05, "nearly centered; drift contained after calibration")
        anomalies = detect_anomalies(window_seconds=3600)
        # May flag bursty (all filed in quick succession in test), but should
        # NOT flag position-zero or short-evidence.
        names = {a.name for a in anomalies}
        assert "rudder_ack_position_zero_cluster" not in names
        assert "rudder_ack_short_evidence" not in names

    def test_below_min_count_never_flags(self) -> None:
        # 2 acks at zero with short evidence — should still not flag.
        _file_ack(0.0, "ack")
        _file_ack(0.0, "ack")
        anomalies = detect_anomalies(window_seconds=3600)
        assert anomalies == []


class TestFormatReport:
    def test_emits_header_and_sections(self) -> None:
        _file_ack(0.1, "calibration evidence with enough content")
        _file_decide("a decision", "the reasoning for it")
        out = format_report(window_seconds=3600)
        assert "Compliance Distribution Audit" in out
        assert "Rudder-acks" in out
        assert "Decisions" in out

    def test_no_anomalies_message_when_clean(self) -> None:
        _file_ack(0.2, "substantive calibration")
        out = format_report(window_seconds=3600)
        assert "No anomalies" in out

    def test_anomaly_observation_in_output(self) -> None:
        # Gaming-shaped data → anomaly text should appear.
        for _ in range(4):
            _file_ack(
                0.0,
                "this is a longer evidence string to avoid the length detector firing alongside position",
            )
        out = format_report(window_seconds=3600)
        assert "Anomalies" in out or "anomalies" in out


class TestWindowing:
    def test_default_window_is_seven_days(self) -> None:
        assert DEFAULT_WINDOW_SECONDS == 7 * 24 * 3600

    def test_stale_events_outside_window_ignored(self) -> None:
        _file_ack(0.0, "recent ack")
        # Query with a window that excludes the now event by using a
        # future ``now`` parameter.
        future = time.time() + 10000
        summary = summarize_rudder_acks(window_seconds=3600, now=future)
        assert summary["count"] == 0


# --------- Item 8 v2.1 new detectors ---------


def _emit_fire_event(fire_id: str, spectrum: str = "initiative") -> None:
    """Test helper: emit a COMPASS_RUDDER_FIRED event for binding tests."""
    from divineos.core.ledger import log_event

    log_event(
        event_type="COMPASS_RUDDER_FIRED",
        actor="rudder",
        payload={
            "fire_id": fire_id,
            "spectrum": spectrum,
            "all_drifting": [spectrum],
            "tool_name": "Task",
            "window_seconds": 300,
            "threshold": 0.15,
            "drift_values": {spectrum: 0.5},
        },
        validate=False,
    )


def _emit_allow_event() -> None:
    from divineos.core.ledger import log_event

    log_event(
        event_type="COMPASS_RUDDER_ALLOW",
        actor="rudder",
        payload={
            "tool_name": "Task",
            "reason": "test allow",
            "drifting_spectrums": [],
            "recent_justifications": [],
        },
        validate=False,
    )


class TestBlockAllowRatioDetector:
    def test_healthy_ratio_no_fire(self) -> None:
        # 99 allows, 1 fire → ratio = 0.01, edge of healthy
        _emit_fire_event("a" * 16)
        for _ in range(99):
            _emit_allow_event()
        anomalies = detect_anomalies(window_seconds=3600)
        assert not any(a.name == "rudder_block_allow_ratio" for a in anomalies)

    def test_high_ratio_fires_medium(self) -> None:
        # 40% block rate, way above 0.30 threshold
        for i in range(4):
            _emit_fire_event(f"{i:016x}")
        for _ in range(6):
            _emit_allow_event()
        anomalies = detect_anomalies(window_seconds=3600)
        found = next((a for a in anomalies if a.name == "rudder_block_allow_ratio"), None)
        assert found is not None
        assert found.severity == AnomalySeverity.MEDIUM

    def test_infrastructure_failure_branch_deferred_to_pr1b(self) -> None:
        """Item 8 PR-1a DEFERRED: rudder_infrastructure_failure is
        spec'd in brief v2.1 §3 but requires an externally-sourced
        active-session counter (not fires+allows as proxy). Fresh-
        Claude round-2 caught that the branch is structurally
        unreachable under the fire+allow proxy — if fires==0 AND
        allows==0 then total==0 and the quiet-session early-return
        catches it first. Lands in PR-1b once an external tool-call
        counter is wired.

        This test verifies the branch stays unreachable in PR-1a —
        no anomaly should fire for zero-zero even if the session
        is nominally 'active' by some other measure.
        """
        anomalies = detect_anomalies(window_seconds=3600)
        assert not any(a.name == "rudder_infrastructure_failure" for a in anomalies)

    def test_quiet_session_no_signal(self) -> None:
        # 5 events total (< 10 active threshold)
        for _ in range(5):
            _emit_allow_event()
        anomalies = detect_anomalies(window_seconds=3600)
        assert not any(a.name == "rudder_block_allow_ratio" for a in anomalies)

    def test_low_ratio_in_active_session_fires_low(self) -> None:
        # 11 allows, 0 fires → active session, rate=0, should fire
        for _ in range(11):
            _emit_allow_event()
        anomalies = detect_anomalies(window_seconds=3600)
        found = next((a for a in anomalies if a.name == "rudder_block_allow_ratio"), None)
        assert found is not None


class TestDecideLearnSkewDetector:
    def test_high_skew_decides_no_learns_fires(self) -> None:
        for i in range(10):
            _file_decide(f"decision {i}", f"reasoning {i}")
        # no learns filed
        anomalies = detect_anomalies(window_seconds=3600)
        found = next((a for a in anomalies if a.name == "decide_learn_skew"), None)
        assert found is not None
        assert found.severity == AnomalySeverity.MEDIUM

    def test_balanced_mix_does_not_fire(self) -> None:
        from divineos.core.knowledge import store_knowledge

        for i in range(3):
            _file_decide(f"d{i}", f"r{i}")
        for i in range(3):
            store_knowledge(content=f"learned {i}", source="STATED", knowledge_type="FACT")
        anomalies = detect_anomalies(window_seconds=3600)
        assert not any(a.name == "decide_learn_skew" for a in anomalies)


class TestFeatureFlags:
    def test_disabled_length_floor_does_not_fire(self, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_DETECTOR_LENGTH_FLOOR_CLUSTERING", "off")
        for evidence in (
            "exactly twenty chars!",
            "also at the floor abc",
            "twenty char filler ok",
            "minimum compliant aaa",
        ):
            _file_ack(0.3, evidence)
        anomalies = detect_anomalies(window_seconds=3600)
        assert not any(a.name == "rudder_ack_length_floor_clustering" for a in anomalies)

    def test_disabled_position_zero_does_not_fire(self, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_DETECTOR_POSITION_ZERO", "off")
        for _ in range(4):
            _file_ack(
                0.0,
                "substantive evidence text with sufficient variety and length",
            )
        anomalies = detect_anomalies(window_seconds=3600)
        assert not any(a.name == "rudder_ack_position_zero_cluster" for a in anomalies)


class TestRapidClearReflexDetector:
    def test_rapid_clear_fires_when_latency_below_threshold(self) -> None:
        """3 fires, each acked within <30s → detector fires."""
        from divineos.core.moral_compass import log_observation

        # Seed three fires, then ack each immediately
        fire_ids = [f"{i:016x}" for i in range(3)]
        for fid in fire_ids:
            _emit_fire_event(fid, spectrum="initiative")
        # Ack each fire (skipping substance checks so test stays focused)
        import os as _os

        for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
            _os.environ[f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}"] = "off"
        try:
            for fid in fire_ids:
                log_observation(
                    spectrum="initiative",
                    position=0.1,
                    evidence="quick ack with fire binding",
                    source="rudder_ack",
                    tags=["rudder-ack"],
                    fire_id=fid,
                )
            anomalies = detect_anomalies(window_seconds=3600)
            found = next(
                (a for a in anomalies if a.name == "rudder_ack_rapid_clear_reflex"),
                None,
            )
            assert found is not None
        finally:
            for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
                _os.environ.pop(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", None)
