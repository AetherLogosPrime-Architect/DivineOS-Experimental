"""Regression-pin tests for the audit-response CLI entrypoint.

Channel-shape: the audit pipeline now has a Python entrypoint that
doesn't depend on the .sh hook firing. These tests verify (1) the
CLI command is registered, and (2) the underlying run_audit
function is callable with the same shape the CLI would pass to it.
"""

from __future__ import annotations

import json
from pathlib import Path


def _write_transcript(path: Path, last_assistant: str) -> None:
    records = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": last_assistant}]}},
    ]
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_audit_response_command_is_registered() -> None:
    """LOAD-BEARING: the CLI command exists and is wired into the divineos group.

    If this fails, someone removed the register() call or the import — the
    Python entrypoint for the audit pipeline has disappeared and the
    pipeline is once again .sh-hook-only.
    """
    from divineos.cli import audit_response_commands, cli  # noqa: F401

    assert "audit-response" in cli.commands, (
        "audit-response command not registered on the divineos CLI group. "
        "Python entrypoint to the audit pipeline is missing — pipeline "
        "depends on .sh hooks firing, replicating the SUSPECT shape "
        "this CLI was built to close."
    )


def test_audit_response_wraps_run_audit() -> None:
    """The CLI module references the same run_audit the .sh hook uses."""
    import inspect

    from divineos.cli import audit_response_commands

    src = inspect.getsource(audit_response_commands)
    assert "from divineos.core.operating_loop_audit import run_audit" in src, (
        "audit-response CLI no longer imports run_audit — decoupled from "
        "the audit pipeline it was meant to entry-point."
    )


def test_run_audit_callable_with_cli_shape(tmp_path: Path) -> None:
    """Underlying run_audit accepts the same args the CLI passes."""
    from divineos.core.operating_loop_audit import run_audit

    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, "ok" * 200)
    result = run_audit(str(transcript), write=False)
    assert "total_findings" in result
    assert "findings_log" in result
    assert "persisted" in result


def test_run_audit_handles_missing_transcript() -> None:
    """Fail-open: missing transcript returns empty result, doesn't crash."""
    from divineos.core.operating_loop_audit import run_audit

    result = run_audit("/does/not/exist.jsonl", write=False)
    assert result["total_findings"] == 0
    assert result["persisted"] is False
