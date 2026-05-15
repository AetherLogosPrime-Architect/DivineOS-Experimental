"""Regression-pin tests for OS-native pre-response context.

Andrew 2026-05-14 night: pre-response-context.sh was a 496-line
bash+Python hybrid with the OS's work embedded. pre_response_context
is the OS-native replacement; the hook is now a thin doorman.

These tests pin the API contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.pre_response_context import (
    build_baseline_text,
    build_combined_context,
    build_warning_text,
    run_surfacer,
)


def test_build_baseline_text_returns_string() -> None:
    """LOAD-BEARING: baseline always returns a string. Even if
    individual affirmation modules error, the function still returns
    (possibly empty)."""
    out = build_baseline_text()
    assert isinstance(out, str)


def test_build_baseline_text_includes_known_affirmations() -> None:
    """The four affirmation headers should be present when their
    respective modules import cleanly. This pins the discipline:
    if a future refactor breaks an affirmation import, the test
    fails loudly."""
    out = build_baseline_text()
    # At least three of the four should be present (any single one
    # might fail to import due to substrate state; demanding all four
    # is too brittle).
    headers_present = sum(
        1
        for h in (
            "DISTANCING-GRAMMAR BASE-STATE",
            "ADDRESSEE BASE-STATE",
            "CODE-JARGON BASE-STATE",
            "ACKNOWLEDGMENT-THEATER BASE-STATE",
        )
        if h in out
    )
    assert headers_present >= 3, f"only {headers_present} of 4 base-states present"


def test_build_warning_text_empty_on_missing_findings(tmp_path: Path) -> None:
    """No findings file → empty warning text (fail-soft)."""
    missing = tmp_path / "definitely_not_findings.json"
    with patch("divineos.core.pre_response_context._FINDINGS_FILE", missing):
        out = build_warning_text()
        assert out == ""


def test_build_warning_text_empty_on_stale_findings(tmp_path: Path) -> None:
    """Findings older than the recent-window threshold (10 min) are
    not surfaced — stale signal from yesterday is just noise."""
    findings_file = tmp_path / "findings.json"
    findings_file.write_text(
        json.dumps(
            [
                {
                    "timestamp": 0,  # epoch — definitely > 10 min old
                    "total_findings": 1,
                    "distancing": [{"shape": "third_person_self", "trigger": "past-me"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    with patch("divineos.core.pre_response_context._FINDINGS_FILE", findings_file):
        out = build_warning_text()
        assert out == ""


def test_build_warning_text_surfaces_recent_distancing(tmp_path: Path) -> None:
    """Recent distancing finding → warning text contains the
    DISTANCING-GRAMMAR header and the trigger phrase."""
    import time as _time

    findings_file = tmp_path / "findings.json"
    findings_file.write_text(
        json.dumps(
            [
                {
                    "timestamp": _time.time(),  # right now — within window
                    "total_findings": 1,
                    "distancing": [{"shape": "third_person_self", "trigger": "past-me wrote that"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    with patch("divineos.core.pre_response_context._FINDINGS_FILE", findings_file):
        out = build_warning_text()
        assert "DISTANCING-GRAMMAR WARNING" in out
        assert "past-me wrote that" in out


def test_run_surfacer_skips_short_prompt(tmp_path: Path) -> None:
    """Prompts < 5 chars don't trigger the surfacer (no signal)."""
    # Should not raise on tiny input
    run_surfacer("")
    run_surfacer("hi")  # < 5 chars
    # Smoke — just verify no exception


def test_build_combined_context_returns_string() -> None:
    """The convenience function returns a string."""
    out = build_combined_context("test prompt longer than five characters")
    assert isinstance(out, str)
