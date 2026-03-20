"""Violation detection system for clarity enforcement.

Detects unexplained tool calls and determines violation severity.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger


class ViolationSeverity(Enum):
    """Severity level of a clarity violation."""

    LOW = "LOW"  # Common tools used without explanation
    MEDIUM = "MEDIUM"  # Sometimes used without explanation
    HIGH = "HIGH"  # Rarely used without explanation


@dataclass
class ClarityViolation:
    """Information about a clarity violation."""

    tool_name: str
    tool_input: Dict[str, Any]
    severity: ViolationSeverity
    context: List[str] = field(default_factory=list)  # Preceding messages
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str = ""
    user_role: str = "user"
    agent_name: str = "agent"

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary.

        Returns:
            Dictionary representation of violation
        """
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "severity": self.severity.value,
            "context": self.context,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "user_role": self.user_role,
            "agent_name": self.agent_name,
        }


class ViolationDetector:
    """Detects unexplained tool calls."""

    # Tools commonly used without explanation (LOW severity)
    LOW_SEVERITY_TOOLS = {
        "readFile",
        "listDirectory",
        "readCode",
        "getDiagnostics",
    }

    # Tools sometimes used without explanation (MEDIUM severity)
    MEDIUM_SEVERITY_TOOLS = {
        "executeCommand",
        "executePwsh",
        "strReplace",
        "editCode",
    }

    # Tools rarely used without explanation (HIGH severity)
    HIGH_SEVERITY_TOOLS = {
        "deleteFile",
        "fsWrite",
        "fsAppend",
        "semanticRename",
        "smartRelocate",
    }

    def detect_violation(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: List[str],
        session_id: str,
        user_role: str = "user",
        agent_name: str = "agent",
    ) -> Optional[ClarityViolation]:
        """Detect if a tool call is unexplained.

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
            context: Preceding messages (conversation context)
            session_id: Current session ID
            user_role: Role of the user
            agent_name: Name of the agent

        Returns:
            ClarityViolation if unexplained, None if explained
        """
        # Check if tool call is explained in context
        if self._is_explained(tool_name, context):
            logger.debug(f"Tool call {tool_name} is explained")
            return None

        # Determine severity
        severity = self._determine_severity(tool_name)

        # Create violation
        violation = ClarityViolation(
            tool_name=tool_name,
            tool_input=tool_input,
            severity=severity,
            context=context[-5:] if context else [],  # Last 5 messages
            session_id=session_id,
            user_role=user_role,
            agent_name=agent_name,
        )

        logger.warning(f"Clarity violation detected: {tool_name} ({severity.value} severity)")
        return violation

    @staticmethod
    def _is_explained(tool_name: str, context: List[str]) -> bool:
        """Check if tool call is explained in context.

        A tool call is considered explained if:
        - The context contains a clear explanation of why the tool is being called
        - The explanation appears within the last 5 messages

        Args:
            tool_name: Name of the tool
            context: Preceding messages

        Returns:
            True if explained, False otherwise
        """
        if not context:
            return False

        # Simple heuristic: check if recent context mentions the tool or explains reasoning
        recent_context = " ".join(context[-5:]).lower()

        # Check for explicit explanation keywords
        explanation_keywords = [
            "read",
            "check",
            "verify",
            "analyze",
            "examine",
            "review",
            "look at",
            "get",
            "retrieve",
            "fetch",
            "execute",
            "run",
            "modify",
            "change",
            "update",
            "edit",
            "delete",
            "remove",
            "create",
            "write",
            "generate",
            "because",
            "to",
            "in order to",
            "so that",
        ]

        # Check if any explanation keyword appears in recent context
        for keyword in explanation_keywords:
            if keyword in recent_context:
                return True

        return False

    @staticmethod
    def _determine_severity(tool_name: str) -> ViolationSeverity:
        """Determine severity of violation based on tool name.

        Args:
            tool_name: Name of the tool

        Returns:
            ViolationSeverity: Severity level
        """
        if tool_name in ViolationDetector.LOW_SEVERITY_TOOLS:
            return ViolationSeverity.LOW
        elif tool_name in ViolationDetector.MEDIUM_SEVERITY_TOOLS:
            return ViolationSeverity.MEDIUM
        elif tool_name in ViolationDetector.HIGH_SEVERITY_TOOLS:
            return ViolationSeverity.HIGH
        else:
            # Default to MEDIUM for unknown tools
            return ViolationSeverity.MEDIUM


def detect_clarity_violation(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: List[str],
    session_id: str,
) -> Optional[ClarityViolation]:
    """Detect if a tool call violates clarity requirements.

    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters for the tool
        context: Preceding messages (conversation context)
        session_id: Current session ID

    Returns:
        ClarityViolation if unexplained, None if explained
    """
    detector = ViolationDetector()
    return detector.detect_violation(tool_name, tool_input, context, session_id)
