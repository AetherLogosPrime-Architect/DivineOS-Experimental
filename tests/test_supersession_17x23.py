"""Canonical 17×23 conflict acceptance test for supersession system."""

from divineos.supersession import (
    ContradictionDetector,
    QueryInterface,
    ResolutionEngine,
    ResolutionStrategy,
)


class Test17x23Conflict:
    """Canonical acceptance test for 17×23 conflict."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ContradictionDetector()
        self.engine = ResolutionEngine()
        self.query = QueryInterface(self.engine, self.detector)

    def test_17x23_conflict_full_scenario(self):
        """Test the complete 17×23 conflict scenario.

        This is the canonical acceptance test for the supersession system.
        It tests:
        1. Ingesting two contradictory facts
        2. Detecting the contradiction
        3. Resolving the contradiction
        4. Querying the current truth
        5. Verifying the history is preserved
        """
        # Step 1: Ingest first fact (incorrect value)
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
            "source": "initial_calculation",
            "confidence": 0.95,
        }

        self.query.register_fact(fact1)

        # Verify fact is registered
        assert self.query.get_fact("fact_391") is not None
        assert self.query.is_current_truth("fact_391")

        # Step 2: Ingest second fact (correct value)
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
            "source": "corrected_calculation",
            "confidence": 0.99,
        }

        self.query.register_fact(fact2)

        # Verify both facts are registered
        assert self.query.get_fact("fact_500") is not None

        # Step 3: Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)

        assert contradiction is not None
        assert contradiction.fact1_id == "fact_391"
        assert contradiction.fact2_id == "fact_500"
        assert contradiction.fact1_value == 391
        assert contradiction.fact2_value == 500
        assert contradiction.severity.value == "CRITICAL"

        # Step 4: Resolve contradiction
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        assert supersession is not None
        assert supersession.superseded_fact_id == "fact_391"
        assert supersession.superseding_fact_id == "fact_500"
        assert supersession.reason == "newer_fact"

        # Step 5: Verify supersession tracking
        assert self.engine.is_superseded("fact_391")
        assert not self.engine.is_superseded("fact_500")
        assert self.engine.get_superseding_fact("fact_391") == "fact_500"

        # Step 6: Query current truth
        current_truth = self.query.query_current_truth("mathematical_operation", "17_times_23")

        assert current_truth is not None
        assert current_truth.current_fact["value"] == 500
        assert current_truth.current_fact["id"] == "fact_500"

        # Step 7: Verify superseded facts are tracked
        assert len(current_truth.superseded_facts) == 1
        assert current_truth.superseded_facts[0]["value"] == 391

        # Step 8: Verify supersession events are tracked
        assert len(current_truth.supersession_events) == 1
        assert current_truth.supersession_events[0]["reason"] == "newer_fact"

        # Step 9: Verify history is preserved
        assert len(current_truth.history) == 2
        assert current_truth.history[0][0]["value"] == 391
        assert current_truth.history[1][0]["value"] == 500

        # Step 10: Query supersession chain
        chain = self.query.query_supersession_chain("fact_391")

        assert len(chain) == 1
        assert chain[0]["superseded_fact_id"] == "fact_391"
        assert chain[0]["superseding_fact_id"] == "fact_500"

    def test_17x23_conflict_query_history(self):
        """Test querying history for 17×23 conflict."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
        }

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        contradiction = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction)

        # Query history
        history = self.query.query_history("mathematical_operation", "17_times_23")

        assert len(history) == 2

        # First entry should be the old fact
        assert history[0].current_fact["value"] == 391

        # Second entry should be the new fact
        assert history[1].current_fact["value"] == 500

    def test_17x23_conflict_by_higher_confidence(self):
        """Test 17×23 conflict resolution by higher confidence."""
        # Newer fact has lower confidence
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
            "confidence": 0.99,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
            "confidence": 0.50,
        }

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        # Resolve by higher confidence
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.HIGHER_CONFIDENCE
        )

        # Should choose fact1 (higher confidence)
        assert supersession.superseded_fact_id == "fact_500"
        assert supersession.superseding_fact_id == "fact_391"

        # Query current truth
        current_truth = self.query.query_current_truth("mathematical_operation", "17_times_23")

        assert current_truth.current_fact["value"] == 391

    def test_17x23_conflict_manual_resolution(self):
        """Test 17×23 conflict with manual resolution."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
        }

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        # Manually resolve (user override)
        supersession = self.engine.manual_resolution(
            superseded_fact_id="fact_500", superseding_fact_id="fact_391", reason="user_override"
        )

        assert supersession.reason == "user_override"

        # Query current truth
        current_truth = self.query.query_current_truth("mathematical_operation", "17_times_23")

        assert current_truth.current_fact["value"] == 391

    def test_17x23_conflict_multiple_resolutions(self):
        """Test 17×23 conflict with multiple resolutions."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
        }
        fact3 = {
            "id": "fact_391_corrected",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:10:00Z",
        }

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)
        self.query.register_fact(fact3)

        # First resolution
        contradiction1 = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction1)

        # Second resolution
        contradiction2 = self.detector.detect_contradiction(fact2, fact3)
        self.engine.resolve_contradiction(contradiction2)

        # Query current truth
        current_truth = self.query.query_current_truth("mathematical_operation", "17_times_23")

        # Should be the newest fact
        assert current_truth.current_fact["value"] == 391
        assert current_truth.current_fact["id"] == "fact_391_corrected"

        # Query supersession chain
        chain = self.query.query_supersession_chain("fact_391")

        # Should have two links (391 -> 500 -> 391_corrected)
        assert len(chain) == 2
        assert chain[0]["superseded_fact_id"] == "fact_391"
        assert chain[0]["superseding_fact_id"] == "fact_500"
        assert chain[1]["superseded_fact_id"] == "fact_500"
        assert chain[1]["superseding_fact_id"] == "fact_391_corrected"

        chain2 = self.query.query_supersession_chain("fact_500")

        # Should have one link (500 -> 391_corrected)
        assert len(chain2) == 1
        assert chain2[0]["superseded_fact_id"] == "fact_500"
        assert chain2[0]["superseding_fact_id"] == "fact_391_corrected"

    def test_17x23_conflict_contradictions_query(self):
        """Test querying contradictions for 17×23 conflict."""
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

        self.detector.detect_contradiction(fact1, fact2)

        # Query contradictions
        contradictions = self.query.query_contradictions()

        assert len(contradictions) == 1
        assert contradictions[0]["fact1_value"] == 391
        assert contradictions[0]["fact2_value"] == 500
        assert contradictions[0]["severity"] == "CRITICAL"

    def test_17x23_conflict_context_preservation(self):
        """Test that context is preserved in 17×23 conflict."""
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

        # Verify context is captured
        assert contradiction.context["fact1"]["source"] == "initial_calculation"
        assert contradiction.context["fact1"]["confidence"] == 0.95
        assert contradiction.context["fact2"]["source"] == "corrected_calculation"
        assert contradiction.context["fact2"]["confidence"] == 0.99
