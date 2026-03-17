"""
Tests for hook validator module.

Tests validation of hook configuration files including:
- JSON structure validation
- Required field validation
- Event type validation
- Action type validation
- Error handling and reporting
"""

import json
import tempfile
from pathlib import Path

from divineos.hook_validator import (
    validate_hook_structure,
    validate_hook_file,
    load_hooks_from_directory,
    VALID_EVENT_TYPES,
)


class TestHookStructureValidation:
    """Test hook structure validation."""

    def test_valid_ask_agent_hook(self):
        """Test validation of a valid askAgent hook."""
        hook = {
            "name": "Test Hook",
            "version": "1.0.0",
            "when": {
                "type": "promptSubmit",
            },
            "then": {
                "type": "askAgent",
                "prompt": "Test prompt",
            },
        }
        is_valid, error = validate_hook_structure(hook)
        assert is_valid
        assert error == ""

    def test_valid_run_command_hook(self):
        """Test validation of a valid runCommand hook."""
        hook = {
            "name": "Test Hook",
            "version": "1.0.0",
            "when": {
                "type": "agentStop",
            },
            "then": {
                "type": "runCommand",
                "command": "npm run test",
            },
        }
        is_valid, error = validate_hook_structure(hook)
        assert is_valid
        assert error == ""

    def test_missing_name_field(self):
        """Test validation fails when name is missing."""
        hook = {
            "version": "1.0.0",
            "when": {"type": "promptSubmit"},
            "then": {"type": "askAgent", "prompt": "test"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "name" in error.lower()

    def test_missing_version_field(self):
        """Test validation fails when version is missing."""
        hook = {
            "name": "Test",
            "when": {"type": "promptSubmit"},
            "then": {"type": "askAgent", "prompt": "test"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "version" in error.lower()

    def test_missing_when_field(self):
        """Test validation fails when when is missing."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "then": {"type": "askAgent", "prompt": "test"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "when" in error.lower()

    def test_missing_then_field(self):
        """Test validation fails when then is missing."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "promptSubmit"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "then" in error.lower()

    def test_empty_name(self):
        """Test validation fails when name is empty."""
        hook = {
            "name": "",
            "version": "1.0.0",
            "when": {"type": "promptSubmit"},
            "then": {"type": "askAgent", "prompt": "test"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "name" in error.lower()

    def test_invalid_event_type(self):
        """Test validation fails with invalid event type."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "invalidEvent"},
            "then": {"type": "askAgent", "prompt": "test"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "event type" in error.lower()

    def test_invalid_action_type(self):
        """Test validation fails with invalid action type."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "promptSubmit"},
            "then": {"type": "invalidAction"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "action type" in error.lower()

    def test_ask_agent_missing_prompt(self):
        """Test validation fails when askAgent is missing prompt."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "promptSubmit"},
            "then": {"type": "askAgent"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "prompt" in error.lower()

    def test_run_command_missing_command(self):
        """Test validation fails when runCommand is missing command."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "agentStop"},
            "then": {"type": "runCommand"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        assert "command" in error.lower()

    def test_all_valid_event_types(self):
        """Test that all valid event types are accepted."""
        for event_type in VALID_EVENT_TYPES:
            hook = {
                "name": "Test",
                "version": "1.0.0",
                "when": {"type": event_type},
                "then": {"type": "askAgent", "prompt": "test"},
            }
            is_valid, error = validate_hook_structure(hook)
            assert is_valid, f"Event type {event_type} should be valid"


class TestHookFileValidation:
    """Test hook file validation."""

    def test_valid_hook_file(self):
        """Test validation of a valid hook file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = Path(tmpdir) / "test.kiro.hook"
            hook_data = {
                "name": "Test Hook",
                "version": "1.0.0",
                "when": {"type": "promptSubmit"},
                "then": {"type": "askAgent", "prompt": "test"},
            }
            hook_file.write_text(json.dumps(hook_data))

            is_valid, error, data = validate_hook_file(hook_file)
            assert is_valid
            assert error == ""
            assert data == hook_data

    def test_invalid_json(self):
        """Test validation fails with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = Path(tmpdir) / "test.kiro.hook"
            hook_file.write_text("{invalid json")

            is_valid, error, data = validate_hook_file(hook_file)
            assert not is_valid
            assert "json" in error.lower()
            assert data is None

    def test_file_not_found(self):
        """Test validation fails when file doesn't exist."""
        hook_file = Path("/nonexistent/hook.kiro.hook")
        is_valid, error, data = validate_hook_file(hook_file)
        assert not is_valid
        assert "not found" in error.lower()
        assert data is None

    def test_invalid_structure_in_file(self):
        """Test validation fails with invalid structure in file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = Path(tmpdir) / "test.kiro.hook"
            hook_data = {
                "name": "Test",
                # Missing version, when, then
            }
            hook_file.write_text(json.dumps(hook_data))

            is_valid, error, data = validate_hook_file(hook_file)
            assert not is_valid
            assert data is None


class TestLoadHooksFromDirectory:
    """Test loading hooks from directory."""

    def test_load_valid_hooks(self):
        """Test loading valid hooks from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create valid hook files
            hook1 = {
                "name": "Hook 1",
                "version": "1.0.0",
                "when": {"type": "promptSubmit"},
                "then": {"type": "askAgent", "prompt": "test1"},
            }
            hook2 = {
                "name": "Hook 2",
                "version": "1.0.0",
                "when": {"type": "agentStop"},
                "then": {"type": "runCommand", "command": "test"},
            }

            (tmpdir_path / "hook1.kiro.hook").write_text(json.dumps(hook1))
            (tmpdir_path / "hook2.kiro.hook").write_text(json.dumps(hook2))

            valid_hooks, invalid_hooks = load_hooks_from_directory(tmpdir_path)

            assert len(valid_hooks) == 2
            assert len(invalid_hooks) == 0

    def test_load_mixed_valid_invalid_hooks(self):
        """Test loading directory with both valid and invalid hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Valid hook
            valid_hook = {
                "name": "Valid",
                "version": "1.0.0",
                "when": {"type": "promptSubmit"},
                "then": {"type": "askAgent", "prompt": "test"},
            }
            (tmpdir_path / "valid.kiro.hook").write_text(json.dumps(valid_hook))

            # Invalid hook (missing fields)
            invalid_hook = {"name": "Invalid"}
            (tmpdir_path / "invalid.kiro.hook").write_text(json.dumps(invalid_hook))

            valid_hooks, invalid_hooks = load_hooks_from_directory(tmpdir_path)

            assert len(valid_hooks) == 1
            assert len(invalid_hooks) == 1
            assert invalid_hooks[0]["file"] == "invalid.kiro.hook"

    def test_load_from_nonexistent_directory(self):
        """Test loading from nonexistent directory."""
        nonexistent = Path("/nonexistent/hooks")
        valid_hooks, invalid_hooks = load_hooks_from_directory(nonexistent)

        assert len(valid_hooks) == 0
        assert len(invalid_hooks) == 0

    def test_load_empty_directory(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            valid_hooks, invalid_hooks = load_hooks_from_directory(tmpdir_path)

            assert len(valid_hooks) == 0
            assert len(invalid_hooks) == 0

    def test_ignores_non_hook_files(self):
        """Test that non-hook files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a hook file
            hook = {
                "name": "Hook",
                "version": "1.0.0",
                "when": {"type": "promptSubmit"},
                "then": {"type": "askAgent", "prompt": "test"},
            }
            (tmpdir_path / "hook.kiro.hook").write_text(json.dumps(hook))

            # Create non-hook files
            (tmpdir_path / "readme.txt").write_text("not a hook")
            (tmpdir_path / "config.json").write_text("{}")

            valid_hooks, invalid_hooks = load_hooks_from_directory(tmpdir_path)

            assert len(valid_hooks) == 1
            assert len(invalid_hooks) == 0


class TestErrorMessages:
    """Test that error messages are clear and helpful."""

    def test_error_message_includes_valid_event_types(self):
        """Test that error message includes list of valid event types."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "invalidEvent"},
            "then": {"type": "askAgent", "prompt": "test"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        # Should mention some valid event types
        assert any(et in error for et in ["promptSubmit", "agentStop"])

    def test_error_message_includes_valid_action_types(self):
        """Test that error message includes list of valid action types."""
        hook = {
            "name": "Test",
            "version": "1.0.0",
            "when": {"type": "promptSubmit"},
            "then": {"type": "invalidAction"},
        }
        is_valid, error = validate_hook_structure(hook)
        assert not is_valid
        # Should mention valid action types
        assert any(at in error for at in ["askAgent", "runCommand"])
