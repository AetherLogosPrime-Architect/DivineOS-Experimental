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
            # 'divineos learn' was moved to bypass on 2026-04-23 when the
            # correction-detection gate was shipped — the gate instructs the
            # agent to run `divineos learn` to clear the marker, so learn
            # itself must not be blocked (catch-22 discovered live).
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

    def test_learn_is_bypass_to_break_correction_catch22(self):
        """Regression guard: `divineos learn` must be bypass so the
        correction-detection gate's remedy isn't itself blocked."""
        assert pre_hook._is_bypass_command("divineos learn 'x'") is True


class TestExplorationWriteExemption:
    """Path-exemption for exploration/ writes per 2026-04-27 calibration
    directive. Gates 1.46 (theater marker) and 1.47 (compass-required
    cascade) are calibrated for operator-facing claims; applied to
    exploration-path writes they produce a cascade-loop documented in
    exploration/37_reading_past_me.md.

    The exemption is from path-blocks-tool-use, not from finding-
    recording. Marker still gets set by Stop hook (forensic preserved).
    """

    @pytest.mark.parametrize(
        "tool_name,file_path",
        [
            ("Write", "exploration/37_reading_past_me.md"),
            ("Write", "/repo/exploration/foo.md"),
            ("Write", r"C:\repo\exploration\foo.md"),
            ("Edit", "exploration/30_synthesis.md"),
            ("MultiEdit", "/abs/path/exploration/sub/file.md"),
            ("NotebookEdit", "exploration/notes.ipynb"),
        ],
    )
    def test_exploration_paths_exempt(self, tool_name: str, file_path: str):
        input_data = {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
        }
        assert pre_hook._is_exploration_write(input_data) is True

    @pytest.mark.parametrize(
        "tool_name,file_path",
        [
            # Wrong tool — Bash never goes through path-write
            ("Bash", "exploration/foo.md"),
            # Other paths are NOT exempt — operator-facing
            ("Write", "src/divineos/core/something.py"),
            ("Write", "README.md"),
            ("Write", "tests/test_foo.py"),
            # Empty path
            ("Write", ""),
            # Path that contains "exploration" but not as a directory
            # segment
            ("Write", "exploration_summary.md"),  # not under exploration/
        ],
    )
    def test_non_exploration_paths_not_exempt(self, tool_name: str, file_path: str):
        input_data = {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
        }
        assert pre_hook._is_exploration_write(input_data) is False

    def test_missing_input_data_safe(self):
        assert pre_hook._is_exploration_write({}) is False

    def test_malformed_input_data_safe(self):
        # tool_input is None instead of dict
        assert pre_hook._is_exploration_write({"tool_name": "Write", "tool_input": None}) is False

    def test_exemption_segments_immutable(self):
        """The exemption tuple should be a tuple, not a list — prevents
        accidental in-place modification across imports.
        """
        assert isinstance(pre_hook._THEATER_EXEMPT_PATH_SEGMENTS, tuple)


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


class TestLessonInterruptIntegration:
    """Lesson-interrupt check was folded into the consolidated checkpoint
    module in P3 (previously its own shell hook). Verify it only runs for
    code-modifying tools."""

    def test_lesson_interrupt_skipped_for_bash(self):
        # Non-code-modifying tool → interrupt check skipped, empty string
        result = post_hook._check_lesson_interrupt("Bash", {"command": "ls"})
        assert result == ""

    def test_lesson_interrupt_skipped_for_read(self):
        result = post_hook._check_lesson_interrupt("Read", {"file_path": "x.py"})
        assert result == ""

    def test_lesson_interrupt_runs_for_edit(self):
        # Function itself should run (return string or empty, not error)
        result = post_hook._check_lesson_interrupt("Edit", {"file_path": "x.py"})
        assert isinstance(result, str)

    def test_lesson_interrupt_runs_for_notebook_edit(self):
        result = post_hook._check_lesson_interrupt("NotebookEdit", {})
        assert isinstance(result, str)


class TestAnticipationIntegration:
    """Pattern-anticipation was folded into the consolidated checkpoint
    module in P3 (previously its own shell hook). Verify throttling and
    gating behavior."""

    def test_anticipation_skipped_for_bash(self):
        state: dict = {}
        result = post_hook._run_anticipation("Bash", "foo.py", state)
        assert result == ""

    def test_anticipation_skipped_for_empty_file_path(self):
        state: dict = {}
        result = post_hook._run_anticipation("Edit", "", state)
        assert result == ""

    def test_anticipation_throttled_non_multiple(self):
        """Counter at 1, 2, 3, 4 — none trigger. Counter at 5 — triggers."""
        # Fresh state
        state: dict = {}
        # First 4 edits should not trigger (counter advances but no fire)
        for _ in range(4):
            post_hook._run_anticipation("Edit", "foo.py", state)
        # Counter should be at 4 now, next call bumps to 5 and fires
        assert state[post_hook._ANTICIPATION_COUNTER_KEY] == 4

    def test_anticipation_counter_persists_in_state(self):
        """Counter should land in the main state dict so it's persisted
        by _save_state alongside the rest of the checkpoint state."""
        state: dict = {"edits": 0, "tool_calls": 0}
        post_hook._run_anticipation("Edit", "foo.py", state)
        assert post_hook._ANTICIPATION_COUNTER_KEY in state
        assert state[post_hook._ANTICIPATION_COUNTER_KEY] == 1
