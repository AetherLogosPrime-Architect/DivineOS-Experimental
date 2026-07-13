"""Regression-pin tests for OS-native hedge_audit.

Andrew 2026-05-14 night: detect-hedge.sh was a 97-line bash hook
with transcript walking, hedge_monitor invocation, and marker-
setting embedded. hedge_audit.run_hedge_audit is the OS-native
replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.hedge_audit import run_hedge_audit


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _user(text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_run_hedge_audit_returns_expected_shape(tmp_path: Path) -> None:
    """LOAD-BEARING: contract is dict with flag_count/threshold/
    marker_set/kinds keys."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("hi"), _assistant_text("long enough text " * 30)],  # > 200 chars
    )
    result = run_hedge_audit(transcript)
    assert "flag_count" in result
    assert "threshold" in result
    assert "marker_set" in result
    assert "kinds" in result
    assert isinstance(result["flag_count"], int)
    assert isinstance(result["threshold"], int)
    assert isinstance(result["marker_set"], bool)
    assert isinstance(result["kinds"], list)


def test_run_hedge_audit_skips_missing_transcript() -> None:
    """Missing transcript fails open — empty result."""
    result = run_hedge_audit("/path/that/does/not/exist.jsonl")
    assert result["flag_count"] == 0
    assert result["marker_set"] is False


def test_run_hedge_audit_skips_short_text(tmp_path: Path) -> None:
    """Text < 200 chars is too short for density-based hedge detection."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("hi"), _assistant_text("short")])
    result = run_hedge_audit(transcript)
    assert result["flag_count"] == 0
    assert result["marker_set"] is False
