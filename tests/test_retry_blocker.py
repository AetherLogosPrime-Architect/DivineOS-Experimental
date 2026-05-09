"""Tests for the retry blocker gate."""

import json
import time

import pytest

from divineos.core.retry_blocker import (
    _command_signature,
    _tracker_path,
    check_retry,
    clear_all,
    is_diagnostic_command,
    mark_investigated,
    record_failure,
)


@pytest.fixture(autouse=True)
def _clean_tracker():
    """Ensure clean state before and after each test."""
    clear_all()
    yield
    clear_all()


class TestCommandSignature:
    def test_edit_uses_file_path(self):
        sig = _command_signature("Edit", {"file_path": "/foo/bar.py", "old_string": "x"})
        assert sig == "Edit:/foo/bar.py"

    def test_bash_uses_first_three_words(self):
        sig = _command_signature("Bash", {"command": "pytest tests/ -q --tb=short"})
        assert sig == "Bash:pytest tests/ -q"

    def test_bash_short_command(self):
        sig = _command_signature("Bash", {"command": "ls"})
        assert sig == "Bash:ls"

    def test_other_tool_uses_first_string_arg(self):
        sig = _command_signature("Grep", {"pattern": "foo.*bar", "path": "/src"})
        # sorted keys: path comes before pattern
        assert "Grep:" in sig


class TestRecordAndCheck:
    def test_first_attempt_not_blocked(self):
        """First attempt at a command is never blocked."""
        result = check_retry("Edit", {"file_path": "/foo.py"})
        assert result is None

    def test_retry_after_failure_blocked(self):
        """Same command after failure without investigation is blocked."""
        record_failure("Edit", {"file_path": "/foo.py"}, "SyntaxError")
        result = check_retry("Edit", {"file_path": "/foo.py"})
        assert result is not None
        assert "BLOCKED" in result
        assert "SyntaxError" in result

    def test_different_command_not_blocked(self):
        """Different command after failure is not blocked."""
        record_failure("Edit", {"file_path": "/foo.py"}, "error")
        result = check_retry("Edit", {"file_path": "/bar.py"})
        assert result is None

    def test_investigation_clears_block(self):
        """Marking as investigated clears the retry block."""
        record_failure("Edit", {"file_path": "/foo.py"}, "error")
        mark_investigated()
        result = check_retry("Edit", {"file_path": "/foo.py"})
        assert result is None

    def test_clear_all_removes_tracker(self):
        record_failure("Edit", {"file_path": "/foo.py"}, "error")
        clear_all()
        result = check_retry("Edit", {"file_path": "/foo.py"})
        assert result is None


class TestDiagnosticDetection:
    def test_read_is_diagnostic(self):
        assert is_diagnostic_command("Read", {"file_path": "/foo.py"})

    def test_grep_is_diagnostic(self):
        assert is_diagnostic_command("Grep", {"pattern": "foo"})

    def test_glob_is_diagnostic(self):
        assert is_diagnostic_command("Glob", {"pattern": "*.py"})

    def test_git_diff_is_diagnostic(self):
        assert is_diagnostic_command("Bash", {"command": "git diff src/"})

    def test_divineos_ask_is_diagnostic(self):
        assert is_diagnostic_command("Bash", {"command": "divineos ask 'retry'"})

    def test_edit_is_not_diagnostic(self):
        assert not is_diagnostic_command("Edit", {"file_path": "/foo.py"})

    def test_write_is_not_diagnostic(self):
        assert not is_diagnostic_command("Write", {"file_path": "/foo.py"})

    def test_bash_edit_is_not_diagnostic(self):
        assert not is_diagnostic_command("Bash", {"command": "sed -i 's/foo/bar/' file.py"})


class TestExpiry:
    def test_old_failures_expire(self, monkeypatch):
        """Failures older than FAILURE_EXPIRY_SECONDS are pruned."""
        record_failure("Edit", {"file_path": "/foo.py"}, "error")

        # Manually age the entry
        path = _tracker_path()
        data = json.loads(path.read_text())
        data[0]["timestamp"] = time.time() - 400  # > 300s expiry
        path.write_text(json.dumps(data))

        result = check_retry("Edit", {"file_path": "/foo.py"})
        assert result is None  # expired, not blocked
