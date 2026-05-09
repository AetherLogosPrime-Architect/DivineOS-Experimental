"""Tests for fix verifier — catches premature 'it's fixed' claims."""

import json
import time

from divineos.core.fix_verifier import (
    check_verification_needed,
    clear_verification,
    is_verification_command,
    mark_fix_attempted,
)


class TestMarkAndCheck:
    def test_no_pending_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        assert check_verification_needed("Edit") is None

    def test_mark_then_check_returns_advisory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        mark_fix_attempted("src/foo.py", "NameError: bar")
        msg = check_verification_needed("Edit")
        assert msg is not None
        assert "VERIFY-FIX" in msg
        assert "foo.py" in msg

    def test_clear_removes_pending(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        mark_fix_attempted("src/foo.py")
        clear_verification()
        assert check_verification_needed("Edit") is None

    def test_only_fires_on_edit_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        mark_fix_attempted("src/foo.py")
        # Non-edit tools don't trigger the advisory
        assert check_verification_needed("Read") is None
        assert check_verification_needed("Bash") is None
        assert check_verification_needed("Grep") is None

    def test_expires_after_timeout(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        from divineos.core.paths import marker_path

        mark_fix_attempted("src/foo.py")
        # Manually backdate the marker
        path = marker_path("pending_verification.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["timestamp"] = time.time() - 700  # > 600s expiry
        path.write_text(json.dumps(data), encoding="utf-8")
        assert check_verification_needed("Edit") is None


class TestVerificationCommands:
    def test_pytest_is_verification(self):
        assert is_verification_command("Bash", {"command": "pytest tests/ -q"})

    def test_precommit_is_verification(self):
        assert is_verification_command("Bash", {"command": "bash scripts/precommit.sh"})

    def test_random_bash_is_not(self):
        assert not is_verification_command("Bash", {"command": "ls -la"})

    def test_edit_is_not_verification(self):
        assert not is_verification_command("Edit", {"file_path": "foo.py"})
