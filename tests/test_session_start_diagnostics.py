"""Tests for session_start_diagnostics — briefing surface for hook log.

Falsifiability:
  - Empty log → empty block (nothing to surface, nothing to say).
  - All injected_full → empty block (healthy, stay silent).
  - Any nudge/empty/no_cli → non-empty block naming the outcome.
  - Block format includes outcome counts in deterministic order.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from divineos.core import session_start_diagnostics


def _write_entries(tmp_path, entries):
    log = tmp_path / "session_start_log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    return log


class TestSilence:
    def test_no_log_returns_empty(self, tmp_path) -> None:
        missing = tmp_path / "does_not_exist.jsonl"
        with patch.object(session_start_diagnostics, "_LOG_PATH", missing):
            assert session_start_diagnostics.format_for_briefing() == ""

    def test_all_full_injections_returns_empty(self, tmp_path) -> None:
        log = _write_entries(
            tmp_path,
            [{"outcome": "injected_full", "payload_bytes": 12000} for _ in range(5)],
        )
        with patch.object(session_start_diagnostics, "_LOG_PATH", log):
            assert session_start_diagnostics.format_for_briefing() == ""


class TestSurfacing:
    def test_nudge_fires_the_block(self, tmp_path) -> None:
        log = _write_entries(
            tmp_path,
            [
                {"outcome": "injected_full", "payload_bytes": 12000},
                {"outcome": "injected_full", "payload_bytes": 12500},
                {"outcome": "injected_nudge", "payload_bytes": 35000},
            ],
        )
        with patch.object(session_start_diagnostics, "_LOG_PATH", log):
            out = session_start_diagnostics.format_for_briefing()
            assert out
            assert "session-start log" in out
            assert "injected_nudge" in out
            assert "injected_full" in out

    def test_empty_briefing_fires_the_block(self, tmp_path) -> None:
        log = _write_entries(tmp_path, [{"outcome": "empty_briefing", "payload_bytes": 0}])
        with patch.object(session_start_diagnostics, "_LOG_PATH", log):
            out = session_start_diagnostics.format_for_briefing()
            assert out
            assert "empty_briefing" in out

    def test_no_cli_fires_the_block(self, tmp_path) -> None:
        log = _write_entries(tmp_path, [{"outcome": "no_cli", "payload_bytes": 0}])
        with patch.object(session_start_diagnostics, "_LOG_PATH", log):
            out = session_start_diagnostics.format_for_briefing()
            assert out
            assert "no_cli" in out

    def test_malformed_lines_are_skipped(self, tmp_path) -> None:
        log = tmp_path / "log.jsonl"
        log.write_text(
            'not json\n{"outcome": "injected_nudge"}\n{incomplete\n',
            encoding="utf-8",
        )
        with patch.object(session_start_diagnostics, "_LOG_PATH", log):
            out = session_start_diagnostics.format_for_briefing()
            assert "injected_nudge" in out
