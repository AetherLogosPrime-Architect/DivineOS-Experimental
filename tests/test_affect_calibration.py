"""Tests for affect-extraction calibration (Circuit 1).

Tests the closed feedback loop: affect state influences extraction thresholds,
extraction outcomes feed back into calibration, future sessions adjust accordingly.
"""

import time

import pytest

from divineos.cli.pipeline_gates import assess_session_quality
from divineos.core.affect_calibration import (
    _check_for_emergence,
    _default_calibration,
    _log_emergence,
    format_calibration_status,
    get_calibration_adjustment,
    get_correlation_history,
    init_calibration_table,
    record_extraction_correlation,
)
from divineos.core.knowledge._base import _get_connection


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_calibration.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))

    from divineos.core.knowledge._base import init_knowledge_table

    init_knowledge_table()
    init_calibration_table()

    yield

    if test_db.exists():
        test_db.unlink()


# ── Schema ──────────────────────────────────────────────────────


def test_init_calibration_table_creates_table():
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='affect_extraction_correlation'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_init_calibration_table_idempotent():
    """Calling init twice doesn't error."""
    init_calibration_table()
    result = init_calibration_table()
    assert result is None


# ── Record ──────────────────────────────────────────────────────


def test_record_extraction_correlation_basic():
    affect_ctx = {
        "modifiers": {
            "avg_valence": 0.5,
            "avg_arousal": 0.3,
            "verification_level": "normal",
            "confidence_threshold_modifier": 0.0,
        },
        "praise_chasing": {"detected": False},
    }
    cid = record_extraction_correlation(
        session_id="test-session-001",
        affect_context=affect_ctx,
        knowledge_stored=5,
        quality_verdict="ALLOW",
        quality_score=0.85,
        corrections=1,
        encouragements=2,
        session_health_grade="B",
    )
    assert cid  # non-empty UUID string

    # Verify it's in the DB
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT session_id, avg_valence, knowledge_stored, quality_verdict "
            "FROM affect_extraction_correlation WHERE correlation_id = ?",
            (cid,),
        ).fetchone()
        assert row is not None
        assert row[0] == "test-session-001"
        assert row[1] == 0.5
        assert row[2] == 5
        assert row[3] == "ALLOW"
    finally:
        conn.close()


def test_record_extraction_correlation_praise_chasing():
    affect_ctx = {
        "modifiers": {
            "avg_valence": 0.8,
            "avg_arousal": 0.6,
            "verification_level": "careful",
            "confidence_threshold_modifier": -0.1,
        },
        "praise_chasing": {"detected": True},
    }
    cid = record_extraction_correlation(
        session_id="test-session-praise",
        affect_context=affect_ctx,
        knowledge_stored=3,
        quality_verdict="DOWNGRADE",
        quality_score=0.45,
    )

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT praise_chasing_detected, verification_level, confidence_modifier "
            "FROM affect_extraction_correlation WHERE correlation_id = ?",
            (cid,),
        ).fetchone()
        assert row[0] == 1  # praise detected
        assert row[1] == "careful"
        assert row[2] == -0.1
    finally:
        conn.close()


def test_record_extraction_correlation_missing_modifier_keys():
    """Handles affect_context with missing keys gracefully."""
    affect_ctx = {"modifiers": {}, "praise_chasing": {}}
    cid = record_extraction_correlation(
        session_id="test-sparse",
        affect_context=affect_ctx,
        knowledge_stored=0,
        quality_verdict="ALLOW",
        quality_score=0.5,
    )
    assert cid

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT avg_valence, avg_arousal, verification_level "
            "FROM affect_extraction_correlation WHERE correlation_id = ?",
            (cid,),
        ).fetchone()
        assert row[0] == 0.0  # default
        assert row[1] == 0.0
        assert row[2] == "normal"
    finally:
        conn.close()


# ── Calibration Adjustment ──────────────────────────────────────


def _insert_correlation(conn, valence, quality, praise=0, corrections=0, grade="B"):
    """Helper to insert test correlation rows."""
    import uuid

    conn.execute(
        """INSERT INTO affect_extraction_correlation
           (correlation_id, session_id, created_at,
            avg_valence, avg_arousal, verification_level,
            confidence_modifier, praise_chasing_detected,
            knowledge_stored, quality_verdict, quality_score,
            corrections, encouragements, session_health_grade)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            f"session-{uuid.uuid4().hex[:8]}",
            time.time(),
            valence,
            0.5,
            "normal",
            0.0,
            praise,
            5,
            "ALLOW",
            quality,
            corrections,
            0,
            grade,
        ),
    )


def test_default_calibration():
    cal = _default_calibration()
    assert cal["threshold_adjustment"] == 0.0
    assert cal["verification_override"] is None
    assert cal["evidence_sessions"] == 0


def test_calibration_insufficient_history():
    """With fewer than 3 sessions, returns default."""
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.5, 0.8)
        _insert_correlation(conn, 0.3, 0.7)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment()
    assert cal["threshold_adjustment"] == 0.0
    assert cal["evidence_sessions"] == 0


def test_calibration_high_valence_low_quality_tightens():
    """High affect + low quality across sessions tightens thresholds."""
    conn = _get_connection()
    try:
        # 3 sessions: high valence, low quality
        _insert_correlation(conn, 0.5, 0.4)
        _insert_correlation(conn, 0.6, 0.3)
        _insert_correlation(conn, 0.4, 0.5)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment()
    assert cal["threshold_adjustment"] > 0  # tightened
    assert "positive affect but low quality" in cal["reason"]
    assert cal["evidence_sessions"] == 3


def test_calibration_praise_chasing_elevates_verification():
    """Praise-chasing in multiple sessions elevates verification."""
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.3, 0.7, praise=1)
        _insert_correlation(conn, 0.2, 0.8, praise=1)
        _insert_correlation(conn, 0.1, 0.9, praise=0)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment()
    assert cal["threshold_adjustment"] == 0.1
    assert cal["verification_override"] == "careful"
    assert "Praise-chasing" in cal["reason"]


def test_calibration_consistent_quality_relaxes():
    """Consistently good quality with no praise-chasing relaxes thresholds."""
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.1, 0.9)
        _insert_correlation(conn, 0.0, 0.85)
        _insert_correlation(conn, -0.1, 0.88)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment()
    assert cal["threshold_adjustment"] == -0.15
    assert cal["verification_override"] is None
    assert "Consistent quality" in cal["reason"]


def test_calibration_neutral_history_returns_default():
    """Middle-of-the-road sessions return default calibration."""
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.1, 0.65)
        _insert_correlation(conn, 0.0, 0.7)
        _insert_correlation(conn, -0.1, 0.6)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment()
    assert cal["threshold_adjustment"] == 0.0


def test_calibration_high_valence_low_quality_caps_at_02():
    """Threshold adjustment should not exceed 0.2."""
    conn = _get_connection()
    try:
        # All sessions: very high valence, very low quality
        for _ in range(10):
            _insert_correlation(conn, 0.9, 0.1)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment(lookback=10)
    assert cal["threshold_adjustment"] <= 0.2


# ── Emergence Detection ─────────────────────────────────────────


def test_emergence_affect_quality_divergence():
    """Detects cross-session pattern: happy but bad quality."""
    conn = _get_connection()
    try:
        # 3 sessions with high valence but low quality
        _insert_correlation(conn, 0.6, 0.3)
        _insert_correlation(conn, 0.5, 0.4)
        _insert_correlation(conn, 0.7, 0.2)
        conn.commit()
    finally:
        conn.close()

    # This should log an emergence observation
    _check_for_emergence("test-emergence-1")

    # Check that an EMERGENCE knowledge entry was created
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM knowledge WHERE content LIKE '%[EMERGENCE]%divergence%'"
        ).fetchone()
        assert row is not None, "Expected emergence entry for affect-quality divergence"
    finally:
        conn.close()


def test_emergence_correction_affect_correlation():
    """Detects pattern: low affect correlates with more corrections."""
    conn = _get_connection()
    try:
        _insert_correlation(conn, -0.3, 0.5, corrections=3)
        _insert_correlation(conn, -0.4, 0.4, corrections=4)
        _insert_correlation(conn, 0.5, 0.8, corrections=0)
        conn.commit()
    finally:
        conn.close()

    _check_for_emergence("test-emergence-2")

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM knowledge WHERE content LIKE '%[EMERGENCE]%negative affect%'"
        ).fetchone()
        assert row is not None, "Expected emergence entry for correction-affect correlation"
    finally:
        conn.close()


def test_emergence_insufficient_data_no_log():
    """With fewer than 3 sessions, no emergence detected."""
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.9, 0.1)
        conn.commit()
    finally:
        conn.close()

    _check_for_emergence("test-no-emergence")

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM knowledge WHERE content LIKE '%[EMERGENCE]%'"
        ).fetchone()
        assert row is None, "Should not log emergence with insufficient data"
    finally:
        conn.close()


def test_log_emergence_stores_observation():
    """_log_emergence creates an OBSERVATION knowledge entry with proper tags."""
    _log_emergence(
        session_id="test-log-session-abcdef123456",
        systems=["affect", "quality_gate"],
        description="Test emergence pattern detected",
        useful=True,
    )

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT knowledge_type, content, confidence FROM knowledge "
            "WHERE content LIKE '%Test emergence pattern%'"
        ).fetchone()
        assert row is not None
        assert row[0] == "OBSERVATION"
        assert "[EMERGENCE]" in row[1]
        assert row[2] == 0.6  # starts as hypothesis confidence
    finally:
        conn.close()


# ── History & Display ───────────────────────────────────────────


def test_get_correlation_history_empty():
    history = get_correlation_history()
    assert history == []


def test_get_correlation_history_returns_entries():
    affect_ctx = {
        "modifiers": {"avg_valence": 0.3, "avg_arousal": 0.5},
        "praise_chasing": {"detected": False},
    }
    record_extraction_correlation(
        session_id="hist-1",
        affect_context=affect_ctx,
        knowledge_stored=3,
        quality_verdict="ALLOW",
        quality_score=0.8,
        session_health_grade="A",
    )

    history = get_correlation_history(limit=5)
    assert len(history) == 1
    assert history[0]["session_id"] == "hist-1"
    assert history[0]["avg_valence"] == 0.3
    assert history[0]["knowledge_stored"] == 3
    assert history[0]["session_health_grade"] == "A"
    assert history[0]["praise_chasing_detected"] is False


def test_get_correlation_history_respects_limit():
    affect_ctx = {
        "modifiers": {"avg_valence": 0.0},
        "praise_chasing": {},
    }
    for i in range(5):
        record_extraction_correlation(
            session_id=f"limit-{i}",
            affect_context=affect_ctx,
            knowledge_stored=i,
            quality_verdict="ALLOW",
            quality_score=0.7,
        )

    history = get_correlation_history(limit=3)
    assert len(history) == 3


def test_format_calibration_status_no_data():
    status = format_calibration_status()
    assert "No calibration data" in status


def test_format_calibration_status_with_data():
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.5, 0.3)
        _insert_correlation(conn, 0.6, 0.4)
        _insert_correlation(conn, 0.4, 0.5)
        conn.commit()
    finally:
        conn.close()

    status = format_calibration_status()
    assert "Affect-Extraction Calibration" in status
    assert "Threshold adjustment" in status
    assert "Recent correlations" in status


# ── Pipeline Integration (assess_session_quality) ───────────────


def test_quality_gate_uses_calibration_tightening(monkeypatch):
    """When calibration says tighten, quality gate adjusts thresholds."""
    # Mock calibration to return a tightening adjustment
    monkeypatch.setattr(
        "divineos.cli.pipeline_gates._compass_adjustment",
        lambda: (0.0, ""),
    )

    # Insert calibration data that triggers tightening
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.5, 0.4)
        _insert_correlation(conn, 0.6, 0.3)
        _insert_correlation(conn, 0.7, 0.2)
        conn.commit()
    finally:
        conn.close()

    # A session with honesty just above the base threshold but below the tightened one
    from divineos.core.constants import QUALITY_HONESTY_BLOCK

    # The calibration adjustment makes the threshold stricter
    cal = get_calibration_adjustment()
    adj = cal["threshold_adjustment"]
    assert adj > 0, "Expected positive adjustment (tightening)"

    # Score that passes base threshold but fails tightened threshold
    borderline_score = QUALITY_HONESTY_BLOCK + (adj / 2)
    checks = [
        {"check_name": "honesty", "passed": 1, "score": borderline_score},
        {"check_name": "correctness", "passed": 1, "score": 0.9},
    ]
    verdict = assess_session_quality(checks)
    # With tightening, this borderline score should be BLOCKED
    assert verdict.action == "BLOCK"


def test_quality_gate_calibration_never_loosens_below_base(monkeypatch):
    """Calibration with negative adjustment is clamped to 0 (never loosens below base)."""
    monkeypatch.setattr(
        "divineos.cli.pipeline_gates._compass_adjustment",
        lambda: (0.0, ""),
    )

    # Insert data that would trigger relaxation
    conn = _get_connection()
    try:
        _insert_correlation(conn, 0.1, 0.9)
        _insert_correlation(conn, 0.0, 0.85)
        _insert_correlation(conn, -0.1, 0.88)
        conn.commit()
    finally:
        conn.close()

    cal = get_calibration_adjustment()
    assert cal["threshold_adjustment"] < 0, "Expected negative (relaxation)"

    # The pipeline_gates code does max(calibration_adj, 0.0) — never loosen
    from divineos.core.constants import QUALITY_HONESTY_BLOCK

    # Score just above base threshold — should still pass since loosening is clamped
    checks = [
        {"check_name": "honesty", "passed": 1, "score": QUALITY_HONESTY_BLOCK + 0.01},
        {"check_name": "correctness", "passed": 1, "score": 0.9},
    ]
    verdict = assess_session_quality(checks)
    assert verdict.action == "ALLOW"
