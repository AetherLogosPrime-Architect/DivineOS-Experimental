"""Regression-pin tests for sleep_readiness gate."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from divineos.core import sleep_readiness


def test_no_markers_ready(tmp_path: Path) -> None:
    """When no marker files exist, sleep is ready."""
    nonexistent = tmp_path / "nope.json"

    def fake_path() -> Path:
        return nonexistent

    with patch("divineos.core.correction_marker.marker_path", fake_path), patch(
        "divineos.core.hedge_marker.marker_path", fake_path
    ), patch("divineos.core.compass_required_marker.marker_path", fake_path):
        ready, blockers = sleep_readiness.check_sleep_readiness()
    assert ready is True
    assert blockers == []


def test_correction_marker_blocks(tmp_path: Path) -> None:
    """Correction marker present → not ready, message names it."""
    marker = tmp_path / "correction.json"
    marker.write_text("{}")
    other = tmp_path / "nope.json"

    with patch(
        "divineos.core.correction_marker.marker_path", lambda: marker
    ), patch("divineos.core.hedge_marker.marker_path", lambda: other), patch(
        "divineos.core.compass_required_marker.marker_path", lambda: other
    ):
        ready, blockers = sleep_readiness.check_sleep_readiness()
    assert ready is False
    assert len(blockers) == 1
    assert "correction" in blockers[0].lower()


def test_all_three_markers_blocked(tmp_path: Path) -> None:
    """All three markers present → three blockers in message."""
    m1 = tmp_path / "correction.json"
    m2 = tmp_path / "hedge.json"
    m3 = tmp_path / "compass.json"
    for m in (m1, m2, m3):
        m.write_text("{}")

    with patch(
        "divineos.core.correction_marker.marker_path", lambda: m1
    ), patch("divineos.core.hedge_marker.marker_path", lambda: m2), patch(
        "divineos.core.compass_required_marker.marker_path", lambda: m3
    ):
        ready, blockers = sleep_readiness.check_sleep_readiness()
    assert ready is False
    assert len(blockers) == 3


def test_format_block_message_contains_blockers() -> None:
    blockers = ["correction marker present at /tmp/x — fix it"]
    msg = sleep_readiness.format_block_message(blockers)
    assert "BLOCKED" in msg
    assert "correction marker" in msg
    assert "--force" in msg


def test_marker_import_failure_returns_none() -> None:
    """If a marker module can't be imported, the helper returns None (fail-open)."""
    result = sleep_readiness._marker_blocker(
        "fake", "divineos.does.not.exist", "hint"
    )
    assert result is None


def test_guardrail_marker_present() -> None:
    src = Path(sleep_readiness.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
