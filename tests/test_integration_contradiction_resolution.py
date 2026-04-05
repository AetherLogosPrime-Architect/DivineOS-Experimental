"""Integration tests for Contradiction Detection + Resolution.

Tests that contradictions are detected and resolved correctly, establishing
"current truth" for facts.

Property 2: Contradictions detected and resolved
- For any two facts with the same type and key but different values, the system
  SHALL detect the contradiction and apply a resolution strategy to establish
  which fact is current.

Property 3: Supersession chain consistency
- For any fact that has been superseded, querying the system SHALL return the
  current (superseding) fact, not the superseded one. The supersession chain
  SHALL be transitive (if A→B and B→C, then A→C).
"""

from divineos.supersession.contradiction_detector import (
    ContradictionDetector,
    ContradictionSeverity,
)
from divineos.supersession.resolution_engine import ResolutionEngine
from divineos.supersession.query_interface import QueryInterface
from divineos.core.ledger import get_ledger


class TestContradictionDetectionResolution:
    """Test contradiction detection and resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()
        self.engine = ResolutionEngine()
        self.ledger = get_ledger()
        self.query = QueryInterface(self.engine, self.detector)

    def test_contradiction_detected_and_resolved(self):
        """
        Test that contradictions are detected and resolved.

        Scenario:
        1. Store fact: 17 × 23 = 391
        2. Store fact: 17 × 23 = 392
        3. Detect contradiction
        4. Resolve contradiction
        5. Query returns correct fact

        Property 2: Contradictions detected and resolved
        """
        # Create two contradicting facts
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 392,
            "timestamp": "2026-03-19T10:01:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        # Store facts
        self.ledger.store_fact(fact1)
        self.ledger.store_fact(fact2)

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        assert contradiction is not None, "Contradiction should be detected"
        assert contradiction.severity == ContradictionSeverity.CRITICAL

        # Resolve contradiction
        resolution = self.engine.resolve_contradiction(contradiction)
        assert resolution is not None, "Contradiction should be resolved"
        assert resolution.superseding_fact_id == "fact_2", "Newer fact should win"
        assert resolution.superseded_fact_id == "fact_1", "Older fact should lose"

    def test_query_returns_current_fact(self):
        """
        Test that queries return the current (superseding) fact.

        Scenario:
        1. Store two contradicting facts
        2. Resolve contradiction
        3. Query should return the current fact

        Property 3: Supersession chain consistency
        """
        # Create contradicting facts
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 392,
            "timestamp": "2026-03-19T10:01:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        # Register facts with query interface
        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        # Register with engine
        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction)

        # Query should return current fact
        current = self.query.query_current_truth("mathematical_operation", "17_times_23")
        assert current is not None, "Query should return current fact"
        assert current.current_fact["id"] == "fact_2", "Query should return newer fact"
        assert current.current_fact["value"] == 392, "Query should return correct value"

    def test_supersession_chain_consistency(self):
        """
        Test that supersession chains are consistent and transitive.

        Scenario:
        1. Store three facts: A, B, C (each newer than previous)
        2. Resolve all contradictions
        3. Query should return C (newest)
        4. Supersession chain should be A→B→C

        Property 3: Supersession chain consistency
        """
        # Create three facts (each newer)
        facts = [
            {
                "id": "fact_1",
                "fact_type": "system_state",
                "fact_key": "deployment_status",
                "value": "pending",
                "timestamp": "2026-03-19T10:00:00Z",
                "source": "SYSTEM",
                "confidence": 0.8,
            },
            {
                "id": "fact_2",
                "fact_type": "system_state",
                "fact_key": "deployment_status",
                "value": "in_progress",
                "timestamp": "2026-03-19T10:05:00Z",
                "source": "SYSTEM",
                "confidence": 0.9,
            },
            {
                "id": "fact_3",
                "fact_type": "system_state",
                "fact_key": "deployment_status",
                "value": "completed",
                "timestamp": "2026-03-19T10:10:00Z",
                "source": "SYSTEM",
                "confidence": 1.0,
            },
        ]

        # Register all facts
        for fact in facts:
            self.query.register_fact(fact)
            self.engine.register_fact(fact)

        # Detect and resolve all contradictions
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                contradiction = self.detector.detect_contradiction(facts[i], facts[j])
                if contradiction:
                    self.engine.resolve_contradiction(contradiction)

        # Query should return newest fact
        current = self.query.query_current_truth("system_state", "deployment_status")
        assert current is not None
        assert current.current_fact["id"] == "fact_3"
        assert current.current_fact["value"] == "completed"

        # Verify supersession chain for fact_1
        chain = self.engine.get_supersession_chain("fact_1")
        assert len(chain) >= 1, "Should have supersession events"

    def test_supersession_event_created(self):
        """
        Test that SUPERSESSION events are created when facts are resolved.

        Scenario:
        1. Store two contradicting facts
        2. Resolve contradiction
        3. Engine should contain SUPERSESSION event
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 392,
            "timestamp": "2026-03-19T10:01:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        # Register facts
        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        resolution = self.engine.resolve_contradiction(contradiction)

        # Check for SUPERSESSION event
        assert resolution is not None, "SUPERSESSION event should be created"
        assert resolution.superseded_fact_id == "fact_1"
        assert resolution.superseding_fact_id == "fact_2"

        # Verify event is stored in engine
        all_events = self.engine.get_all_supersession_events()
        assert len(all_events) > 0, "Engine should store supersession events"


class TestContradictionEdgeCases:
    """Test edge cases in contradiction detection and resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()
        self.engine = ResolutionEngine()
        self.ledger = get_ledger()
        self.query = QueryInterface(self.engine, self.detector)

    def test_no_contradiction_same_values(self):
        """
        Test that identical facts don't create contradictions.

        Scenario:
        1. Store two facts with same value
        2. No contradiction should be detected
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:01:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        assert contradiction is None, "No contradiction for identical values"

    def test_no_contradiction_different_keys(self):
        """
        Test that facts with different keys don't contradict.

        Scenario:
        1. Store two facts with different keys
        2. No contradiction should be detected
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "18_times_24",
            "value": 432,
            "timestamp": "2026-03-19T10:01:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        assert contradiction is None, "No contradiction for different keys"

    def test_severity_classification(self):
        """
        Test that contradictions are classified by severity.

        Scenario:
        1. Create contradictions of different types
        2. Verify severity is classified correctly
        """
        # CRITICAL: Mathematical operation
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T10:00:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 392,
            "timestamp": "2026-03-19T10:01:00Z",
            "source": "DEMONSTRATED",
            "confidence": 1.0,
        }

        contradiction = self.detector.detect_contradiction(fact1, fact2)
        assert contradiction.severity == ContradictionSeverity.CRITICAL

    def test_multiple_contradictions_resolved(self):
        """
        Test that multiple contradictions can be resolved.

        Scenario:
        1. Store multiple facts with contradictions
        2. Resolve all contradictions
        3. Query should return correct current facts
        """
        # Create multiple contradicting fact pairs
        fact_pairs = [
            (
                {
                    "id": "fact_1a",
                    "fact_type": "mathematical_operation",
                    "fact_key": "17_times_23",
                    "value": 391,
                    "timestamp": "2026-03-19T10:00:00Z",
                    "source": "DEMONSTRATED",
                    "confidence": 1.0,
                },
                {
                    "id": "fact_1b",
                    "fact_type": "mathematical_operation",
                    "fact_key": "17_times_23",
                    "value": 392,
                    "timestamp": "2026-03-19T10:01:00Z",
                    "source": "DEMONSTRATED",
                    "confidence": 1.0,
                },
            ),
            (
                {
                    "id": "fact_2a",
                    "fact_type": "system_state",
                    "fact_key": "status",
                    "value": "pending",
                    "timestamp": "2026-03-19T10:00:00Z",
                    "source": "SYSTEM",
                    "confidence": 0.8,
                },
                {
                    "id": "fact_2b",
                    "fact_type": "system_state",
                    "fact_key": "status",
                    "value": "completed",
                    "timestamp": "2026-03-19T10:01:00Z",
                    "source": "SYSTEM",
                    "confidence": 1.0,
                },
            ),
        ]

        # Store and resolve all facts
        for fact1, fact2 in fact_pairs:
            self.query.register_fact(fact1)
            self.query.register_fact(fact2)
            self.engine.register_fact(fact1)
            self.engine.register_fact(fact2)

            contradiction = self.detector.detect_contradiction(fact1, fact2)
            if contradiction:
                self.engine.resolve_contradiction(contradiction)

        # Verify all current facts are correct
        current_1 = self.query.query_current_truth("mathematical_operation", "17_times_23")
        assert current_1 is not None
        assert current_1.current_fact["id"] == "fact_1b"

        current_2 = self.query.query_current_truth("system_state", "status")
        assert current_2 is not None
        assert current_2.current_fact["id"] == "fact_2b"
