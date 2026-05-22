"""Tests for self_grade — recording the agent's own read of a session.

The self-vs-computed divergence machinery was retired 2026-05-22 (decision
58e5ad1d): comparing a self-grade letter to the misfiring composite flagged
honest self-assessment as overclaim. What survives is the recording; the
honest comparison lives in `compass reflect-review` (per-axis) and
`validate --divergence` (vs operator).
"""

from __future__ import annotations

import pytest

from divineos.core.growth import init_session_history_table, record_session_metrics
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.self_grade import init_self_grade_columns, record_self_grade


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()
    init_knowledge_table()
    init_session_history_table()
    init_self_grade_columns()
    yield


def _read_self_grade(session_id: str) -> tuple[str, str]:
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT self_grade, self_grade_evidence FROM session_history WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    return (row[0], row[1]) if row else ("", "")


class TestRecordSelfGrade:
    def test_persists_to_session(self):
        record_session_metrics("sess-1", health_grade="B", health_score=0.75)
        ok = record_self_grade("sess-1", "A", "I think this went better than metrics show")
        assert ok
        grade, evidence = _read_self_grade("sess-1")
        assert grade == "A"
        assert "better than metrics" in evidence

    def test_invalid_grade_rejected(self):
        record_session_metrics("sess-1", health_grade="B", health_score=0.75)
        assert not record_self_grade("sess-1", "X", "")
        assert not record_self_grade("sess-1", "", "")

    def test_missing_session_returns_false(self):
        assert not record_self_grade("nonexistent", "A", "")

    def test_overwrite_updates_existing(self):
        record_session_metrics("sess-1", health_grade="B", health_score=0.75)
        record_self_grade("sess-1", "A", "first read")
        record_self_grade("sess-1", "C", "actually I was wrong")
        grade, evidence = _read_self_grade("sess-1")
        assert grade == "C"
        assert "actually I was wrong" in evidence


class TestDivergenceRetired:
    """Pin the retirement: the module no longer computes self-vs-composite."""

    def test_divergence_machinery_gone(self):
        import divineos.core.self_grade as sg

        for retired in (
            "compute_divergence",
            "calibration_summary",
            "get_calibration_history",
            "CalibrationPoint",
            "grade_letter_to_score",
            "score_to_grade_letter",
        ):
            assert not hasattr(sg, retired), f"{retired} should be retired"
