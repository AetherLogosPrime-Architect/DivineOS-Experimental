"""Regression-pin tests for OS-native theater_audit.

Andrew 2026-05-14 night: detect-theater.sh was a 142-line bash hook
with theater/fabrication monitor invocation, marker-setting, and
findings-log persistence embedded. theater_audit.run_theater_audit
is the OS-native replacement; the hook is now a thin doorman.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.theater_audit import run_theater_audit


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _user(text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_run_theater_audit_returns_expected_shape(tmp_path: Path) -> None:
    """LOAD-BEARING: contract is dict with flags/monitors/persisted/
    marker_set keys."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("hi"), _assistant_text("plain text response")])
    result = run_theater_audit(transcript)
    assert "flags" in result
    assert "monitors" in result
    assert "persisted" in result
    assert "marker_set" in result
    assert isinstance(result["flags"], list)
    assert isinstance(result["monitors"], list)
    assert isinstance(result["persisted"], bool)
    assert isinstance(result["marker_set"], bool)


def test_run_theater_audit_skips_missing_transcript() -> None:
    """Missing transcript fails open — returns empty result."""
    result = run_theater_audit("/path/that/does/not/exist.jsonl")
    assert result["monitors"] == []
    assert result["persisted"] is False
    assert result["marker_set"] is False


def test_run_theater_audit_empty_transcript(tmp_path: Path) -> None:
    """Empty assistant text → empty monitors, no marker, no persist."""
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("", encoding="utf-8")
    result = run_theater_audit(transcript)
    assert result["monitors"] == []
    assert result["persisted"] is False
    assert result["marker_set"] is False


def test_run_theater_audit_no_assistant_records(tmp_path: Path) -> None:
    """Transcript with no assistant records returns empty result."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("only user text")])
    result = run_theater_audit(transcript)
    assert result["monitors"] == []
    assert result["persisted"] is False
