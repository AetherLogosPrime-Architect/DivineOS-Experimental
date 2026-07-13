"""Integration module - IDE, MCP tool integration, enforcement, and verification."""

from divineos.core.enforcement import (
    capture_user_input,
    handle_cli_error,
    setup_cli_enforcement,
)
from divineos.core.enforcement_verifier import (
    check_event_capture_rate,
    detect_missing_events,
    generate_enforcement_report,
    verify_enforcement,
)
from divineos.core.tool_wrapper import (
    capture_tool_execution,
    get_unified_capture,
    is_internal_tool,
    wrap_tool_execution,
)

__all__ = [
    "capture_tool_execution",
    "capture_user_input",
    "check_event_capture_rate",
    "detect_missing_events",
    "generate_enforcement_report",
    "get_unified_capture",
    "handle_cli_error",
    "is_internal_tool",
    "setup_cli_enforcement",
    "verify_enforcement",
    "wrap_tool_execution",
]
