"""Tests for Circuit 3: Compass <-> Self-Critique convergence.

When moral compass and self-critique both flag the same concern
independently, the combined signal is more trustworthy than either alone.
"""

import pytest

from divineos.core.convergence_detector import (
    ConvergenceReport,
    ConvergentSignal,
    _classify_signal,
    apply_convergence_to_knowledge,
    detect_convergence,
    format_convergence_report,
)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_circuit3.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))

    from divineos.core.knowledge._base import init_knowledge_table

    init_knowledge_table()
    yield


# ── Signal Classification ───────────────────────────────────────


def test_both_concern_convergent():
    """Both systems flag a problem -> convergent concern."""
    signal = _classify_signal(
        "thoroughness",
        "thoroughness",
        {"position": -0.5, "zone": "deficiency", "observation_count": 5},
        {"average": -0.4, "direction": "declining", "concern": "low thoroughness"},
    )
    assert signal is not None
    assert signal.convergence_type == "both_concern"
    assert signal.combined_confidence > 0.5
    assert "Convergent concern" in signal.description


def test_both_strong_convergent():
    """Both systems see strength -> convergent strength."""
    signal = _classify_signal(
        "thoroughness",
        "thoroughness",
        {"position": 0.3, "zone": "virtue", "observation_count": 5},
        {"average": 0.5, "direction": "improving", "concern": ""},
    )
    assert signal is not None
    assert signal.convergence_type == "both_strong"
    assert "Convergent strength" in signal.description


def test_compass_concern_critique_strong_divergent():
    """Compass concerned but critique strong -> divergence."""
    signal = _classify_signal(
        "precision",
        "communication",
        {"position": -0.5, "zone": "deficiency", "observation_count": 3},
        {"average": 0.6, "direction": "stable", "concern": ""},
    )
    assert signal is not None
    assert signal.convergence_type == "divergent"
    assert "Divergence" in signal.description
    assert signal.combined_confidence == 0.4


def test_compass_strong_critique_concern_divergent():
    """Compass strong but critique weak -> divergence."""
    signal = _classify_signal(
        "engagement",
        "autonomy",
        {"position": 0.2, "zone": "virtue", "observation_count": 4},
        {"average": -0.5, "direction": "declining", "concern": "low autonomy"},
    )
    assert signal is not None
    assert signal.convergence_type == "divergent"


def test_neutral_returns_none():
    """When neither system flags anything notable, no signal."""
    signal = _classify_signal(
        "thoroughness",
        "thoroughness",
        {"position": 0.0, "zone": "virtue", "observation_count": 3},
        {"average": 0.1, "direction": "stable", "concern": ""},
    )
    assert signal is None


def test_combined_confidence_capped_at_one():
    """Combined confidence should not exceed 1.0."""
    signal = _classify_signal(
        "thoroughness",
        "thoroughness",
        {"position": -0.9, "zone": "deficiency", "observation_count": 10},
        {"average": -0.8, "direction": "declining", "concern": "very low"},
    )
    assert signal is not None
    assert signal.combined_confidence <= 1.0


# ── Convergence Report ──────────────────────────────────────────


def test_detect_convergence_returns_report():
    """detect_convergence returns a ConvergenceReport even with no data."""
    report = detect_convergence()
    assert isinstance(report, ConvergenceReport)
    assert isinstance(report.signals, list)
    assert isinstance(report.concerns, list)
    assert isinstance(report.strengths, list)
    assert isinstance(report.divergences, list)


def test_report_classifies_signals():
    """Signals are properly sorted into concerns, strengths, divergences."""
    report = ConvergenceReport()

    concern = ConvergentSignal(
        compass_spectrum="thoroughness",
        critique_spectrum="thoroughness",
        compass_position=-0.5,
        critique_score=-0.4,
        compass_zone="deficiency",
        critique_direction="declining",
        convergence_type="both_concern",
        combined_confidence=0.8,
        description="test concern",
    )
    strength = ConvergentSignal(
        compass_spectrum="precision",
        critique_spectrum="communication",
        compass_position=0.3,
        critique_score=0.5,
        compass_zone="virtue",
        critique_direction="improving",
        convergence_type="both_strong",
        combined_confidence=0.4,
        description="test strength",
    )
    divergence = ConvergentSignal(
        compass_spectrum="engagement",
        critique_spectrum="autonomy",
        compass_position=-0.5,
        critique_score=0.6,
        compass_zone="deficiency",
        critique_direction="stable",
        convergence_type="divergent",
        combined_confidence=0.4,
        description="test divergence",
    )

    report.signals = [concern, strength, divergence]
    report.concerns = [concern]
    report.strengths = [strength]
    report.divergences = [divergence]

    assert len(report.concerns) == 1
    assert len(report.strengths) == 1
    assert len(report.divergences) == 1


# ── Knowledge Storage ───────────────────────────────────────────


def test_apply_convergence_stores_concerns():
    """Convergent concerns are stored as high-confidence OBSERVATION."""
    from divineos.core.knowledge._base import _get_connection

    report = ConvergenceReport(compass_available=True, critique_available=True)
    report.concerns = [
        ConvergentSignal(
            compass_spectrum="thoroughness",
            critique_spectrum="thoroughness",
            compass_position=-0.5,
            critique_score=-0.4,
            compass_zone="deficiency",
            critique_direction="declining",
            convergence_type="both_concern",
            combined_confidence=0.8,
            description="Both systems flag thoroughness",
        )
    ]

    stored = apply_convergence_to_knowledge(report)
    assert stored == 1

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT content, confidence FROM knowledge WHERE content LIKE '%[CONVERGENCE]%'"
        ).fetchone()
        assert row is not None
        assert "[CONVERGENCE]" in row[0]
        assert row[1] == 0.8
    finally:
        conn.close()


def test_apply_convergence_stores_divergences():
    """Divergences are stored as moderate-confidence OBSERVATION."""
    from divineos.core.knowledge._base import _get_connection

    report = ConvergenceReport(compass_available=True, critique_available=True)
    report.divergences = [
        ConvergentSignal(
            compass_spectrum="precision",
            critique_spectrum="communication",
            compass_position=-0.5,
            critique_score=0.6,
            compass_zone="deficiency",
            critique_direction="stable",
            convergence_type="divergent",
            combined_confidence=0.4,
            description="Compass and critique disagree on precision/communication",
        )
    ]

    stored = apply_convergence_to_knowledge(report)
    assert stored == 1

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT content, confidence FROM knowledge WHERE content LIKE '%[DIVERGENCE]%'"
        ).fetchone()
        assert row is not None
        assert row[1] == 0.5  # divergences stored at 0.5
    finally:
        conn.close()


def test_apply_convergence_empty_report():
    stored = apply_convergence_to_knowledge(ConvergenceReport())
    assert stored == 0


# ── Formatting ──────────────────────────────────────────────────


def test_format_no_compass():
    report = ConvergenceReport(compass_available=False)
    text = format_convergence_report(report)
    assert "unavailable" in text


def test_format_no_critique():
    report = ConvergenceReport(compass_available=True, critique_available=False)
    text = format_convergence_report(report)
    assert "unavailable" in text


def test_format_no_signals():
    report = ConvergenceReport(compass_available=True, critique_available=True)
    text = format_convergence_report(report)
    assert "No convergent signals" in text


def test_format_with_concerns():
    report = ConvergenceReport(compass_available=True, critique_available=True)
    report.signals = [
        ConvergentSignal(
            compass_spectrum="thoroughness",
            critique_spectrum="thoroughness",
            compass_position=-0.5,
            critique_score=-0.4,
            compass_zone="deficiency",
            critique_direction="declining",
            convergence_type="both_concern",
            combined_confidence=0.8,
            description="Both flag thoroughness",
        )
    ]
    report.concerns = report.signals

    text = format_convergence_report(report)
    assert "Convergent Concerns" in text
    assert "thoroughness" in text
