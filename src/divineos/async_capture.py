"""
Asynchronous Event Capture Module — Non-blocking event emission with resilience.

This module provides asynchronous wrappers for event emission functions that:
1. Emit events asynchronously without blocking the IDE chat
2. Handle errors gracefully without propagating to the IDE
3. Queue events when the ledger is temporarily unavailable
4. Implement retry mechanism with exponential backoff

All operations return control to the IDE within 100ms.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime, timedelta
from loguru import logger
from collections import deque
import threading

from divineos.event_emission import (
    emit_user_input as sync_emit_user_input,
    emit_tool_call as sync_emit_tool_call,
    emit_tool_result as sync_emit_tool_result,
    emit_session_end as sync_emit_session_end,
)


class EventQueue:
    """
    Queue for events when ledger is temporarily unavailable.
    
    Stores events in memory and retries with exponential backoff.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, max_retries: int = 5, initial_backoff_ms: int = 100):
        """
        Initialize the event queue.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_backoff_ms: Initial backoff time in milliseconds
        """
        self.queue: deque = deque()
        self.max_retries = max_retries
        self.initial_backoff_ms = initial_backoff_ms
        self.lock = threading.Lock()
        self.is_processing = False
        
    def enqueue(self, event_data: Dict[str, Any]) -> None:
        """
        Add an event to the queue.
        
        Args:
            event_data: Event data including type, function, and arguments
        """
        with self.lock:
            self.queue.append(event_data)
            logger.debug(f"Event queued. Queue size: {len(self.queue)}")
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Remove and return the next event from the queue.
        
        Returns:
            Event data or None if queue is empty
        """
        with self.lock:
            if self.queue:
                return self.queue.popleft()
            return None
    
    def size(self) -> int:
        """Get the current queue size."""
        with self.lock:
            return len(self.queue)
    
    def clear(self) -> None:
        """Clear all events from the queue."""
        with self.lock:
            self.queue.clear()
            logger.debug("Event queue cleared")


# Global event queue instance
_event_queue = EventQueue()


def get_event_queue() -> EventQueue:
    """Get the global event queue instance."""
    return _event_queue


async def _retry_with_backoff(
    func: Callable,
    args: tuple,
    kwargs: dict,
    max_retries: int = 5,
    initial_backoff_ms: int = 100,
) -> Optional[str]:
    """
    Execute a function with exponential backoff retry mechanism.
    
    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        max_retries: Maximum number of retry attempts
        initial_backoff_ms: Initial backoff time in milliseconds
        
    Returns:
        Result from the function or None if all retries failed
    """
    backoff_ms = initial_backoff_ms
    
    for attempt in range(max_retries):
        try:
            # Run the sync function in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            # Create a partial function with args and kwargs to pass to executor
            import functools
            partial_func = functools.partial(func, *args, **kwargs)
            result = await loop.run_in_executor(None, partial_func)
            
            if attempt > 0:
                logger.debug(f"Event emission succeeded after {attempt} retries")
            
            return result
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.debug(f"Event emission attempt {attempt + 1} failed: {e}. Retrying in {backoff_ms}ms...")
                await asyncio.sleep(backoff_ms / 1000.0)
                backoff_ms = min(backoff_ms * 2, 5000)  # Cap at 5 seconds
            else:
                logger.error(f"Event emission failed after {max_retries} attempts: {e}")
                return None


async def emit_user_input_async(
    content: str,
    session_id: Optional[str] = None,
) -> Optional[str]:
    """
    Asynchronously emit a USER_INPUT event to the ledger.
    
    Returns control to IDE within 100ms. Errors are logged but not propagated.
    If ledger is unavailable, event is queued for retry.
    
    Args:
        content: The user message content
        session_id: Optional session ID
        
    Returns:
        event_id if successful, None if failed
        
    Requirements:
        - Requirement 6.1: Emit asynchronously without blocking IDE chat
        - Requirement 6.2: Return control to IDE within 100ms
        - Requirement 6.3: Do not propagate errors to IDE chat
        - Requirement 6.4: Queue events if ledger unavailable
    """
    try:
        start_time = time.time()
        
        # Try to emit the event with retry mechanism
        event_id = await _retry_with_backoff(
            sync_emit_user_input,
            (content,),
            {"session_id": session_id},
            max_retries=3,
            initial_backoff_ms=50,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if event_id is None:
            # Queue the event for later retry
            _event_queue.enqueue({
                "type": "USER_INPUT",
                "func": sync_emit_user_input,
                "args": (content,),
                "kwargs": {"session_id": session_id},
                "timestamp": datetime.now(),
            })
            logger.warning(f"USER_INPUT event queued due to ledger unavailability")
        else:
            logger.debug(f"USER_INPUT event emitted in {elapsed_ms:.1f}ms")
        
        return event_id
        
    except Exception as e:
        # Log error but don't propagate to IDE
        logger.error(f"Error in emit_user_input_async: {e}")
        
        # Queue the event for retry
        _event_queue.enqueue({
            "type": "USER_INPUT",
            "func": sync_emit_user_input,
            "args": (content,),
            "kwargs": {"session_id": session_id},
            "timestamp": datetime.now(),
        })
        
        return None


async def emit_tool_call_async(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_use_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[str]:
    """
    Asynchronously emit a TOOL_CALL event to the ledger.
    
    Returns control to IDE within 100ms. Errors are logged but not propagated.
    If ledger is unavailable, event is queued for retry.
    
    Args:
        tool_name: Name of the tool being called
        tool_input: Complete input parameters as a dictionary
        tool_use_id: Optional unique ID for this tool use
        session_id: Optional session ID
        
    Returns:
        event_id if successful, None if failed
        
    Requirements:
        - Requirement 6.1: Emit asynchronously without blocking IDE chat
        - Requirement 6.2: Return control to IDE within 100ms
        - Requirement 6.3: Do not propagate errors to IDE chat
        - Requirement 6.4: Queue events if ledger unavailable
    """
    try:
        start_time = time.time()
        
        # Try to emit the event with retry mechanism
        event_id = await _retry_with_backoff(
            sync_emit_tool_call,
            (tool_name, tool_input),
            {"tool_use_id": tool_use_id, "session_id": session_id},
            max_retries=3,
            initial_backoff_ms=50,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if event_id is None:
            # Queue the event for later retry
            _event_queue.enqueue({
                "type": "TOOL_CALL",
                "func": sync_emit_tool_call,
                "args": (tool_name, tool_input),
                "kwargs": {"tool_use_id": tool_use_id, "session_id": session_id},
                "timestamp": datetime.now(),
            })
            logger.warning(f"TOOL_CALL event queued due to ledger unavailability")
        else:
            logger.debug(f"TOOL_CALL event emitted in {elapsed_ms:.1f}ms")
        
        return event_id
        
    except Exception as e:
        # Log error but don't propagate to IDE
        logger.error(f"Error in emit_tool_call_async: {e}")
        
        # Queue the event for retry
        _event_queue.enqueue({
            "type": "TOOL_CALL",
            "func": sync_emit_tool_call,
            "args": (tool_name, tool_input),
            "kwargs": {"tool_use_id": tool_use_id, "session_id": session_id},
            "timestamp": datetime.now(),
        })
        
        return None


async def emit_tool_result_async(
    tool_name: str,
    tool_use_id: str,
    result: str,
    duration_ms: int,
    session_id: Optional[str] = None,
    failed: bool = False,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """
    Asynchronously emit a TOOL_RESULT event to the ledger.
    
    Returns control to IDE within 100ms. Errors are logged but not propagated.
    If ledger is unavailable, event is queued for retry.
    
    Args:
        tool_name: Name of the tool that was executed
        tool_use_id: Unique ID matching the TOOL_CALL event
        result: Complete result output
        duration_ms: Execution duration in milliseconds
        session_id: Optional session ID
        failed: Whether the tool execution failed
        error_message: Error message if failed=True
        
    Returns:
        event_id if successful, None if failed
        
    Requirements:
        - Requirement 6.1: Emit asynchronously without blocking IDE chat
        - Requirement 6.2: Return control to IDE within 100ms
        - Requirement 6.3: Do not propagate errors to IDE chat
        - Requirement 6.4: Queue events if ledger unavailable
    """
    try:
        start_time = time.time()
        
        # Try to emit the event with retry mechanism
        event_id = await _retry_with_backoff(
            sync_emit_tool_result,
            (tool_name, tool_use_id, result, duration_ms),
            {
                "session_id": session_id,
                "failed": failed,
                "error_message": error_message,
            },
            max_retries=3,
            initial_backoff_ms=50,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if event_id is None:
            # Queue the event for later retry
            _event_queue.enqueue({
                "type": "TOOL_RESULT",
                "func": sync_emit_tool_result,
                "args": (tool_name, tool_use_id, result, duration_ms),
                "kwargs": {
                    "session_id": session_id,
                    "failed": failed,
                    "error_message": error_message,
                },
                "timestamp": datetime.now(),
            })
            logger.warning(f"TOOL_RESULT event queued due to ledger unavailability")
        else:
            logger.debug(f"TOOL_RESULT event emitted in {elapsed_ms:.1f}ms")
        
        return event_id
        
    except Exception as e:
        # Log error but don't propagate to IDE
        logger.error(f"Error in emit_tool_result_async: {e}")
        
        # Queue the event for retry
        _event_queue.enqueue({
            "type": "TOOL_RESULT",
            "func": sync_emit_tool_result,
            "args": (tool_name, tool_use_id, result, duration_ms),
            "kwargs": {
                "session_id": session_id,
                "failed": failed,
                "error_message": error_message,
            },
            "timestamp": datetime.now(),
        })
        
        return None


async def emit_session_end_async(
    session_id: Optional[str] = None,
    message_count: Optional[int] = None,
    tool_call_count: Optional[int] = None,
    tool_result_count: Optional[int] = None,
    duration_seconds: Optional[float] = None,
) -> Optional[str]:
    """
    Asynchronously emit a SESSION_END event to the ledger.
    
    Returns control to IDE within 100ms. Errors are logged but not propagated.
    If ledger is unavailable, event is queued for retry.
    
    Args:
        session_id: Optional session ID
        message_count: Optional count of USER_INPUT events
        tool_call_count: Optional count of TOOL_CALL events
        tool_result_count: Optional count of TOOL_RESULT events
        duration_seconds: Optional session duration in seconds
        
    Returns:
        event_id if successful, None if failed
        
    Requirements:
        - Requirement 6.1: Emit asynchronously without blocking IDE chat
        - Requirement 6.2: Return control to IDE within 100ms
        - Requirement 6.3: Do not propagate errors to IDE chat
        - Requirement 6.4: Queue events if ledger unavailable
    """
    try:
        start_time = time.time()
        
        # Try to emit the event with retry mechanism
        event_id = await _retry_with_backoff(
            sync_emit_session_end,
            (),
            {
                "session_id": session_id,
                "message_count": message_count,
                "tool_call_count": tool_call_count,
                "tool_result_count": tool_result_count,
                "duration_seconds": duration_seconds,
            },
            max_retries=3,
            initial_backoff_ms=50,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if event_id is None:
            # Queue the event for later retry
            _event_queue.enqueue({
                "type": "SESSION_END",
                "func": sync_emit_session_end,
                "args": (),
                "kwargs": {
                    "session_id": session_id,
                    "message_count": message_count,
                    "tool_call_count": tool_call_count,
                    "tool_result_count": tool_result_count,
                    "duration_seconds": duration_seconds,
                },
                "timestamp": datetime.now(),
            })
            logger.warning(f"SESSION_END event queued due to ledger unavailability")
        else:
            logger.debug(f"SESSION_END event emitted in {elapsed_ms:.1f}ms")
        
        return event_id
        
    except Exception as e:
        # Log error but don't propagate to IDE
        logger.error(f"Error in emit_session_end_async: {e}")
        
        # Queue the event for retry
        _event_queue.enqueue({
            "type": "SESSION_END",
            "func": sync_emit_session_end,
            "args": (),
            "kwargs": {
                "session_id": session_id,
                "message_count": message_count,
                "tool_call_count": tool_call_count,
                "tool_result_count": tool_result_count,
                "duration_seconds": duration_seconds,
            },
            "timestamp": datetime.now(),
        })
        
        return None


async def flush_event_queue() -> int:
    """
    Flush all queued events by retrying them.
    
    Returns:
        Number of events successfully flushed
    """
    flushed_count = 0
    queue = get_event_queue()
    
    while queue.size() > 0:
        event_data = queue.dequeue()
        if event_data is None:
            break
        
        try:
            func = event_data["func"]
            args = event_data["args"]
            kwargs = event_data["kwargs"]
            
            # Try to emit with retry
            result = await _retry_with_backoff(
                func,
                args,
                kwargs,
                max_retries=3,
                initial_backoff_ms=100,
            )
            
            if result is not None:
                flushed_count += 1
                logger.debug(f"Flushed queued {event_data['type']} event")
            else:
                # Re-queue if still failed
                queue.enqueue(event_data)
                logger.warning(f"Failed to flush {event_data['type']} event, re-queuing")
                break
                
        except Exception as e:
            logger.error(f"Error flushing queued event: {e}")
            queue.enqueue(event_data)
            break
    
    return flushed_count


async def start_queue_flusher(interval_seconds: float = 5.0) -> None:
    """
    Start a background task that periodically flushes the event queue.
    
    Args:
        interval_seconds: How often to attempt flushing (in seconds)
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            queue = get_event_queue()
            
            if queue.size() > 0:
                flushed = await flush_event_queue()
                if flushed > 0:
                    logger.info(f"Flushed {flushed} queued events")
                    
        except Exception as e:
            logger.error(f"Error in queue flusher: {e}")
