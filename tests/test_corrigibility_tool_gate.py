"""Tests for the corrigibility tool-gate.

Per prereg-2b8b26d9b2c4. Behavioral tests for every deny path AND every
allow path under each operating mode. The Perplexity audit 2026-06-25
specifically called out that the existing pre_tool_use_gate.py has only
a file-read pin and no behavioral coverage — this module ships with
real coverage from the start.

Mode is controlled by monkeypatching `get_mode` in the module under
test rather than touching the real mode-file. The real `set_mode` API
goes through the ledger and we do not want test side-effects there.
"""

from __future__ import annotations

import pytest

from divineos.core import corrigibility_tool_gate
from divineos.core.corrigibility import OperatingMode
from divineos.core.corrigibility_tool_gate import (
    check_tool_under_corrigibility,
    is_recovery_command,
)


def _force_mode(monkeypatch, mode: OperatingMode) -> None:
    monkeypatch.setattr(corrigibility_tool_gate, "get_mode", lambda: mode)


# --- is_recovery_command pure-pattern tests ---


@pytest.mark.parametrize(
    "command",
    [
        "divineos mode",
        "divineos mode unstop",
        "divineos status",
        "divineos hud",
        "divineos hud --brief",
        "divineos briefing",
        "divineos verify",
        "ls",
        "ls -la /tmp",
        "cat README.md",
        "head -5 file.txt",
        "tail -100 log",
        "pwd",
        "echo hello",
        "git status",
        "git log --oneline",
        "git diff HEAD",
        "git branch",
        "git show HEAD",
        "gh pr list",
        "gh pr view 123",
        "gh pr checks 100",
        "  ls  ",
    ],
)
def test_recovery_commands_recognized(command: str) -> None:
    assert is_recovery_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "",
        "rm file.txt",
        "git commit -m foo",
        "git reset --hard HEAD",
        "python script.py",
        "pip install requests",
        "cat file.txt | grep secret",
        "cat file > out.txt",
        "divineos extract",
        "divineos learn 'something'",
        "gh pr merge 123 --squash",
    ],
)
def test_non_recovery_commands_rejected(command: str) -> None:
    assert not is_recovery_command(command)


# --- Aletheia audit 2026-06-26: push-to-origin polarity ---
# Push-to-origin (non-main, non-force) is submit-for-audit, NOT
# world-commitment. Allowed under EMERGENCY_STOP so the agent can
# route fixes to the place reviewers can see them. The world-commitment
# (merge-to-main) is gated separately by branch protection.


@pytest.mark.parametrize(
    "command",
    [
        "git push origin feature/foo",
        "git push origin fix-corrigibility-polarity",
        "git push -u origin some-branch",
        "git push origin bugfix.v2",
        "git push origin chore_123",
        "  git push origin my-branch  ",  # whitespace tolerated
    ],
)
def test_safe_push_to_origin_allowed_for_audit(command: str) -> None:
    """Per Aletheia 2026-06-26: push-to-origin is submit-for-review,
    not world-commitment. Allow so fixes can reach the auditor under stop."""
    assert is_recovery_command(command), f"{command!r} should be allowed (submit-for-audit)"


@pytest.mark.parametrize(
    "command",
    [
        # Push to main/master in any form (world-commitment)
        "git push origin main",
        "git push origin master",
        "git push -u origin main",
        "git push origin :main",  # colon-form delete of main
        "git push origin HEAD:main",
        # Force in any flavor (history rewrite)
        "git push --force origin foo",
        "git push --force-with-lease origin foo",
        "git push -f origin foo",
        "git push origin -f foo",
        # Mirror (replaces all refs)
        "git push --mirror origin",
        # Branch deletion via push
        "git push --delete origin some-branch",
        "git push origin :some-branch",  # colon-form delete of any branch
        # Forced refspec via +
        "git push origin +foo:bar",
    ],
)
def test_dangerous_push_variants_still_denied(command: str) -> None:
    """Deny-overrides take precedence over the safe-push allow pattern.
    World-commitment, history-rewrite, and destructive variants are never
    "submit for review" — they're the actions EMERGENCY_STOP must prevent."""
    assert not is_recovery_command(command), f"{command!r} should be denied"


# --- check_tool_under_corrigibility — NORMAL mode (allow everything) ---


def test_normal_mode_allows_bash(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.NORMAL)
    assert check_tool_under_corrigibility("Bash", {"command": "rm -rf /tmp/foo"}).allow


def test_normal_mode_allows_edit(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.NORMAL)
    assert check_tool_under_corrigibility("Edit", {"file_path": "/x"}).allow


def test_normal_mode_allows_write(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.NORMAL)
    assert check_tool_under_corrigibility("Write", {"file_path": "/x"}).allow


# --- check_tool_under_corrigibility — EMERGENCY_STOP mode ---


def test_emergency_stop_denies_edit(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    decision = check_tool_under_corrigibility("Edit", {"file_path": "/x"})
    assert not decision.allow
    assert "EMERGENCY_STOP" in decision.reason


def test_emergency_stop_denies_write(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    assert not check_tool_under_corrigibility("Write", {"file_path": "/x"}).allow


def test_emergency_stop_denies_notebookedit(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    assert not check_tool_under_corrigibility("NotebookEdit", {"notebook_path": "/x"}).allow


def test_emergency_stop_denies_bash_for_mutating_command(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    decision = check_tool_under_corrigibility("Bash", {"command": "rm -rf /tmp/foo"})
    assert not decision.allow
    assert "Only read-only" in decision.reason


def test_emergency_stop_allows_bash_for_recovery_command(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    assert check_tool_under_corrigibility("Bash", {"command": "divineos mode unstop"}).allow


def test_emergency_stop_allows_bash_for_read_only_inspection(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    for cmd in ("ls", "git status", "divineos hud"):
        assert check_tool_under_corrigibility("Bash", {"command": cmd}).allow, (
            f"{cmd} should be allowed under stop"
        )


def test_emergency_stop_allows_read_only_tools(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    for tool in ("Read", "Grep", "Glob"):
        assert check_tool_under_corrigibility(tool, {}).allow, (
            f"{tool} should be allowed under stop"
        )


def test_emergency_stop_handles_missing_command_input(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    assert not check_tool_under_corrigibility("Bash", {}).allow


def test_emergency_stop_handles_none_input(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    assert not check_tool_under_corrigibility("Bash", None).allow


def test_emergency_stop_handles_non_string_command(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.EMERGENCY_STOP)
    assert not check_tool_under_corrigibility("Bash", {"command": 123}).allow


# --- RESTRICTED / DIAGNOSTIC modes: handled at CLI layer, not here ---


def test_restricted_mode_allows_tools(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.RESTRICTED)
    assert check_tool_under_corrigibility("Bash", {"command": "rm file"}).allow
    assert check_tool_under_corrigibility("Edit", {}).allow


def test_diagnostic_mode_allows_tools(monkeypatch) -> None:
    _force_mode(monkeypatch, OperatingMode.DIAGNOSTIC)
    assert check_tool_under_corrigibility("Bash", {"command": "rm file"}).allow
    assert check_tool_under_corrigibility("Edit", {}).allow


# --- Fail-closed under uncertainty (H1 audit finding does NOT apply) ---


def test_mode_read_failure_fails_closed(monkeypatch) -> None:
    """If get_mode() raises, deny the tool. Safety-critical path —
    H1's fail-open default does not apply here."""

    def _broken_get_mode():
        raise OSError("mode file unreadable")

    monkeypatch.setattr(corrigibility_tool_gate, "get_mode", _broken_get_mode)

    decision = check_tool_under_corrigibility("Bash", {"command": "ls"})
    assert not decision.allow
    assert "fail closed" in decision.reason.lower()
