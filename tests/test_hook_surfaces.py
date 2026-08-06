"""Tests for the migrated surfaces.

The must_read surface is the first hook moved off bash into the OS. Its
behaviour must be identical to `.claude/hooks/must-read-gate.sh` — the
migration moves WHERE the decision lives, not WHAT it decides.

The load-bearing test is `test_read_is_never_blocked`. The must-read gate's
own remedy is a Read; a gate that can block its own remedy is a locked box,
and this substrate has a task number for that (#98). It was true in the bash
version and it has to survive the move.
"""

from __future__ import annotations

import pytest

from divineos.core import hook_router as hr
from divineos.core import hook_surfaces as hs


@pytest.fixture(autouse=True)
def _clean():
    hr.clear()
    yield
    hr.clear()


class TestSubstantiveDispatch:
    def test_read_is_never_blocked(self):
        """The remedy must stay reachable. A gate that blocks its own unlock
        is a locked box (task #98)."""
        out = hs.must_read_surface({"tool_name": "Read", "tool_input": {}})
        assert out is None or out.refused is False

    @pytest.mark.parametrize("tool", ["Glob", "Grep", "NotebookRead", "TodoWrite", "Task"])
    def test_read_shaped_tools_pass(self, tool):
        out = hs.must_read_surface({"tool_name": tool, "tool_input": {}})
        assert out is None

    @pytest.mark.parametrize("tool", ["WebFetch", "SomeUnknownTool", ""])
    def test_non_substantive_tools_pass(self, tool):
        """Only substrate-changing tools are gated."""
        out = hs.must_read_surface({"tool_name": tool, "tool_input": {}})
        assert out is None

    def test_substantive_tool_set_is_explicit(self):
        """The judgment that used to live in bash, now testable."""
        assert hs._SUBSTANTIVE_TOOLS == {
            "Bash",
            "PowerShell",
            "Edit",
            "Write",
            "NotebookEdit",
        }
        # Read must never appear here.
        assert "Read" not in hs._SUBSTANTIVE_TOOLS

    def test_unreadable_index_reports_error_not_refusal(self, monkeypatch):
        """Could-not-look must not render as could-not-proceed, and must not
        block on a fact not in evidence."""
        monkeypatch.setattr(
            "divineos.core.must_read.pending", lambda *a, **k: (None, "disk on fire")
        )
        out = hs.must_read_surface({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert out is not None
        assert out.error is not None and out.refused is False

    def test_nothing_pending_is_silent(self, monkeypatch):
        monkeypatch.setattr("divineos.core.must_read.pending", lambda *a, **k: ([], None))
        assert hs.must_read_surface({"tool_name": "Bash", "tool_input": {}}) is None

    def test_pending_refuses_with_the_block_text(self, monkeypatch):
        from divineos.core.must_read import PendingRead

        fake = PendingRead(key="k", path=__import__("pathlib").Path("x.md"), reason="r", armed_at=0)
        monkeypatch.setattr("divineos.core.must_read.pending", lambda *a, **k: ([fake], None))
        out = hs.must_read_surface({"tool_name": "Bash", "tool_input": {}})
        assert out is not None and out.refused is True
        assert "MUST-READ PENDING" in out.reason


class TestInstall:
    def test_install_registers_on_pretooluse(self):
        hs.install()
        assert "must_read" in hr.registered("PreToolUse")

    def test_install_is_idempotent(self):
        """Each doorbell calls install(); calling twice must not raise."""
        hs.install()
        hs.install()
        assert hr.registered("PreToolUse").count("must_read") == 1
