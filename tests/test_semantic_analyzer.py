"""Tests for semantic analyzer in clarity violation detection.

Tests cover:
- Explicit tool mention detection
- Semantic relationship analysis
- Confidence scoring
- Edge cases and false positives/negatives
"""

from divineos.clarity_enforcement.semantic_analyzer import (
    ConfidenceLevel,
    SemanticAnalyzer,
)


class TestSemanticAnalyzerBasics:
    """Test basic semantic analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test that analyzer initializes correctly."""
        analyzer = SemanticAnalyzer()
        assert analyzer is not None
        assert len(analyzer.TOOL_PURPOSES) > 0
        assert len(analyzer.CONTEXT_INDICATORS) > 0

    def test_explicit_mention_detection(self):
        """Test detection of explicit tool mentions."""
        analyzer = SemanticAnalyzer()

        # Test exact match
        context = ["I need to readFile to check the code"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "readFile", context
        )
        assert is_explained
        assert confidence == ConfidenceLevel.HIGH

    def test_no_context_returns_low_confidence(self):
        """Test that empty context returns low confidence."""
        analyzer = SemanticAnalyzer()

        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship("readFile", [])
        assert not is_explained
        assert confidence == ConfidenceLevel.LOW


class TestSemanticRelationships:
    """Test semantic relationship detection."""

    def test_read_tool_with_read_context(self):
        """Test readFile with 'read' in context."""
        analyzer = SemanticAnalyzer()

        context = ["I need to read the file to understand the structure"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "readFile", context
        )
        assert is_explained
        assert confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_write_tool_with_write_context(self):
        """Test fsWrite with 'write' in context."""
        analyzer = SemanticAnalyzer()

        context = ["I need to write a new configuration file"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "fsWrite", context
        )
        assert is_explained
        assert confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_delete_tool_with_delete_context(self):
        """Test deleteFile with 'delete' in context."""
        analyzer = SemanticAnalyzer()

        context = ["I need to delete the old backup file"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "deleteFile", context
        )
        assert is_explained
        assert confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_execute_tool_with_run_context(self):
        """Test executePwsh with 'run' in context."""
        analyzer = SemanticAnalyzer()

        context = ["Let me run the tests to verify everything works"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "executePwsh", context
        )
        assert is_explained
        assert confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_modify_tool_with_change_context(self):
        """Test strReplace with 'change' in context."""
        analyzer = SemanticAnalyzer()

        context = ["I need to change the error message in the code"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "strReplace", context
        )
        assert is_explained
        assert confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_high_confidence_scoring(self):
        """Test high confidence scoring."""
        analyzer = SemanticAnalyzer()

        context = ["I need to read and check the file content"]
        score = analyzer.get_confidence_score("readFile", context)
        assert score >= 0.6  # At least medium confidence

    def test_low_confidence_scoring(self):
        """Test low confidence scoring."""
        analyzer = SemanticAnalyzer()

        context = ["The weather is nice today"]
        score = analyzer.get_confidence_score("readFile", context)
        assert score < 0.5  # Low confidence

    def test_no_context_zero_score(self):
        """Test that no context gives zero score."""
        analyzer = SemanticAnalyzer()

        score = analyzer.get_confidence_score("readFile", [])
        assert score == 0.0

    def test_score_range(self):
        """Test that scores are in valid range."""
        analyzer = SemanticAnalyzer()

        contexts = [
            [],
            ["hello"],
            ["read the file"],
            ["I need to read and check the file content"],
        ]

        for context in contexts:
            score = analyzer.get_confidence_score("readFile", context)
            assert 0.0 <= score <= 1.0


class TestExplanationDetails:
    """Test detailed explanation generation."""

    def test_explanation_details_structure(self):
        """Test that explanation details have correct structure."""
        analyzer = SemanticAnalyzer()

        context = ["I need to read the file"]
        details = analyzer.get_explanation_details("readFile", context)

        assert "tool_name" in details
        assert "is_explained" in details
        assert "confidence_level" in details
        assert "confidence_score" in details
        assert "reasoning" in details
        assert "context_length" in details
        assert "recent_context" in details

    def test_explanation_details_values(self):
        """Test that explanation details have correct values."""
        analyzer = SemanticAnalyzer()

        context = ["I need to read the file"]
        details = analyzer.get_explanation_details("readFile", context)

        assert details["tool_name"] == "readFile"
        assert isinstance(details["is_explained"], bool)
        assert details["confidence_level"] in ["HIGH", "MEDIUM", "LOW"]
        assert 0.0 <= details["confidence_score"] <= 1.0
        assert isinstance(details["reasoning"], str)
        assert details["context_length"] == 1


class TestEdgeCases:
    """Test edge cases and potential false positives/negatives."""

    def test_unknown_tool(self):
        """Test handling of unknown tools."""
        analyzer = SemanticAnalyzer()

        context = ["I need to do something"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "unknownTool", context
        )
        assert not is_explained
        assert confidence == ConfidenceLevel.LOW

    def test_case_insensitivity(self):
        """Test that analysis is case-insensitive."""
        analyzer = SemanticAnalyzer()

        context1 = ["I need to READ the file"]
        context2 = ["I need to read the file"]

        is_explained1, conf1, _ = analyzer.analyze_semantic_relationship("readFile", context1)
        is_explained2, conf2, _ = analyzer.analyze_semantic_relationship("readFile", context2)

        assert is_explained1 == is_explained2
        assert conf1 == conf2

    def test_multiple_keywords(self):
        """Test detection with multiple relevant keywords."""
        analyzer = SemanticAnalyzer()

        context = ["I need to read and examine the file content to verify it"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "readFile", context
        )
        assert is_explained
        assert confidence == ConfidenceLevel.HIGH  # Multiple keywords = high confidence

    def test_irrelevant_keywords(self):
        """Test that irrelevant keywords don't cause false positives."""
        analyzer = SemanticAnalyzer()

        context = ["The reader was reading a book about files"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "deleteFile", context
        )
        # Should not be explained because "reading" is not about deleting
        assert not is_explained or confidence == ConfidenceLevel.LOW

    def test_recent_context_priority(self):
        """Test that recent context is prioritized."""
        analyzer = SemanticAnalyzer()

        # Old context about reading, recent context about something else
        context = [
            "I need to read the file",
            "The weather is nice",
            "Let me think about this",
        ]

        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "readFile", context
        )
        # Should still find the read keyword in recent context
        assert is_explained or confidence != ConfidenceLevel.HIGH

    def test_long_context(self):
        """Test handling of long context."""
        analyzer = SemanticAnalyzer()

        context = [f"Message {i}" for i in range(100)]
        context[-1] = "I need to read the file"

        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "readFile", context
        )
        assert is_explained

    def test_empty_tool_purposes(self):
        """Test handling of tools with no purposes defined."""
        analyzer = SemanticAnalyzer()

        # Create a tool with no purposes
        context = ["I need to do something"]
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "unknownTool", context
        )
        assert not is_explained
        assert confidence == ConfidenceLevel.LOW


class TestSemanticAnalyzerIntegration:
    """Integration tests for semantic analyzer."""

    def test_full_workflow(self):
        """Test full semantic analysis workflow."""
        analyzer = SemanticAnalyzer()

        # Scenario: User asks to read a file
        context = ["Can you check the error in the log file?"]

        # Analyze
        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "readFile", context
        )

        # Get score
        score = analyzer.get_confidence_score("readFile", context)

        # Get details
        details = analyzer.get_explanation_details("readFile", context)

        # Verify consistency
        assert is_explained == (score > 0.0)
        assert details["is_explained"] == is_explained
        assert details["confidence_score"] == score

    def test_multiple_tools_same_context(self):
        """Test analyzing multiple tools with same context."""
        analyzer = SemanticAnalyzer()

        context = ["I need to read the file and then modify it"]

        read_explained, read_conf, _ = analyzer.analyze_semantic_relationship("readFile", context)
        modify_explained, modify_conf, _ = analyzer.analyze_semantic_relationship(
            "strReplace", context
        )

        # Both should be explained
        assert read_explained
        assert modify_explained

    def test_tool_specific_context(self):
        """Test that tool-specific context is recognized."""
        analyzer = SemanticAnalyzer()

        # Context specific to file operations
        context = ["I need to create a new Python file with the implementation"]

        is_explained, confidence, reasoning = analyzer.analyze_semantic_relationship(
            "fsWrite", context
        )
        assert is_explained
        assert confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
