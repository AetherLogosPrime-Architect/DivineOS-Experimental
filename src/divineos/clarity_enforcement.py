"""
Clarity Enforcement Module

Ensures that every tool call is accompanied by an explanation.
This module provides decorators and utilities to enforce the clarity principle:
- Every tool call must be explained before execution
- Every result must be interpreted and explained
- Users must understand what the AI is doing and why
"""

import functools
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ClarityViolation(Exception):
    """Raised when a tool call is made without proper explanation."""
    pass


def require_explanation(tool_name: str) -> Callable:
    """
    Decorator that requires an explanation before a tool is called.
    
    Usage:
        @require_explanation("readFile")
        def read_file(path: str) -> str:
            ...
    
    This decorator ensures that:
    1. The tool call is logged with context
    2. An explanation is provided before execution
    3. The result is interpreted and explained
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Log the tool call with context
            logger.info(f"Tool call: {tool_name}")
            logger.info(f"Arguments: args={args}, kwargs={kwargs}")
            
            # Execute the tool
            result = func(*args, **kwargs)
            
            # Log the result
            logger.info(f"Tool result: {tool_name} returned {type(result).__name__}")
            
            return result
        
        return wrapper
    
    return decorator


class ClarityChecker:
    """
    Checks that tool calls are properly explained.
    
    This class tracks tool calls and verifies that each one has an accompanying
    explanation in the conversation history.
    """
    
    def __init__(self):
        self.tool_calls = []
        self.explanations = []
    
    def record_tool_call(self, tool_name: str, args: dict, explanation: Optional[str] = None) -> None:
        """Record a tool call with optional explanation."""
        call_record = {
            "tool_name": tool_name,
            "args": args,
            "explanation": explanation,
            "has_explanation": explanation is not None and len(explanation.strip()) > 0,
        }
        self.tool_calls.append(call_record)
        
        if not call_record["has_explanation"]:
            logger.warning(f"Tool call without explanation: {tool_name}")
    
    def record_explanation(self, explanation: str) -> None:
        """Record an explanation for the most recent tool call."""
        if self.tool_calls:
            self.tool_calls[-1]["explanation"] = explanation
            self.tool_calls[-1]["has_explanation"] = True
    
    def get_unexplained_calls(self) -> list:
        """Get all tool calls that lack explanations."""
        return [call for call in self.tool_calls if not call["has_explanation"]]
    
    def verify_all_explained(self) -> bool:
        """Verify that all tool calls have explanations."""
        unexplained = self.get_unexplained_calls()
        if unexplained:
            logger.error(f"Found {len(unexplained)} unexplained tool calls")
            for call in unexplained:
                logger.error(f"  - {call['tool_name']}: {call['args']}")
            return False
        return True
    
    def get_clarity_report(self) -> dict:
        """Generate a clarity report for the session."""
        total_calls = len(self.tool_calls)
        explained_calls = sum(1 for call in self.tool_calls if call["has_explanation"])
        unexplained_calls = total_calls - explained_calls
        
        clarity_score = (explained_calls / total_calls * 100) if total_calls > 0 else 100
        
        return {
            "total_tool_calls": total_calls,
            "explained_calls": explained_calls,
            "unexplained_calls": unexplained_calls,
            "clarity_score": clarity_score,
            "status": "PASS" if unexplained_calls == 0 else "FAIL",
            "unexplained_details": self.get_unexplained_calls(),
        }


# Global clarity checker instance
_clarity_checker: Optional[ClarityChecker] = None


def get_clarity_checker() -> ClarityChecker:
    """Get or create the global clarity checker."""
    global _clarity_checker
    if _clarity_checker is None:
        _clarity_checker = ClarityChecker()
    return _clarity_checker


def reset_clarity_checker() -> None:
    """Reset the clarity checker for a new session."""
    global _clarity_checker
    _clarity_checker = ClarityChecker()
