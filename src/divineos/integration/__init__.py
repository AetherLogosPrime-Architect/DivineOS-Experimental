"""Integration module - IDE, MCP tool integration, enforcement, and verification."""

from divineos.integration.enforcement import (
    setup_cli_enforcement,
    capture_user_input,
    handle_cli_error,
)
from divineos.integration.tool_wrapper import (
    wrap_tool_execution,
    is_internal_tool,
    create_tool_wrapper_decorator,
)
from divineos.integration.enforcement_verifier import (
    verify_enforcement,
    check_event_capture_rate,
    detect_missing_events,
    generate_enforcement_report,
)

__all__ = [
    "setup_cli_enforcement",
    "capture_user_input",
    "handle_cli_error",
    "wrap_tool_execution",
    "is_internal_tool",
    "create_tool_wrapper_decorator",
    "verify_enforcement",
    "check_event_capture_rate",
    "detect_missing_events",
    "generate_enforcement_report",
]
