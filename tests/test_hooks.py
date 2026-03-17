"""Tests for Kiro hook files and hook integration."""

import json
import pytest
from pathlib import Path


class TestHookFileFormat:
    """Test hook file format and JSON validity."""

    @pytest.fixture
    def hooks_dir(self):
        """Get the hooks directory."""
        return Path(__file__).parent.parent / ".kiro" / "hooks"

    @pytest.fixture
    def hook_files(self, hooks_dir):
        """Get all hook files."""
        return list(hooks_dir.glob("*.kiro.hook"))

    def test_hook_files_exist(self, hooks_dir):
        """Test that all required hook files exist."""
        required_hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in required_hooks:
            hook_path = hooks_dir / hook_name
            assert hook_path.exists(), f"Hook file {hook_name} not found"

    def test_hook_files_are_valid_json(self, hook_files):
        """Test that all hook files are valid JSON."""
        for hook_file in hook_files:
            with open(hook_file, "r") as f:
                content = f.read()
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Hook file {hook_file.name} is not valid JSON: {e}")

    def test_hook_files_not_empty(self, hook_files):
        """Test that hook files are not empty."""
        for hook_file in hook_files:
            with open(hook_file, "r") as f:
                content = f.read().strip()
                assert len(content) > 0, f"Hook file {hook_file.name} is empty"

    def test_hook_files_readable(self, hook_files):
        """Test that hook files are readable."""
        for hook_file in hook_files:
            try:
                with open(hook_file, "r") as f:
                    f.read()
            except Exception as e:
                pytest.fail(f"Cannot read hook file {hook_file.name}: {e}")


class TestHookSchema:
    """Test hook JSON schema compliance."""

    @pytest.fixture
    def hooks_dir(self):
        """Get the hooks directory."""
        return Path(__file__).parent.parent / ".kiro" / "hooks"

    @pytest.fixture
    def load_hook(self, hooks_dir):
        """Load a hook file."""

        def _load(hook_name):
            hook_path = hooks_dir / hook_name
            with open(hook_path, "r") as f:
                return json.load(f)

        return _load

    def test_hook_has_required_fields(self, load_hook):
        """Test that hooks have required fields."""
        required_fields = ["name", "version", "when", "then"]

        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            for field in required_fields:
                assert field in hook, f"Hook {hook_name} missing required field: {field}"

    def test_hook_when_has_type(self, load_hook):
        """Test that hook 'when' clause has 'type' field."""
        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            assert "type" in hook["when"], f"Hook {hook_name} 'when' clause missing 'type'"

    def test_hook_then_has_type(self, load_hook):
        """Test that hook 'then' clause has 'type' field."""
        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            assert "type" in hook["then"], f"Hook {hook_name} 'then' clause missing 'type'"

    def test_hook_when_type_valid(self, load_hook):
        """Test that hook 'when' type is valid."""
        valid_types = ["promptSubmit", "postToolUse", "agentStop", "preToolUse", "fileEdited"]

        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            when_type = hook["when"]["type"]
            assert when_type in valid_types, (
                f"Hook {hook_name} has invalid 'when' type: {when_type}"
            )

    def test_hook_then_type_valid(self, load_hook):
        """Test that hook 'then' type is valid."""
        valid_types = ["askAgent", "runCommand"]

        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            then_type = hook["then"]["type"]
            assert then_type in valid_types, (
                f"Hook {hook_name} has invalid 'then' type: {then_type}"
            )

    def test_hook_askagent_has_prompt(self, load_hook):
        """Test that askAgent hooks have 'prompt' field."""
        askagent_hooks = [
            "capture-user-input.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in askagent_hooks:
            hook = load_hook(hook_name)
            if hook["then"]["type"] == "askAgent":
                assert "prompt" in hook["then"], f"Hook {hook_name} askAgent missing 'prompt'"

    def test_hook_runcommand_has_command(self, load_hook):
        """Test that runCommand hooks have 'command' field."""
        runcommand_hooks = [
            "capture-session-end.kiro.hook",
        ]

        for hook_name in runcommand_hooks:
            hook = load_hook(hook_name)
            if hook["then"]["type"] == "runCommand":
                assert "command" in hook["then"], f"Hook {hook_name} runCommand missing 'command'"

    def test_hook_version_format(self, load_hook):
        """Test that hook version is in valid format."""
        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            version = hook["version"]
            # Version should be string like "1.0.0" or "1"
            assert isinstance(version, str), f"Hook {hook_name} version is not a string"
            assert len(version) > 0, f"Hook {hook_name} version is empty"


class TestHookContent:
    """Test hook content and configuration."""

    @pytest.fixture
    def hooks_dir(self):
        """Get the hooks directory."""
        return Path(__file__).parent.parent / ".kiro" / "hooks"

    @pytest.fixture
    def load_hook(self, hooks_dir):
        """Load a hook file."""

        def _load(hook_name):
            hook_path = hooks_dir / hook_name
            with open(hook_path, "r") as f:
                return json.load(f)

        return _load

    def test_capture_user_input_hook(self, load_hook):
        """Test capture-user-input hook configuration."""
        hook = load_hook("capture-user-input.kiro.hook")

        assert hook["name"] == "Capture user input to ledger"
        assert hook["when"]["type"] == "promptSubmit"
        assert hook["then"]["type"] == "askAgent"
        assert "prompt" in hook["then"]
        assert len(hook["then"]["prompt"]) > 0

    def test_capture_session_end_hook(self, load_hook):
        """Test capture-session-end hook configuration."""
        hook = load_hook("capture-session-end.kiro.hook")

        assert hook["name"] == "Capture session end"
        assert hook["when"]["type"] == "agentStop"
        assert hook["then"]["type"] == "askAgent"
        assert "prompt" in hook["then"]
        assert "divineos emit SESSION_END" in hook["then"]["prompt"]

    def test_capture_tool_calls_hook(self, load_hook):
        """Test capture-tool-calls hook configuration."""
        hook = load_hook("capture-tool-calls.kiro.hook")

        assert hook["name"] == "Capture tool calls and results"
        assert hook["when"]["type"] == "postToolUse"
        assert hook["then"]["type"] == "askAgent"
        assert "prompt" in hook["then"]
        assert len(hook["then"]["prompt"]) > 0

    def test_auto_analyze_sessions_hook(self, load_hook):
        """Test auto-analyze-sessions hook configuration."""
        hook = load_hook("auto-analyze-sessions.kiro.hook")

        assert hook["name"] == "Auto-analyze sessions"
        assert hook["when"]["type"] == "agentStop"
        assert hook["then"]["type"] == "askAgent"
        assert "prompt" in hook["then"]
        assert "analyze" in hook["then"]["prompt"].lower()

    def test_hook_descriptions_present(self, load_hook):
        """Test that all hooks have descriptions."""
        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in hooks:
            hook = load_hook(hook_name)
            assert "description" in hook, f"Hook {hook_name} missing description"
            assert len(hook["description"]) > 0, f"Hook {hook_name} description is empty"

    def test_hook_names_unique(self, load_hook):
        """Test that all hook names are unique."""
        hooks = [
            "capture-user-input.kiro.hook",
            "capture-session-end.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        names = []
        for hook_name in hooks:
            hook = load_hook(hook_name)
            names.append(hook["name"])

        assert len(names) == len(set(names)), "Hook names are not unique"


class TestHookTriggers:
    """Test hook trigger event types."""

    @pytest.fixture
    def hooks_dir(self):
        """Get the hooks directory."""
        return Path(__file__).parent.parent / ".kiro" / "hooks"

    @pytest.fixture
    def load_hook(self, hooks_dir):
        """Load a hook file."""

        def _load(hook_name):
            hook_path = hooks_dir / hook_name
            with open(hook_path, "r") as f:
                return json.load(f)

        return _load

    def test_promptsubmit_trigger(self, load_hook):
        """Test that promptSubmit trigger is configured correctly."""
        hook = load_hook("capture-user-input.kiro.hook")
        assert hook["when"]["type"] == "promptSubmit"

    def test_posttooluse_trigger(self, load_hook):
        """Test that postToolUse trigger is configured correctly."""
        hook = load_hook("capture-tool-calls.kiro.hook")
        assert hook["when"]["type"] == "postToolUse"

    def test_agentstop_triggers(self, load_hook):
        """Test that agentStop triggers are configured correctly."""
        session_end_hook = load_hook("capture-session-end.kiro.hook")
        assert session_end_hook["when"]["type"] == "agentStop"

        analyze_hook = load_hook("auto-analyze-sessions.kiro.hook")
        assert analyze_hook["when"]["type"] == "agentStop"

    def test_multiple_hooks_same_trigger(self, load_hook):
        """Test that multiple hooks can trigger on same event."""
        session_end_hook = load_hook("capture-session-end.kiro.hook")
        analyze_hook = load_hook("auto-analyze-sessions.kiro.hook")

        # Both should trigger on agentStop
        assert session_end_hook["when"]["type"] == "agentStop"
        assert analyze_hook["when"]["type"] == "agentStop"

        # Both should use askAgent to ensure proper event emission
        assert session_end_hook["then"]["type"] == "askAgent"
        assert analyze_hook["then"]["type"] == "askAgent"


class TestHookActions:
    """Test hook action types and configurations."""

    @pytest.fixture
    def hooks_dir(self):
        """Get the hooks directory."""
        return Path(__file__).parent.parent / ".kiro" / "hooks"

    @pytest.fixture
    def load_hook(self, hooks_dir):
        """Load a hook file."""

        def _load(hook_name):
            hook_path = hooks_dir / hook_name
            with open(hook_path, "r") as f:
                return json.load(f)

        return _load

    def test_askagent_actions(self, load_hook):
        """Test that askAgent actions are configured correctly."""
        askagent_hooks = [
            "capture-user-input.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in askagent_hooks:
            hook = load_hook(hook_name)
            assert hook["then"]["type"] == "askAgent"
            assert "prompt" in hook["then"]
            assert len(hook["then"]["prompt"]) > 0

    def test_prompts_not_empty(self, load_hook):
        """Test that all prompts are not empty."""
        askagent_hooks = [
            "capture-user-input.kiro.hook",
            "capture-tool-calls.kiro.hook",
            "auto-analyze-sessions.kiro.hook",
        ]

        for hook_name in askagent_hooks:
            hook = load_hook(hook_name)
            prompt = hook["then"]["prompt"]
            assert len(prompt) > 0, f"Hook {hook_name} has empty prompt"
            assert len(prompt) < 1000, f"Hook {hook_name} prompt is too long"

    def test_session_end_hook_uses_emit_function(self, load_hook):
        """Test that session end hook uses divineos emit SESSION_END command."""
        hook = load_hook("capture-session-end.kiro.hook")
        prompt = hook["then"]["prompt"]
        assert "divineos emit SESSION_END" in prompt, (
            "Prompt should reference divineos emit SESSION_END command"
        )
