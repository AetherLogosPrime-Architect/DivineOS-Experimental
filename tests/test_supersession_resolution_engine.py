"""Tests for the ResolutionEngine component."""

from divineos.supersession import (
    ResolutionEngine,
    ResolutionStrategy,
    ContradictionDetector,
)


class TestResolutionByNewerFact:
    """Tests for resolution by newer fact."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()

    def test_resolve_by_newer_fact(self):
        """Test resolving contradiction by choosing newer fact."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
            "confidence": 0.95,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
            "confidence": 0.99,
        }

        # Register facts
        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Create contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)

        # Resolve
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        assert supersession is not None
        assert supersession.superseded_fact_id == "fact_391"
        assert supersession.superseding_fact_id == "fact_500"
        assert supersession.reason == "newer_fact"

    def test_newer_fact_marked_as_superseded(self):
        """Test that older fact is marked as superseded."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "test",
            "fact_key": "test",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "test",
            "fact_key": "test",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        contradiction = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction, ResolutionStrategy.NEWER_FACT)

        assert self.engine.is_superseded("fact_391")
        assert not self.engine.is_superseded("fact_500")


class TestResolutionByHigherConfidence:
    """Tests for resolution by higher confidence."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()

    def test_resolve_by_higher_confidence(self):
        """Test resolving contradiction by choosing higher confidence."""
        fact1 = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
            "confidence": 0.95,
        }
        fact2 = {
            "id": "fact_500",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 500,
            "timestamp": "2026-03-19T17:05:00Z",
            "confidence": 0.99,
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.HIGHER_CONFIDENCE
        )

        assert supersession is not None
        assert supersession.superseded_fact_id == "fact_391"
        assert supersession.superseding_fact_id == "fact_500"
        assert supersession.reason == "higher_confidence"

    def test_higher_confidence_chooses_correct_fact(self):
        """Test that higher confidence strategy chooses fact with higher confidence."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
            "timestamp": "2026-03-19T17:05:00Z",
            "confidence": 0.99,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": 2,
            "timestamp": "2026-03-19T17:00:00Z",
            "confidence": 0.50,
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        contradiction = self.detector.detect_contradiction(fact1, fact2)

        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.HIGHER_CONFIDENCE
        )

        assert supersession.superseded_fact_id == "fact_2"
        assert supersession.superseding_fact_id == "fact_1"


class TestManualResolution:
    """Tests for manual resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()

    def test_manual_resolution(self):
        """Test manual resolution of contradiction."""
        supersession = self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="user_override"
        )

        assert supersession is not None
        assert supersession.superseded_fact_id == "fact_391"
        assert supersession.superseding_fact_id == "fact_500"
        assert supersession.reason == "user_override"

    def test_manual_resolution_creates_event(self):
        """Test that manual resolution creates a supersession event."""
        supersession = self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="correction"
        )

        stored = self.engine.get_supersession_event(supersession.event_id)
        assert stored is not None
        assert stored.reason == "correction"


class TestCurrentTruth:
    """Tests for getting current truth."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()

    def test_get_current_truth_after_resolution(self):
        """Test getting current truth after resolution."""
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

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        contradiction = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction)

        current = self.engine.get_current_truth("mathematical_operation", "17_times_23")

        assert current is not None
        assert current["value"] == 500
        assert current["id"] == "fact_500"

    def test_get_current_truth_returns_none_for_nonexistent(self):
        """Test that get_current_truth returns None for nonexistent facts."""
        current = self.engine.get_current_truth("nonexistent_type", "nonexistent_key")

        assert current is None


class TestSupersessionEvents:
    """Tests for supersession events."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()

    def test_supersession_event_has_hash(self):
        """Test that supersession events have a hash."""
        supersession = self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        assert supersession.hash is not None
        assert len(supersession.hash) == 64  # SHA256 hex digest

    def test_supersession_event_has_timestamp(self):
        """Test that supersession events have a timestamp."""
        supersession = self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        assert supersession.timestamp is not None
        assert "Z" in supersession.timestamp

    def test_supersession_event_to_dict(self):
        """Test converting supersession event to dictionary."""
        supersession = self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        result = supersession.to_dict()

        assert result["superseded_fact_id"] == "fact_391"
        assert result["superseding_fact_id"] == "fact_500"
        assert result["reason"] == "test"
        assert "hash" in result
        assert "timestamp" in result


class TestSupersessionChain:
    """Tests for supersession chains."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()

    def test_get_supersession_chain_single_link(self):
        """Test getting supersession chain with single link."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        chain = self.engine.get_supersession_chain("fact_391")

        assert len(chain) == 1
        assert chain[0].superseded_fact_id == "fact_391"
        assert chain[0].superseding_fact_id == "fact_500"

    def test_get_supersession_chain_multiple_links(self):
        """Test getting supersession chain with multiple links."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test1"
        )
        self.engine.manual_resolution(
            superseded_fact_id="fact_500", superseding_fact_id="fact_600", reason="test2"
        )

        chain = self.engine.get_supersession_chain("fact_391")

        assert len(chain) == 2
        assert chain[0].superseded_fact_id == "fact_391"
        assert chain[1].superseded_fact_id == "fact_500"

    def test_get_supersession_chain_empty_for_current_fact(self):
        """Test that current fact has empty supersession chain."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        chain = self.engine.get_supersession_chain("fact_500")

        assert len(chain) == 0


class TestSupersededByLinks:
    """Tests for superseded_by links."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()

    def test_get_superseding_fact(self):
        """Test getting the fact that supersedes another."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        superseding_id = self.engine.get_superseding_fact("fact_391")

        assert superseding_id == "fact_500"

    def test_get_superseding_fact_returns_none_for_current(self):
        """Test that current fact returns None for superseding fact."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500", reason="test"
        )

        superseding_id = self.engine.get_superseding_fact("fact_500")

        assert superseding_id is None


class TestFactRegistration:
    """Tests for fact registration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()

    def test_register_fact(self):
        """Test registering a fact."""
        fact = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
        }

        self.engine.register_fact(fact)

        assert "fact_1" in self.engine.facts
        assert self.engine.facts["fact_1"]["value"] == 1


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()

    def test_resolution_with_equal_confidence(self):
        """Test resolution when confidence is equal."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
            "timestamp": "2026-03-19T17:00:00Z",
            "confidence": 0.95,
        }
        fact2 = {
            "id": "fact_2",
            "fact_type": "test",
            "fact_key": "test",
            "value": 2,
            "timestamp": "2026-03-19T17:05:00Z",
            "confidence": 0.95,
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        detector = ContradictionDetector()
        contradiction = detector.detect_contradiction(fact1, fact2)

        # Should fall back to newer fact
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.HIGHER_CONFIDENCE
        )

        assert supersession.superseded_fact_id == "fact_1"
        assert supersession.superseding_fact_id == "fact_2"

    def test_multiple_resolutions_same_fact(self):
        """Test multiple resolutions for the same fact."""
        self.engine.manual_resolution(
            superseded_fact_id="fact_1", superseding_fact_id="fact_2", reason="reason1"
        )
        self.engine.manual_resolution(
            superseded_fact_id="fact_2", superseding_fact_id="fact_3", reason="reason2"
        )

        all_events = self.engine.get_all_supersession_events()

        assert len(all_events) == 2
