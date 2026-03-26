"""Semantic analysis for clarity violation detection.

Analyzes the relationship between tool names and context to determine
if a tool call is semantically explained by the surrounding context.
"""

from typing import Dict, List, Tuple, Any
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence level for semantic analysis results."""

    HIGH = "HIGH"  # Strong semantic relationship detected
    MEDIUM = "MEDIUM"  # Moderate semantic relationship detected
    LOW = "LOW"  # Weak or no semantic relationship detected


class SemanticAnalyzer:
    """Analyzes semantic relationships between tools and context."""

    # Tool purpose mappings (Claude Code + legacy VS Code/Kiro names)
    TOOL_PURPOSES: Dict[str, List[str]] = {
        # Claude Code tools
        "Read": [
            "read",
            "view",
            "check",
            "examine",
            "look at",
            "see",
            "get",
            "retrieve",
            "fetch",
            "content",
        ],
        "Edit": ["edit", "modify", "change", "update", "fix", "refactor", "replace", "correct"],
        "Write": ["write", "create", "generate", "make", "new", "file"],
        "Bash": ["run", "execute", "test", "build", "compile", "check", "command", "shell"],
        "Glob": ["find", "search", "list", "files", "pattern", "match"],
        "Grep": ["search", "find", "grep", "content", "pattern", "match"],
        "Agent": ["delegate", "research", "explore", "investigate"],
        # Legacy read tools
        "readFile": [
            "read",
            "view",
            "check",
            "examine",
            "look at",
            "see",
            "get",
            "retrieve",
            "fetch",
            "content",
        ],
        "readCode": [
            "read",
            "view",
            "check",
            "examine",
            "look at",
            "see",
            "get",
            "retrieve",
            "fetch",
            "code",
        ],
        "listDirectory": [
            "list",
            "show",
            "view",
            "check",
            "examine",
            "directory",
            "folder",
            "files",
        ],
        "getDiagnostics": ["check", "diagnose", "error", "problem", "issue", "validate", "verify"],
        # Legacy write tools
        "fsWrite": ["write", "create", "generate", "make", "new", "file"],
        "fsAppend": ["append", "add", "extend", "update", "modify"],
        "strReplace": ["replace", "change", "modify", "update", "fix", "correct"],
        "editCode": ["edit", "modify", "change", "update", "fix", "refactor"],
        # Legacy other tools
        "deleteFile": ["delete", "remove", "clean", "clear"],
        "semanticRename": ["rename", "change name", "refactor"],
        "smartRelocate": ["move", "relocate", "reorganize", "refactor"],
        "executePwsh": ["run", "execute", "test", "build", "compile", "check"],
        "executeCommand": ["run", "execute", "test", "build", "compile", "check"],
    }

    # Context keywords that indicate tool usage
    CONTEXT_INDICATORS: Dict[str, List[str]] = {
        "read": [
            "read",
            "check",
            "view",
            "examine",
            "look",
            "see",
            "get",
            "retrieve",
            "fetch",
            "content",
            "file",
        ],
        "write": ["write", "create", "generate", "make", "new", "file", "add", "append"],
        "delete": ["delete", "remove", "clean", "clear"],
        "modify": ["modify", "change", "update", "fix", "refactor", "replace"],
        "execute": ["run", "execute", "test", "build", "compile", "check"],
        "analyze": ["analyze", "check", "verify", "validate", "diagnose", "examine"],
    }

    def analyze_semantic_relationship(
        self,
        tool_name: str,
        context: List[str],
    ) -> Tuple[bool, ConfidenceLevel, str]:
        """Analyze semantic relationship between tool and context.

        Args:
            tool_name: Name of the tool being called
            context: Preceding messages (conversation context)

        Returns:
            Tuple of (is_explained, confidence_level, reasoning)
        """
        if not context:
            return False, ConfidenceLevel.LOW, "No context available"

        # Get tool purposes
        tool_purposes = self.TOOL_PURPOSES.get(tool_name, [])
        if not tool_purposes:
            return False, ConfidenceLevel.LOW, f"Unknown tool: {tool_name}"

        # Analyze context
        recent_context = " ".join(context[-5:]).lower()

        # Check for explicit tool mentions
        explicit_mention = self._check_explicit_mention(tool_name, recent_context)
        if explicit_mention:
            return True, ConfidenceLevel.HIGH, f"Tool explicitly mentioned: {tool_name}"

        # Check for semantic relationships
        semantic_match, confidence, reasoning = self._check_semantic_relationship(
            tool_name, tool_purposes, recent_context
        )

        return semantic_match, confidence, reasoning

    @staticmethod
    def _check_explicit_mention(tool_name: str, context: str) -> bool:
        """Check if tool is explicitly mentioned in context.

        Args:
            tool_name: Name of the tool
            context: Context text (lowercase)

        Returns:
            True if tool is mentioned, False otherwise
        """
        # Check for exact tool name
        if tool_name.lower() in context:
            return True

        # Check for common variations
        variations = [
            tool_name.lower(),
            tool_name.lower().replace("_", " "),
            tool_name.lower().replace("_", "-"),
        ]

        for variation in variations:
            if variation in context:
                return True

        return False

    @staticmethod
    def _check_semantic_relationship(
        tool_name: str,
        tool_purposes: List[str],
        context: str,
    ) -> Tuple[bool, ConfidenceLevel, str]:
        """Check for semantic relationship between tool and context.

        Args:
            tool_name: Name of the tool
            tool_purposes: List of purpose keywords for the tool
            context: Context text (lowercase)

        Returns:
            Tuple of (is_explained, confidence_level, reasoning)
        """
        # Count purpose keyword matches
        matches = 0
        matched_keywords = []

        for purpose in tool_purposes:
            if purpose in context:
                matches += 1
                matched_keywords.append(purpose)

        # Determine confidence based on match count
        if matches >= 2:
            return (
                True,
                ConfidenceLevel.HIGH,
                f"Strong semantic match: {', '.join(matched_keywords)}",
            )
        elif matches == 1:
            return True, ConfidenceLevel.MEDIUM, f"Moderate semantic match: {matched_keywords[0]}"
        else:
            return False, ConfidenceLevel.LOW, "No semantic relationship detected"

    def get_confidence_score(
        self,
        tool_name: str,
        context: List[str],
    ) -> float:
        """Get a confidence score (0.0-1.0) for semantic explanation.

        Args:
            tool_name: Name of the tool
            context: Preceding messages

        Returns:
            Confidence score from 0.0 (not explained) to 1.0 (fully explained)
        """
        if not context:
            return 0.0

        is_explained, confidence_level, _ = self.analyze_semantic_relationship(tool_name, context)

        if not is_explained:
            return 0.0

        # Map confidence levels to scores
        confidence_scores = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.3,
        }

        return confidence_scores.get(confidence_level, 0.0)

    def get_explanation_details(
        self,
        tool_name: str,
        context: List[str],
    ) -> Dict[str, Any]:
        """Get detailed explanation of semantic analysis.

        Args:
            tool_name: Name of the tool
            context: Preceding messages

        Returns:
            Dictionary with analysis details
        """
        is_explained, confidence_level, reasoning = self.analyze_semantic_relationship(
            tool_name, context
        )

        confidence_score = self.get_confidence_score(tool_name, context)

        return {
            "tool_name": tool_name,
            "is_explained": is_explained,
            "confidence_level": confidence_level.value,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
            "context_length": len(context),
            "recent_context": " ".join(context[-3:]) if context else "",
        }
