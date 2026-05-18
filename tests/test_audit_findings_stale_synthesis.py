"""Falsifier for the audit-findings stale_count synthesis fix.

Andrew named the bug in the gate-quest todo: _row_audit_findings was
hardcoding stale_count=0, which made HIGH-severity unresolved findings
get deprioritized into the middle of the briefing under the U-shape
reorder (lost-in-the-middle, Liu et al. 2024). Fix: synthesize
stale_count from severity weights so high-severity findings get
end-position prominence.

These tests pin the weights and the synthesis behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


def _mock_finding(severity: str):
    """Build a mock Finding-shaped object for the row builder."""
    return SimpleNamespace(
        severity=SimpleNamespace(value=severity),
        status=SimpleNamespace(value="OPEN"),
        title=f"test finding ({severity})",
        description="",
        created_at=0,
    )


def test_stale_count_zero_when_no_unresolved_findings() -> None:
    """Row returns None when there are no unresolved findings."""
    from divineos.core.briefing_dashboard import _row_audit_findings

    with patch("divineos.core.watchmen.store.list_findings", return_value=[]):
        row = _row_audit_findings()
    assert row is None


def test_stale_count_synthesizes_from_high_severity() -> None:
    """LOAD-BEARING: HIGH-severity unresolved findings contribute weight 3."""
    from divineos.core.briefing_dashboard import _row_audit_findings

    findings = [_mock_finding("HIGH"), _mock_finding("HIGH")]
    with patch("divineos.core.watchmen.store.list_findings", return_value=findings):
        row = _row_audit_findings()
    assert row is not None
    # 2 HIGH = 2 * 3 = 6
    assert row.stale_count == 6, (
        f"Expected stale_count=6 (2 HIGH findings * weight 3), "
        f"got {row.stale_count}. If this is 0, the synthesis fix has "
        f"regressed and HIGH-severity findings are again invisible to "
        f"the U-shape reorder."
    )


def test_severity_weights_are_correct() -> None:
    """The full weight mapping: CRITICAL=5, HIGH=3, MEDIUM=1, LOW=0, INFO=0."""
    from divineos.core.briefing_dashboard import _row_audit_findings

    findings = [
        _mock_finding("CRITICAL"),  # +5
        _mock_finding("HIGH"),  # +3
        _mock_finding("MEDIUM"),  # +1
        _mock_finding("LOW"),  # +0
        _mock_finding("INFO"),  # +0
    ]
    with patch("divineos.core.watchmen.store.list_findings", return_value=findings):
        row = _row_audit_findings()
    assert row is not None
    assert row.stale_count == 9, (
        f"Expected stale_count=9 (CRITICAL=5 + HIGH=3 + MEDIUM=1), "
        f"got {row.stale_count}. The weight mapping has changed."
    )


def test_unknown_severity_weighted_zero() -> None:
    """Defensive: unknown severity values contribute 0, don't crash."""
    from divineos.core.briefing_dashboard import _row_audit_findings

    findings = [_mock_finding("UNKNOWN_SEVERITY")]
    with patch("divineos.core.watchmen.store.list_findings", return_value=findings):
        row = _row_audit_findings()
    assert row is not None
    assert row.stale_count == 0


def test_count_independent_of_stale_count() -> None:
    """count is the # unresolved; stale_count is the synthesized urgency."""
    from divineos.core.briefing_dashboard import _row_audit_findings

    findings = [
        _mock_finding("LOW"),
        _mock_finding("LOW"),
        _mock_finding("LOW"),
    ]  # 3 findings, total weight 0
    with patch("divineos.core.watchmen.store.list_findings", return_value=findings):
        row = _row_audit_findings()
    assert row is not None
    assert row.count == 3
    assert row.stale_count == 0
