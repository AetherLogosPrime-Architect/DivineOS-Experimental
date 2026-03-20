"""Tests for violation hooks."""

from unittest.mock import Mock, patch

from divineos.clarity_enforcement.hooks import (
    ViolationEventType,
    ViolationHook,
    ViolationHookRegistry,
    get_hook_registry,
    register_violation_hook,
    unregister_violation_hook,
    trigger_violation_hook,
    auto_explain_high_severity,
    alert_critical_severity,
    log_violation_context,
    register_default_hooks,
)
from divineos.clarity_enforcement.violation_detector import (
    ClarityViolation,
    ViolationSeverity,
)


class TestViolationEventType:
    """Test ViolationEventType enum."""

    def test_event_type_values(self):
        """Test event type enum values."""
        assert ViolationEventType.DETECTED.value == "on_violation_detected"
        assert ViolationEventType.LOGGED.value == "on_violation_logged"
        assert ViolationEventType.BLOCKED.value == "on_violation_blocked"
        assert ViolationEventType.RESOLVED.value == "on_violation_resolved"

    def test_event_type_members(self):
        """Test event type enum members."""
        members = list(ViolationEventType)
        assert len(members) == 4


class TestViolationHook:
    """Test ViolationHook class."""

    def test_violation_hook_creation(self):
        """Test creating violation hook."""
        handler = Mock()
        hook = ViolationHook(ViolationEventType.DETECTED, handler)
        assert hook.event_type == ViolationEventType.DETECTED
        assert hook.handler == handler
        assert hook.name is not None

    def test_violation_hook_with_name(self):
        """Test creating violation hook with custom name."""
        handler = Mock()
        hook = ViolationHook(
            ViolationEventType.DETECTED,
            handler,
            name="custom_hook",
        )
        assert hook.name == "custom_hook"

    def test_violation_hook_trigger(self):
        """Test triggering violation hook."""
        handler = Mock()
        hook = ViolationHook(ViolationEventType.DETECTED, handler)

        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        hook.trigger(violation)
        handler.assert_called_once_with(violation)

    def test_violation_hook_trigger_with_exception(self):
        """Test triggering hook that raises exception."""

        def failing_handler(violation):
            raise ValueError("Test error")

        hook = ViolationHook(ViolationEventType.DETECTED, failing_handler)

        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        # Should not raise, just log error
        hook.trigger(violation)


class TestViolationHookRegistry:
    """Test ViolationHookRegistry class."""

    def test_registry_creation(self):
        """Test creating hook registry."""
        registry = ViolationHookRegistry()
        assert registry is not None

    def test_register_hook(self):
        """Test registering hook."""
        registry = ViolationHookRegistry()
        handler = Mock()

        hook = registry.register(ViolationEventType.DETECTED, handler)
        assert hook is not None
        assert hook.event_type == ViolationEventType.DETECTED

    def test_register_hook_with_name(self):
        """Test registering hook with custom name."""
        registry = ViolationHookRegistry()
        handler = Mock()

        hook = registry.register(
            ViolationEventType.DETECTED,
            handler,
            name="my_hook",
        )
        assert hook.name == "my_hook"

    def test_unregister_hook(self):
        """Test unregistering hook."""
        registry = ViolationHookRegistry()
        handler = Mock()

        registry.register(
            ViolationEventType.DETECTED,
            handler,
            name="my_hook",
        )
        assert registry.unregister(ViolationEventType.DETECTED, "my_hook")

    def test_unregister_nonexistent_hook(self):
        """Test unregistering nonexistent hook."""
        registry = ViolationHookRegistry()
        assert not registry.unregister(ViolationEventType.DETECTED, "nonexistent")

    def test_trigger_hooks(self):
        """Test triggering hooks."""
        registry = ViolationHookRegistry()
        handler1 = Mock()
        handler2 = Mock()

        registry.register(ViolationEventType.DETECTED, handler1)
        registry.register(ViolationEventType.DETECTED, handler2)

        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        registry.trigger(ViolationEventType.DETECTED, violation)

        handler1.assert_called_once_with(violation)
        handler2.assert_called_once_with(violation)

    def test_trigger_specific_event_type(self):
        """Test triggering specific event type."""
        registry = ViolationHookRegistry()
        handler_detected = Mock()
        handler_logged = Mock()

        registry.register(ViolationEventType.DETECTED, handler_detected)
        registry.register(ViolationEventType.LOGGED, handler_logged)

        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        registry.trigger(ViolationEventType.DETECTED, violation)

        handler_detected.assert_called_once()
        handler_logged.assert_not_called()

    def test_get_hooks(self):
        """Test getting hooks for event type."""
        registry = ViolationHookRegistry()
        handler1 = Mock()
        handler2 = Mock()

        registry.register(ViolationEventType.DETECTED, handler1)
        registry.register(ViolationEventType.DETECTED, handler2)

        hooks = registry.get_hooks(ViolationEventType.DETECTED)
        assert len(hooks) == 2

    def test_get_hooks_empty(self):
        """Test getting hooks for event type with no hooks."""
        registry = ViolationHookRegistry()
        hooks = registry.get_hooks(ViolationEventType.DETECTED)
        assert len(hooks) == 0

    def test_clear_specific_event_type(self):
        """Test clearing hooks for specific event type."""
        registry = ViolationHookRegistry()
        handler1 = Mock()
        handler2 = Mock()

        registry.register(ViolationEventType.DETECTED, handler1)
        registry.register(ViolationEventType.LOGGED, handler2)

        registry.clear(ViolationEventType.DETECTED)

        assert len(registry.get_hooks(ViolationEventType.DETECTED)) == 0
        assert len(registry.get_hooks(ViolationEventType.LOGGED)) == 1

    def test_clear_all_hooks(self):
        """Test clearing all hooks."""
        registry = ViolationHookRegistry()
        handler1 = Mock()
        handler2 = Mock()

        registry.register(ViolationEventType.DETECTED, handler1)
        registry.register(ViolationEventType.LOGGED, handler2)

        registry.clear()

        for event_type in ViolationEventType:
            assert len(registry.get_hooks(event_type)) == 0


class TestGlobalHookRegistry:
    """Test global hook registry functions."""

    def test_get_hook_registry_singleton(self):
        """Test singleton pattern for hook registry."""
        registry1 = get_hook_registry()
        registry2 = get_hook_registry()
        assert registry1 is registry2

    def test_register_violation_hook_global(self):
        """Test registering hook globally."""
        registry = get_hook_registry()
        registry.clear()

        handler = Mock()
        hook = register_violation_hook(ViolationEventType.DETECTED, handler)
        assert hook is not None

    def test_unregister_violation_hook_global(self):
        """Test unregistering hook globally."""
        registry = get_hook_registry()
        registry.clear()

        handler = Mock()
        register_violation_hook(
            ViolationEventType.DETECTED,
            handler,
            name="test_hook",
        )
        assert unregister_violation_hook(ViolationEventType.DETECTED, "test_hook")

    def test_trigger_violation_hook_global(self):
        """Test triggering hooks globally."""
        registry = get_hook_registry()
        registry.clear()

        handler = Mock()
        register_violation_hook(ViolationEventType.DETECTED, handler)

        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        trigger_violation_hook(ViolationEventType.DETECTED, violation)
        handler.assert_called_once()


class TestBuiltInHooks:
    """Test built-in violation hooks."""

    def test_auto_explain_high_severity_critical(self):
        """Test auto-explain hook with CRITICAL violation."""
        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        with patch("divineos.clarity_enforcement.hooks.logger") as mock_logger:
            auto_explain_high_severity(violation)
            mock_logger.info.assert_called_once()

    def test_auto_explain_high_severity_high(self):
        """Test auto-explain hook with HIGH violation."""
        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        with patch("divineos.clarity_enforcement.hooks.logger") as mock_logger:
            auto_explain_high_severity(violation)
            mock_logger.info.assert_called_once()

    def test_auto_explain_high_severity_medium(self):
        """Test auto-explain hook with MEDIUM violation."""
        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.MEDIUM,
            context=[],
        )

        with patch("divineos.clarity_enforcement.hooks.logger") as mock_logger:
            auto_explain_high_severity(violation)
            mock_logger.info.assert_not_called()

    def test_alert_critical_severity_critical(self):
        """Test alert hook with CRITICAL violation."""
        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        with patch("divineos.clarity_enforcement.hooks.logger") as mock_logger:
            alert_critical_severity(violation)
            mock_logger.warning.assert_called_once()

    def test_alert_critical_severity_high(self):
        """Test alert hook with HIGH violation."""
        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=[],
        )

        with patch("divineos.clarity_enforcement.hooks.logger") as mock_logger:
            alert_critical_severity(violation)
            mock_logger.warning.assert_called_once()

    def test_log_violation_context(self):
        """Test context logging hook."""
        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=["key: value"],
        )

        with patch("divineos.clarity_enforcement.hooks.logger") as mock_logger:
            log_violation_context(violation)
            mock_logger.debug.assert_called_once()


class TestRegisterDefaultHooks:
    """Test registering default hooks."""

    def test_register_default_hooks(self):
        """Test registering default hooks."""
        registry = get_hook_registry()
        registry.clear()

        register_default_hooks()

        # Check that hooks were registered
        detected_hooks = registry.get_hooks(ViolationEventType.DETECTED)
        logged_hooks = registry.get_hooks(ViolationEventType.LOGGED)

        assert len(detected_hooks) >= 2  # auto_explain and alert
        assert len(logged_hooks) >= 1  # log_context

    def test_default_hooks_functionality(self):
        """Test default hooks work correctly."""
        registry = get_hook_registry()
        registry.clear()

        register_default_hooks()

        violation = ClarityViolation(
            tool_name="test_tool",
            tool_input={},
            severity=ViolationSeverity.HIGH,
            context=["test context"],
        )

        with patch("divineos.clarity_enforcement.hooks.logger"):
            # Should not raise
            registry.trigger(ViolationEventType.DETECTED, violation)
