"""Tests for scripts/compaction_token_monitor.py.

The full main() loop is impossible to test cleanly because it polls
forever. These tests cover the testable surface:

- transcript-finding logic (find most-recently-modified .jsonl)
- current-state classification (ok / block thresholds — collapsed
  2026-06-19 from the prior ok / warn / block)
- error handling when no transcript is found

The poll loop itself is exercised in the live arming check during PR
review, not in CI.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_script_module():
    """Import scripts/compaction_token_monitor.py as a module."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "compaction_token_monitor.py"
    spec = importlib.util.spec_from_file_location(
        "compaction_token_monitor_under_test", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["compaction_token_monitor_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script_module():
    return _load_script_module()


def _write_transcript(path: Path, tokens: int) -> None:
    """Write a minimal transcript with the given token count."""
    path.write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "x"}],
                    "usage": {
                        "cache_read_input_tokens": tokens,
                        "cache_creation_input_tokens": 0,
                        "input_tokens": 0,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


class TestFindActiveTranscript:
    """The Monitor needs to find the active transcript reliably."""

    def test_finds_most_recently_modified_jsonl(self, script_module, tmp_path, monkeypatch):
        """When multiple .jsonl files exist, picks the freshest."""
        projects_dir = tmp_path / ".claude" / "projects" / "test-proj"
        projects_dir.mkdir(parents=True)

        old_transcript = projects_dir / "old.jsonl"
        new_transcript = projects_dir / "new.jsonl"
        _write_transcript(old_transcript, 100_000)
        _write_transcript(new_transcript, 800_000)
        # Make 'new' newer than 'old' by touching it explicitly.
        import os as _os

        _os.utime(old_transcript, (1_000_000_000, 1_000_000_000))
        _os.utime(new_transcript, (2_000_000_000, 2_000_000_000))

        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        found = script_module._find_active_transcript()
        assert found is not None
        assert found.name == "new.jsonl"

    def test_returns_none_when_projects_dir_missing(self, script_module, tmp_path, monkeypatch):
        """Graceful absence-handling: no projects dir → None, not crash."""
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        # Don't create the projects dir at all.
        assert script_module._find_active_transcript() is None

    def test_returns_none_when_no_jsonl_files(self, script_module, tmp_path, monkeypatch):
        """Empty projects dir → None."""
        projects_dir = tmp_path / ".claude" / "projects"
        projects_dir.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        assert script_module._find_active_transcript() is None


class TestCurrentState:
    """Threshold classification — should match context_governor's
    consolidation_state semantics exactly (ok / block; the prior warn band
    was collapsed away 2026-06-19)."""

    def test_below_hard_returns_ok(self, script_module, tmp_path):
        tx = tmp_path / "tx.jsonl"
        _write_transcript(tx, 500_000)
        state, tokens = script_module._current_state(tx)
        assert state == "ok"
        assert tokens == 500_000

    def test_in_old_warn_band_returns_ok(self, script_module, tmp_path):
        # 940k is below the 950k hard line (lowered 2026-06-28 from 970k).
        tx = tmp_path / "tx.jsonl"
        _write_transcript(tx, 940_000)
        state, _ = script_module._current_state(tx)
        assert state == "ok"

    def test_just_below_hard_returns_ok(self, script_module, tmp_path):
        tx = tmp_path / "tx.jsonl"
        _write_transcript(tx, script_module.HARD_THRESHOLD - 1)
        state, _ = script_module._current_state(tx)
        assert state == "ok"

    def test_at_block_returns_block(self, script_module, tmp_path):
        tx = tmp_path / "tx.jsonl"
        _write_transcript(tx, script_module.HARD_THRESHOLD)
        state, _ = script_module._current_state(tx)
        assert state == "block"

    def test_above_block_returns_block(self, script_module, tmp_path):
        tx = tmp_path / "tx.jsonl"
        _write_transcript(tx, script_module.HARD_THRESHOLD + 10_000)
        state, _ = script_module._current_state(tx)
        assert state == "block"


class TestThresholdCoupling:
    """Aletheia 2026-06-09 coupling-note (find-c0f7f9f9b183): the script's
    threshold must come from context_governor, not be re-literalled. This
    test pins the coupling so a future change can't reintroduce drift by
    copy-pasting a numeric literal into the script."""

    def test_threshold_imported_from_context_governor(self, script_module):
        """The script's HARD must be the SAME OBJECT as the governor's —
        not just equal-valued. Catches the failure-mode where someone
        replaces the import with a hardcoded literal that happens to match
        today's value."""
        from divineos.core import context_governor

        assert script_module.HARD_THRESHOLD is context_governor.HARD_THRESHOLD

    def test_kfmt_derives_display_from_constant(self, script_module):
        """The human-readable threshold string in emitted messages must
        be derived from the constant, not be a hardcoded literal. If the
        constant changes, the message updates with it."""
        assert script_module._kfmt(980_000) == "980k"
        assert script_module._kfmt(900_000) == "900k"
        assert script_module._kfmt(1_000_000) == "1000k"
