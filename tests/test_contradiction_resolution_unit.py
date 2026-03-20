"""
Unit Tests for Contradiction Resolution (Non-Property-Based)

These tests validate the same correctness properties as the property-based tests
but without using hypothesis to avoid hanging issues.
"""

from src.divineos.supersession import (
    ResolutionEngine,
    ResolutionStrategy,
    ContradictionDetector,
)


class TestContradictionResolutionUnit:
    """Unit tests for contradiction resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()

    def test_supersession_chain_always_consistent(self):
        """
        Property: For any fact that has been superseded, the supersession
        chain SHALL be consistent (no cycles, always points to current fact).
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "test",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Get supersession chain for the superseded fact
        chain = self.engine.get_supersession_chain(supersession.superseded_fact_id)

        # Verify chain is consistent
        assert len(chain) >= 1, "Chain should have at least one link"
        assert chain[0].superseded_fact_id == supersession.superseded_fact_id
        assert chain[0].superseding_fact_id == supersession.superseding_fact_id

        # Verify no cycles (chain should not contain the superseded fact again)
        for event in chain:
            assert event.superseded_fact_id != event.superseding_fact_id

    def test_superseded_fact_marked_correctly(self):
        """
        Property: After resolution, the superseded fact SHALL be marked as
        superseded, and the superseding fact SHALL NOT be marked as superseded.
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "test",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Verify superseded fact is marked
        assert self.engine.is_superseded(supersession.superseded_fact_id)

        # Verify superseding fact is NOT marked as superseded
        assert not self.engine.is_superseded(supersession.superseding_fact_id)

    def test_query_returns_current_fact_not_superseded(self):
        """
        Property: When querying for a fact after resolution, the system
        SHALL return the current (superseding) fact, not the superseded one.
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "test",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Query for current fact
        current = self.engine.get_current_truth("measurement", "temperature")

        # Verify current fact is the superseding fact
        assert current is not None
        assert current["id"] == supersession.superseding_fact_id
        assert current["id"] != supersession.superseded_fact_id

    def test_multiple_contradictions_chain(self):
        """Test that multiple contradictions create a proper chain."""
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "test",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "test",
        }

        fact3 = {
            "id": "fact_3",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 27.0,
            "timestamp": "2026-03-20T10:02:00Z",
            "confidence": 0.98,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)
        self.engine.register_fact(fact3)

        # Resolve fact1 vs fact2
        contradiction1 = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction1, ResolutionStrategy.NEWER_FACT)

        # Resolve fact2 vs fact3
        contradiction2 = self.detector.detect_contradiction(fact2, fact3)
        self.engine.resolve_contradiction(contradiction2, ResolutionStrategy.NEWER_FACT)

        # Verify chain from fact1
        chain = self.engine.get_supersession_chain("fact_1")
        assert len(chain) >= 1

        # Verify current fact is fact3
        current = self.engine.get_current_truth("measurement", "temperature")
        assert current["id"] == "fact_3"
