"""Tests for the consolidated PreToolUse and PostToolUse hook modules.

Locked invariants:

1. Bypass commands skip all gates (divineos briefing, git, pytest, etc.)
2. Non-bypass commands run through gates.
3. Gate-deny decisions emit a JSON object with the Claude Code hook shape.
4. All-gates-pass emits empty stdout.
5. PostToolUse checkpoint loads and saves state idempotently.
6. PostToolUse counters increment correctly per tool type.
"""

from __future__ import annotations

import json
import os
from io import StringIO

import pytest

from divineos.hooks import post_tool_use_checkpoint as post_hook
from divineos.hooks import pre_tool_use_gate as pre_hook


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Redirect ~/.divineos to a tmp dir so hooks don't touch real state."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from pathlib import Path as _P

    original_home = _P.home
    monkeypatch.setattr(_P, "home", classmethod(lambda cls: tmp_path))
    # Also patch os.path.expanduser since the hook modules use it
    original_expanduser = os.path.expanduser
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda p: str(tmp_path) + p[1:] if p.startswith("~") else original_expanduser(p),
    )
    yield
    monkeypatch.setattr(_P, "home", original_home)


class TestPreToolUseBypassCommands:
    """Bypass commands should skip all gates regardless of engagement state."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "divineos briefing",
            "divineos ask 'something'",
            "divineos recall",
            "divineos hud --brief",
            "divineos feel -v 0.5",
            "divineos emit SESSION_END",
            "divineos goal add 'x'",
            "divineos context",
            "divineos preflight",
            "divineos audit list",
            "divineos prereg list",
            "git status",
            "git diff HEAD",
            "pytest tests/",
            "python -m pytest",
            "ls src/",
            "cat file.py",
            "pip install foo",
            "ruff check",
        ],
    )
    def test_bypass_commands_return_true(self, cmd: str):
        assert pre_hook._is_bypass_command(cmd) is True

    @pytest.mark.parametrize(
        "cmd",
        [
            "divineos learn 'x'",
            "divineos forget abc",
            "divineos ingest file.md",
            "rm -rf /",
            "curl http://evil",
            "node script.js",
            "",
            "bash -c 'anything'",
        ],
    )
    def test_non_bypass_commands_return_false(self, cmd: str):
        assert pre_hook._is_bypass_command(cmd) is False


class TestPreToolUseEntryPoint:
    """Integration-style tests of the main() entry point."""

    def test_bypass_command_produces_empty_output(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.stdin", StringIO(json.dumps({"tool_input": {"command": "divineos briefing"}}))
        )
        pre_hook.main()
        out = capsys.readouterr().out
        assert out == ""

    def test_empty_stdin_graceful(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", StringIO(""))
        rc = pre_hook.main()
        # Should not crash; returns 0
        assert rc == 0

    def test_malformed_json_graceful(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", StringIO("not valid json {"))
        rc = pre_hook.main()
        assert rc == 0


class TestDenyShape:
    """Deny decisions must match the Claude Code hook response format."""

    def test_make_deny_shape(self):
        d = pre_hook._make_deny("test reason")
        assert "hookSpecificOutput" in d
        hso = d["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "deny"
        assert hso["permissionDecisionReason"] == "test reason"


class TestPostToolUseState:
    """The checkpoint module loads / saves state correctly."""

    def test_load_state_defaults_when_missing(self, tmp_path):
        # _isolated_home has redirected the state path already
        state = post_hook._load_state()
        assert state["edits"] == 0
        assert state["tool_calls"] == 0
        assert state["checkpoints_run"] == 0

    def test_save_then_load_roundtrip(self):
        state = {"edits": 5, "tool_calls": 12, "last_checkpoint": 1000.0, "checkpoints_run": 2}
        post_hook._save_state(state)
        loaded = post_hook._load_state()
        assert loaded["edits"] == 5
        assert loaded["tool_calls"] == 12
        assert loaded["checkpoints_run"] == 2

    def test_malformed_state_file_falls_back_to_defaults(self):
        path = post_hook._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{", encoding="utf-8")
        state = post_hook._load_state()
        assert state["edits"] == 0
        assert state["tool_calls"] == 0


class TestPostToolUseCounters:
    """Tool-call counter should increment for any tool; edit counter only for Edit/Write."""

    def test_edit_increments_both_counters(self, monkeypatch):
        state = {"edits": 0, "tool_calls": 0, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)

        monkeypatch.setattr(
            "sys.stdin",
            StringIO(
                json.dumps(
                    {
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "foo.py"},
                    }
                )
            ),
        )
        post_hook.main()

        state = post_hook._load_state()
        assert state["tool_calls"] == 1
        assert state["edits"] == 1

    def test_bash_increments_only_tool_calls(self, monkeypatch):
        state = {"edits": 0, "tool_calls": 0, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)

        monkeypatch.setattr(
            "sys.stdin",
            StringIO(
                json.dumps(
                    {
                        "tool_name": "Bash",
                        "tool_input": {"command": "ls"},
                    }
                )
            ),
        )
        post_hook.main()

        state = post_hook._load_state()
        assert state["tool_calls"] == 1
        assert state["edits"] == 0

    def test_empty_input_does_not_crash(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", StringIO(""))
        rc = post_hook.main()
        assert rc == 0


class TestPostToolUseContextWarnings:
    """Warnings / nudges should fire at configured thresholds."""

    def test_no_warning_below_threshold(self, monkeypatch, capsys):
        state = {"edits": 0, "tool_calls": 50, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})),
        )
        post_hook.main()
        out = capsys.readouterr().out
        # No warnings below threshold — output should be empty
        assert out == ""

    def test_warning_at_context_threshold(self, monkeypatch, capsys):
        # Bumping from 99 to 100 with this call
        state = {"edits": 0, "tool_calls": 99, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})),
        )
        post_hook.main()
        out = capsys.readouterr().out
        # Should emit additionalContext with a warning
        assert out.strip(), "Expected a warning at context threshold"
        payload = json.loads(out)
        assert "additionalContext" in payload
        assert "Context monitor" in payload["additionalContext"]
