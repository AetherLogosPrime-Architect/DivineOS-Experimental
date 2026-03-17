"""
IDE Tool Integration — Middleware to capture tool execution from IDE.

This module provides integration points for the IDE to emit TOOL_CALL and
TOOL_RESULT events when tools are executed. It acts as a bridge between
the IDE tool execution layer and the DivineOS event ledger.
"""

import time
import uuid
from typing import Any, Dict, Optional
from loguru import logger

from divineos.event_emission import emit_tool_call, emit_tool_result


class IDEToolExecutor:
    """
    Middleware for IDE tool execution that captures events.
    
    Usage:
        executor = IDEToolExecutor()
        result = executor.execute_tool("readFile", {"path": "file.py"})
    """
    
    def __init__(self):
        """Initialize the IDE tool executor."""
        self.active_tools: Dict[str, Dict[str, Any]] = {}
    
    def start_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: Optional[str] = None
    ) -> str:
        """
        Record the start of a tool execution and emit TOOL_CALL event.
        
        Args:
            tool_name: Name of the tool being executed
            tool_input: Input parameters for the tool
            tool_use_id: Optional unique ID for this tool use
        
        Returns:
            tool_use_id: The ID for this tool execution (for later reference)
        """
        if tool_use_id is None:
            tool_use_id = str(uuid.uuid4())
        
        # Record tool execution start
        self.active_tools[tool_use_id] = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "start_time": time.time(),
            "tool_use_id": tool_use_id
        }
        
        # Emit TOOL_CALL event
        try:
            event_id = emit_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id
            )
            logger.debug(f"Emitted TOOL_CALL for {tool_name}: {event_id}")
        except Exception as e:
            logger.error(f"Failed to emit TOOL_CALL for {tool_name}: {e}")
        
        return tool_use_id
    
    def end_tool_execution(
        self,
        tool_use_id: str,
        result: str,
        failed: bool = False,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Record the end of a tool execution and emit TOOL_RESULT event.
        
        Args:
            tool_use_id: The ID returned from start_tool_execution
            result: The result output from the tool
            failed: Whether the tool execution failed
            error_message: Error message if failed=True
        
        Returns:
            event_id: The ID of the emitted TOOL_RESULT event, or None if failed
        """
        if tool_use_id not in self.active_tools:
            logger.warning(f"Tool execution {tool_use_id} not found in active tools")
            return None
        
        tool_info = self.active_tools.pop(tool_use_id)
        duration_ms = int((time.time() - tool_info["start_time"]) * 1000)
        
        # Emit TOOL_RESULT event
        try:
            event_id = emit_tool_result(
                tool_name=tool_info["tool_name"],
                tool_use_id=tool_use_id,
                result=result,
                duration_ms=duration_ms,
                failed=failed,
                error_message=error_message
            )
            logger.debug(f"Emitted TOOL_RESULT for {tool_info['tool_name']}: {event_id}")
            return event_id
        except Exception as e:
            logger.error(f"Failed to emit TOOL_RESULT for {tool_info['tool_name']}: {e}")
            return None
    
    def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_function: callable,
        tool_use_id: Optional[str] = None
    ) -> Any:
        """
        Execute a tool and automatically capture TOOL_CALL and TOOL_RESULT events.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            tool_function: The actual tool function to execute
            tool_use_id: Optional unique ID for this tool use
        
        Returns:
            The result from tool_function
        
        Raises:
            Exception: Re-raises any exception from tool_function
        """
        # Start tool execution and emit TOOL_CALL
        tool_use_id = self.start_tool_execution(tool_name, tool_input, tool_use_id)
        
        try:
            # Execute the tool
            result = tool_function(**tool_input)
            result_str = str(result) if not isinstance(result, str) else result
            
            # End tool execution and emit TOOL_RESULT
            self.end_tool_execution(tool_use_id, result_str, failed=False)
            
            return result
        
        except Exception as e:
            # End tool execution with failure and emit TOOL_RESULT
            error_msg = str(e)
            self.end_tool_execution(
                tool_use_id,
                error_msg,
                failed=True,
                error_message=error_msg
            )
            raise


# Global executor instance
_executor = IDEToolExecutor()


def get_ide_tool_executor() -> IDEToolExecutor:
    """Get the global IDE tool executor instance."""
    return _executor


def emit_tool_call_for_ide(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_use_id: Optional[str] = None
) -> str:
    """
    Emit a TOOL_CALL event for IDE tool execution.
    
    This is called by the IDE when a tool is about to be executed.
    
    Args:
        tool_name: Name of the tool
        tool_input: Input parameters
        tool_use_id: Optional unique ID
    
    Returns:
        tool_use_id: The ID for this tool execution
    """
    return _executor.start_tool_execution(tool_name, tool_input, tool_use_id)


def emit_tool_result_for_ide(
    tool_use_id: str,
    result: str,
    failed: bool = False,
    error_message: Optional[str] = None
) -> Optional[str]:
    """
    Emit a TOOL_RESULT event for IDE tool execution.
    
    This is called by the IDE when a tool has completed execution.
    
    Args:
        tool_use_id: The ID returned from emit_tool_call_for_ide
        result: The result output from the tool
        failed: Whether the tool execution failed
        error_message: Error message if failed=True
    
    Returns:
        event_id: The ID of the emitted TOOL_RESULT event
    """
    return _executor.end_tool_execution(tool_use_id, result, failed, error_message)
