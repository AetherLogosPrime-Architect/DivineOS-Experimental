"""Tests for the ContradictionDetector component."""

from divineos.supersession import (
    Contradiction,
    ContradictionDetector,
    ContradictionSeverity,
)


class TestContradictionDetection:
    """Tests for contradiction detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()

    def test_detect_contradiction_with_different_values(self):
        """Test detecting contradiction when values differ."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
            "source": "initial_calculation",
            "confidence": 0.95,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
            "source": "corrected_calculation",
            "confidence": 0.99,
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is not None
        assert contradiction.fact1_id == "fact_391"
        assert contradiction.fact2_id == "fact_500"
        assert contradiction.fact1_value == 391
        assert contradiction.fact2_value == 500
        assert contradiction.severity == ContradictionSeverity.CRITICAL

    def test_no_contradiction_with_same_values(self):
        """Test no contradiction when values are the same."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }
        fact2 = {
            "id": "fact_391_dup",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:05:00Z",
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is None

    def test_no_contradiction_with_different_fact_types(self):
        """Test no contradiction when fact types differ."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "system_state",
            "fact_key": "17_times_23",
            "value": 500,
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is None

    def test_no_contradiction_with_different_fact_keys(self):
        """Test no contradiction when fact keys differ."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "18_times_24",
            "value": 432,
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is None

    def test_contradiction_stored_in_detector(self):
        """Test that contradictions are stored in the detector."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is not None
        stored = self.detector.get_contradiction("fact_391_fact_500")
        assert stored is not None
        assert stored.fact1_id == "fact_391"


class TestSeverityClassification:
    """Tests for severity classification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()

    def test_critical_severity_for_mathematical_operation(self):
        """Test CRITICAL severity for mathematical operations."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "test",
            "value": 1,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "test",
            "value": 2,
        }

        severity = self.detector.classify_severity(fact1, fact2)

        assert severity == ContradictionSeverity.CRITICAL

    def test_critical_severity_for_security_check(self):
        """Test CRITICAL severity for security checks."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "security_check",
            "fact_key": "test",
            "value": "pass",
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "security_check",
            "fact_key": "test",
            "value": "fail",
        }

        severity = self.detector.classify_severity(fact1, fact2)

        assert severity == ContradictionSeverity.CRITICAL

    def test_high_severity_for_system_state(self):
        """Test HIGH severity for system state."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "system_state",
            "fact_key": "test",
            "value": "running",
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "system_state",
            "fact_key": "test",
            "value": "stopped",
        }

        severity = self.detector.classify_severity(fact1, fact2)

        assert severity == ContradictionSeverity.HIGH

    def test_medium_severity_for_metadata(self):
        """Test MEDIUM severity for metadata."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "metadata",
            "fact_key": "test",
            "value": "value1",
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "metadata",
            "fact_key": "test",
            "value": "value2",
        }

        severity = self.detector.classify_severity(fact1, fact2)

        assert severity == ContradictionSeverity.MEDIUM

    def test_low_severity_for_unknown_type(self):
        """Test LOW severity for unknown fact types."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "unknown_type",
            "fact_key": "test",
            "value": "value1",
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "unknown_type",
            "fact_key": "test",
            "value": "value2",
        }

        severity = self.detector.classify_severity(fact1, fact2)

        assert severity == ContradictionSeverity.LOW


class TestContextCapture:
    """Tests for context capture."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()

    def test_context_capture_includes_both_facts(self):
        """Test that context capture includes both facts."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
            "source": "initial_calculation",
            "confidence": 0.95,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
            "source": "corrected_calculation",
            "confidence": 0.99,
        }

        context = self.detector.capture_context(fact1, fact2)

        assert "fact1" in context
        assert "fact2" in context
        assert context["fact1"]["id"] == "fact_391"
        assert context["fact1"]["value"] == 391
        assert context["fact2"]["id"] == "fact_500"
        assert context["fact2"]["value"] == 500

    def test_context_capture_includes_timestamps(self):
        """Test that context capture includes timestamps."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
            "timestamp": "2026-03-19T17:00:00Z",
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": 2,
            "timestamp": "2026-03-19T17:05:00Z",
        }

        context = self.detector.capture_context(fact1, fact2)

        assert context["fact1"]["timestamp"] == "2026-03-19T17:00:00Z"
        assert context["fact2"]["timestamp"] == "2026-03-19T17:05:00Z"

    def test_context_capture_includes_confidence(self):
        """Test that context capture includes confidence scores."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
            "confidence": 0.95,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": 2,
            "confidence": 0.99,
        }

        context = self.detector.capture_context(fact1, fact2)

        assert context["fact1"]["confidence"] == 0.95
        assert context["fact2"]["confidence"] == 0.99

    def test_context_capture_includes_additional_context(self):
        """Test that context capture includes additional context."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": 2,
        }
        additional = {"reason": "test_reason", "severity": "high"}

        context = self.detector.capture_context(fact1, fact2, additional)

        assert context["additional"]["reason"] == "test_reason"
        assert context["additional"]["severity"] == "high"


class TestContradictionDataStructure:
    """Tests for Contradiction data structure."""

    def test_contradiction_to_dict(self):
        """Test converting contradiction to dictionary."""
        contradiction = Contradiction(
            fact1_id="fact_391",
            fact2_id="fact_500",
            fact1_value=391,
            fact2_value=500,
            severity=ContradictionSeverity.CRITICAL,
            timestamp="2026-03-19T17:05:01Z",
            context={"test": "context"},
        )

        result = contradiction.to_dict()

        assert result["fact1_id"] == "fact_391"
        assert result["fact2_id"] == "fact_500"
        assert result["fact1_value"] == 391
        assert result["fact2_value"] == 500
        assert result["severity"] == "CRITICAL"
        assert result["timestamp"] == "2026-03-19T17:05:01Z"
        assert result["context"] == {"test": "context"}


class TestMultipleContradictions:
    """Tests for handling multiple contradictions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()

    def test_detect_multiple_contradictions(self):
        """Test detecting multiple contradictions."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
        }
        fact3 = {
            "id": "fact_3",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 450,
        }

        contradiction1 = self.detector.detect_contradiction(fact1, fact2)
        contradiction2 = self.detector.detect_contradiction(fact2, fact3)

        assert contradiction1 is not None
        assert contradiction2 is not None

        all_contradictions = self.detector.get_all_contradictions()
        assert len(all_contradictions) == 2

    def test_clear_contradictions(self):
        """Test clearing all contradictions."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
        }

        self.detector.detect_contradiction(fact1, fact2)
        assert len(self.detector.get_all_contradictions()) == 1

        self.detector.clear_contradictions()
        assert len(self.detector.get_all_contradictions()) == 0


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()

    def test_contradiction_with_none_values(self):
        """Test contradiction detection with None values."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": None,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": "something",
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is not None

    def test_contradiction_with_empty_strings(self):
        """Test contradiction detection with empty strings."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": "",
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": "something",
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is not None

    def test_contradiction_with_missing_fields(self):
        """Test contradiction detection with missing fields."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            # Missing value
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": "something",
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        # Should detect contradiction (None != "something")
        assert contradiction is not None

    def test_contradiction_with_complex_values(self):
        """Test contradiction detection with complex values."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": {"nested": "value1"},
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": {"nested": "value2"},
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is not None
