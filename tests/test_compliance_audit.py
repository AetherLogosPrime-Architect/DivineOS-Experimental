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
    from divineos.core.ledger import init_db
    from divineos.core.moral_compass import init_compass

    init_db()
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

    def test_evidence_length_short_fraction(self) -> None:
        _file_ack(0.1, "ack")  # 3 chars — short
        _file_ack(0.1, "ok")  # 2 chars — short
        _file_ack(0.1, "long evidence describing a real calibration event")
        summary = summarize_rudder_acks(window_seconds=3600)
        assert summary["evidence_length"]["fraction_short"] == pytest.approx(2 / 3, abs=0.01)


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

    def test_detects_short_evidence(self) -> None:
        for _ in range(4):
            _file_ack(0.3, "ack")  # short AND non-zero position
        anomalies = detect_anomalies(window_seconds=3600)
        names = {a.name for a in anomalies}
        assert "rudder_ack_short_evidence" in names

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
