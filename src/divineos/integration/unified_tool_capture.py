"""Unified Tool Capture - Adapter for backward compatibility.

This module re-exports the unified tool capture functionality from
core/tool_wrapper.py, which is the canonical implementation.

The UnifiedToolCapture class, get_unified_capture(), and capture_tool_execution()
functions are now defined in core/tool_wrapper.py as part of the consolidation
effort to have a single source of truth for tool capture.

This module is kept for backward compatibility with existing imports.
"""

# Re-export from canonical location
from divineos.core.tool_wrapper import (
    UnifiedToolCapture,
    capture_tool_execution,
    get_unified_capture,
)

__all__ = [
    "UnifiedToolCapture",
    "capture_tool_execution",
    "get_unified_capture",
]
