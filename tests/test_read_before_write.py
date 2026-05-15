"""Regression-pin tests for read_before_write gate.

Andrew named the gate quest 2026-05-14: CLAUDE.md Hard Rule #1
(read-before-write) was a rule without a gate. This gate makes it
structural. Catches fabrication-from-register at its pre-emission
point — the Edit/Write tool call against an unread file.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from divineos.core import read_before_write as rbw


@pytest.fixture(autouse=True)
def isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test gets a fresh state directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # Force the module to recompute home each call.
    monkeypatch.setattr(rbw.Path, "home", classmethod(lambda cls: tmp_path))


def test_write_to_existing_unread_file_is_denied(tmp_path: Path) -> None:
    """LOAD-BEARING: editing an existing unread file fires the gate."""
    target = tmp_path / "existing.py"
    target.write_text("# pre-existing content")
    msg = rbw.gate_check("Edit", {"file_path": str(target)})
    assert msg is not None
    assert "read-before-write" in msg.lower()
    assert str(target) in msg


def test_write_to_nonexistent_file_allowed(tmp_path: Path) -> None:
    """New file creation is allowed — no prior content to fabricate about."""
    target = tmp_path / "new_file.py"
    assert not target.exists()
    msg = rbw.gate_check("Write", {"file_path": str(target)})
    assert msg is None


def test_read_then_write_allowed(tmp_path: Path) -> None:
    """The intended-use loop: Read records, subsequent Edit passes."""
    target = tmp_path / "existing.py"
    target.write_text("# content")
    # Read first.
    rbw.gate_check("Read", {"file_path": str(target)})
    # Edit now allowed.
    msg = rbw.gate_check("Edit", {"file_path": str(target)})
    assert msg is None


def test_exploration_path_exempt(tmp_path: Path) -> None:
    """Exploration paths bypass the gate (expressive-surface calibration)."""
    explor_dir = tmp_path / "exploration"
    explor_dir.mkdir()
    target = explor_dir / "musing.md"
    target.write_text("# free-write")
    msg = rbw.gate_check("Edit", {"file_path": str(target)})
    assert msg is None


def test_non_write_tools_pass(tmp_path: Path) -> None:
    """Bash, Grep, etc. are not in the write-tool set — pass through."""
    target = tmp_path / "existing.py"
    target.write_text("x = 1")
    assert rbw.gate_check("Bash", {"command": "cat existing.py"}) is None
    assert rbw.gate_check("Grep", {"pattern": "x"}) is None


def test_transcript_walk_records_reads(tmp_path: Path) -> None:
    """When the harness doesn't fire PreToolUse on Read, transcript
    walking is the canonical fallback."""
    target = tmp_path / "from_transcript.py"
    target.write_text("# content")
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": str(target)},
                        }
                    ]
                },
            }
        )
        + "\n"
    )
    # No record_read called directly; only the transcript shows the Read.
    msg = rbw.gate_check(
        "Edit",
        {"file_path": str(target)},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_empty_file_path_passes(tmp_path: Path) -> None:
    """Defensive: missing file_path returns None, not a crash."""
    assert rbw.gate_check("Edit", {}) is None
    assert rbw.gate_check("Edit", {"file_path": ""}) is None


def test_guardrail_marker_present() -> None:
    """The module is on the guardrail list; the marker must travel
    with it across refactors (Aletheia Finding 48 class-fix)."""
    src = Path(rbw.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
