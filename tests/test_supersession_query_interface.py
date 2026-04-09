"""Tests for the QueryInterface component."""

from divineos.supersession import (
    ContradictionDetector,
    FactWithHistory,
    QueryInterface,
    ResolutionEngine,
)


class TestQueryCurrentTruth:
    """Tests for querying current truth."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_query_current_truth_single_fact(self):
        """Test querying current truth with single fact."""
        fact = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }

        self.query.register_fact(fact)

        result = self.query.query_current_truth("mathematical_operation", "17_times_23")

        assert result is not None
        assert result.current_fact["value"] == 391

    def test_query_current_truth_after_supersession(self):
        """Test querying current truth after supersession."""
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

        result = self.query.query_current_truth("mathematical_operation", "17_times_23")

        assert result is not None
        assert result.current_fact["value"] == 500

    def test_query_current_truth_returns_none_for_nonexistent(self):
        """Test that query returns None for nonexistent facts."""
        result = self.query.query_current_truth("nonexistent_type", "nonexistent_key")

        assert result is None


class TestQueryHistory:
    """Tests for querying history."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_query_history_single_fact(self):
        """Test querying history with single fact."""
        fact = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }

        self.query.register_fact(fact)

        results = self.query.query_history("mathematical_operation", "17_times_23")

        assert len(results) == 1
        assert results[0].current_fact["value"] == 391

    def test_query_history_multiple_facts(self):
        """Test querying history with multiple facts."""
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

        results = self.query.query_history("mathematical_operation", "17_times_23")

        assert len(results) == 2

    def test_query_history_sorted_by_timestamp(self):
        """Test that history is sorted by timestamp."""
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

        # Register in reverse order
        self.query.register_fact(fact2)
        self.query.register_fact(fact1)

        results = self.query.query_history("mathematical_operation", "17_times_23")

        # Should be sorted by timestamp
        assert results[0].history[0][0]["value"] == 391
        assert results[0].history[1][0]["value"] == 500


class TestQuerySupersessionChain:
    """Tests for querying supersession chains."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_query_supersession_chain_single_link(self):
        """Test querying supersession chain with single link."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        chain = self.query.query_supersession_chain("fact_391")

        assert len(chain) == 1
        assert chain[0]["superseded_fact_id"] == "fact_391"
        assert chain[0]["superseding_fact_id"] == "fact_500"

    def test_query_supersession_chain_multiple_links(self):
        """Test querying supersession chain with multiple links."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test1"
        )
        self.engine.manual_resolution(
            superseded_fact_id="fact_500", superseding_fact_id="fact_600", reason="test2"
        )

        chain = self.query.query_supersession_chain("fact_391")

        assert len(chain) == 2


class TestQueryContradictions:
    """Tests for querying contradictions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_query_all_contradictions(self):
        """Test querying all contradictions."""
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

        contradictions = self.query.query_contradictions()

        assert len(contradictions) == 1
        assert contradictions[0]["fact1_value"] == 391
        assert contradictions[0]["fact2_value"] == 500

    def test_query_contradictions_by_severity(self):
        """Test querying contradictions filtered by severity."""
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

        critical = self.query.query_contradictions(severity="CRITICAL")

        assert len(critical) == 1
        assert critical[0]["severity"] == "CRITICAL"

    def test_query_contradictions_by_severity_returns_empty(self):
        """Test that querying by non-matching severity returns empty."""
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

        low = self.query.query_contradictions(severity="LOW")

        assert len(low) == 0


class TestFactRegistration:
    """Tests for fact registration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_register_fact(self):
        """Test registering a fact."""
        fact = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
        }

        self.query.register_fact(fact)

        retrieved = self.query.get_fact("fact_1")
        assert retrieved is not None
        assert retrieved["value"] == 1

    def test_get_all_facts(self):
        """Test getting all registered facts."""
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

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        all_facts = self.query.get_all_facts()

        assert len(all_facts) == 2
        assert "fact_1" in all_facts
        assert "fact_2" in all_facts


class TestCurrentTruthChecking:
    """Tests for checking if a fact is current truth."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_is_current_truth_for_unsuperseded_fact(self):
        """Test that unsuperseded fact is current truth."""
        fact = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
        }

        self.query.register_fact(fact)

        assert self.query.is_current_truth("fact_1")

    def test_is_current_truth_for_superseded_fact(self):
        """Test that superseded fact is not current truth."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_1", superseding_fact_id="fact_2", reason="test"
        )

        assert not self.query.is_current_truth("fact_1")
        assert self.query.is_current_truth("fact_2")


class TestGetSupersedingFact:
    """Tests for getting superseding fact."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_get_superseding_fact(self):
        """Test getting the fact that supersedes another."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "test",
            "fact_key": "test",
            "value": 391,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "test",
            "fact_key": "test",
            "value": 500,
        }

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        superseding = self.query.get_superseding_fact("fact_391")

        assert superseding is not None
        assert superseding["value"] == 500


class TestQueryByType:
    """Tests for querying facts by type."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_query_by_type(self):
        """Test querying facts by type."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "mathematical_operation",
            "fact_key": "test",
            "value": 1,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "system_state",
            "fact_key": "test",
            "value": 2,
        }

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        math_facts = self.query.query_by_type("mathematical_operation")

        assert len(math_facts) == 1
        assert math_facts[0]["id"] == "fact_1"

    def test_query_current_by_type(self):
        """Test querying current facts by type."""
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

        self.query.register_fact(fact1)
        self.query.register_fact(fact2)

        self.engine.manual_resolution(
            superseded_fact_id="fact_1", superseding_fact_id="fact_2", reason="test"
        )

        current_math_facts = self.query.query_current_by_type("mathematical_operation")

        assert len(current_math_facts) == 1
        assert current_math_facts[0]["id"] == "fact_2"


class TestFactWithHistoryDataStructure:
    """Tests for FactWithHistory data structure."""

    def test_fact_with_history_to_dict(self):
        """Test converting FactWithHistory to dictionary."""
        current_fact = {
            "id": "fact_500",
            "value": 500,
        }
        superseded_facts = [
            {
                "id": "fact_391",
                "value": 391,
            }
        ]
        supersession_events = [
            {
                "event_id": "event_1",
                "reason": "newer_fact",
            }
        ]
        history = [
            ({"id": "fact_391", "value": 391}, "2026-03-19T17:00:00Z"),
            ({"id": "fact_500", "value": 500}, "2026-03-19T17:05:00Z"),
        ]

        fact_with_history = FactWithHistory(
            current_fact=current_fact,
            superseded_facts=superseded_facts,
            supersession_events=supersession_events,
            history=history,
        )

        result = fact_with_history.to_dict()

        assert result["current_fact"]["value"] == 500
        assert len(result["superseded_facts"]) == 1
        assert len(result["supersession_events"]) == 1
        assert len(result["history"]) == 2


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.query = QueryInterface(self.engine, self.detector)

    def test_query_with_no_facts_registered(self):
        """Test querying when no facts are registered."""
        result = self.query.query_current_truth("test", "test")

        assert result is None

    def test_query_history_with_no_facts(self):
        """Test querying history when no facts exist."""
        results = self.query.query_history("test", "test")

        assert len(results) == 0

    def test_query_contradictions_with_none(self):
        """Test querying contradictions when none exist."""
        contradictions = self.query.query_contradictions()

        assert len(contradictions) == 0
