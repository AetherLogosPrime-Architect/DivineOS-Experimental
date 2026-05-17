"""Regression-pin tests for the OS-native post-response audit orchestrator.

Andrew 2026-05-14 night: hooks should point to the OS, not replace
it. post-response-audit.sh was a 677-line bash+Python hybrid with
the OS's work embedded inside. operating_loop_audit.run_audit() is
the OS-native replacement; the hook is now a thin doorman.

These tests pin the contract so a future refactor can't silently
revert the architecture.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.operating_loop_audit import run_audit


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _user(text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_run_audit_returns_expected_shape(tmp_path: Path) -> None:
    """LOAD-BEARING: contract of run_audit is dict with the three
    keys. Test pins the shape so callers (hooks, alternative
    implementations) can rely on it."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("hi"),
            _assistant_text("ok, working on it. " * 20),  # long enough to bypass min-text check
        ],
    )
    result = run_audit(transcript, write=False)
    assert "findings_log" in result
    assert "total_findings" in result
    assert "persisted" in result
    assert isinstance(result["findings_log"], dict)
    assert isinstance(result["total_findings"], int)
    assert isinstance(result["persisted"], bool)


def test_run_audit_skips_short_text(tmp_path: Path) -> None:
    """Texts < 50 chars are skipped — not enough signal. Returns
    empty findings, no persistence."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("hi"),
            _assistant_text("short."),  # < 50 chars
        ],
    )
    result = run_audit(transcript, write=False)
    assert result["total_findings"] == 0
    assert result["persisted"] is False


def test_run_audit_skips_missing_transcript() -> None:
    """Missing transcript file fails open — returns empty result."""
    result = run_audit("/path/that/definitely/does/not/exist.jsonl", write=False)
    assert result["total_findings"] == 0
    assert result["persisted"] is False


def test_run_audit_write_false_does_not_persist(tmp_path: Path) -> None:
    """LOAD-BEARING: write=False guarantees no disk side effects.
    Used by test harnesses and preview runs that must not touch
    persistent state."""
    transcript = tmp_path / "t.jsonl"
    findings_file = tmp_path / "findings.json"
    _write_jsonl(
        transcript,
        [
            _user("hi"),
            _assistant_text("substantial response text " * 20),
        ],
    )
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(findings_file.parent)}):
        result = run_audit(transcript, write=False)
        assert result["persisted"] is False
        assert not findings_file.exists()


def test_run_audit_findings_log_has_all_detector_keys(tmp_path: Path) -> None:
    """LOAD-BEARING: findings_log always has every known detector key
    present (possibly empty). Distinguishes 'detector ran and found
    nothing' from 'detector key missing entirely'. Briefing surface
    and downstream readers depend on key consistency."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("hi"), _assistant_text("text " * 30)])
    result = run_audit(transcript, write=False)
    expected_keys = {
        "register",
        "spiral",
        "substitution",
        "distancing",
        "jargon_dump",
        "sycophancy",
        "residency",
        "acknowledgment_theater",
        "code_jargon",
        "linguistic_drift",
        "hedge_evidence",
        "care_dismissal",
        "harm_acknowledgment",
    }
    for key in expected_keys:
        assert key in result["findings_log"], f"Missing detector key: {key}"
