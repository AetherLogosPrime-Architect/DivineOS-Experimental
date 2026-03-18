"""Integration module - IDE, MCP tool integration, enforcement, and verification."""

from divineos.core.enforcement import (
    setup_cli_enforcement,
    capture_user_input,
    handle_cli_error,
)
from divineos.core.tool_wrapper import (
    wrap_tool_execution,
    is_internal_tool,
)
from divineos.core.enforcement_verifier import (
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
    "verify_enforcement",
    "check_event_capture_rate",
    "detect_missing_events",
    "generate_enforcement_report",
]
