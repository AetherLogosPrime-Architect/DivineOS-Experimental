"""
Property-Based Tests for Contradiction Resolution

Tests formal correctness properties that must hold across all valid inputs.
Each property is universally quantified and validated using hypothesis.

Feature: divineos-system-hardening-integration
Property 2: Contradictions detected and resolved
Validates: Requirements 1.5
"""

from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone

from divineos.supersession import (
    ResolutionEngine,
    ResolutionStrategy,
    ContradictionDetector,
    ContradictionSeverity,
)


# ============================================================================
# Strategies for generating test data
# ============================================================================


def fact_id_strategy():
    """Generate valid fact IDs."""
    return st.text(min_size=5, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")


def fact_type_strategy():
    """Generate valid fact types."""
    return st.sampled_from(
        [
            "mathematical_operation",
            "measurement",
            "system_state",
            "configuration",
            "security_check",
            "deployment_status",
            "metadata",
            "timing",
            "performance_metric",
        ]
    )


def fact_key_strategy():
    """Generate valid fact keys."""
    return st.text(min_size=3, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")


def timestamp_strategy():
    """Generate valid ISO8601 timestamps."""
    return st.datetimes(
        min_value=datetime(2026, 1, 1),
        max_value=datetime(2026, 12, 31),
    ).map(lambda dt: dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"))


def confidence_strategy():
    """Generate valid confidence levels (0.0 to 1.0)."""
    return st.floats(min_value=0.0, max_value=1.0)


def fact_value_strategy():
    """Generate various fact values."""
    return st.one_of(
        st.integers(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.text(min_size=1, max_size=50),
        st.booleans(),
    )


def contradicting_facts_strategy():
    """Generate two facts that contradict each other (same type/key, different values)."""
    return st.tuples(
        fact_id_strategy(),
        fact_id_strategy(),
        fact_type_strategy(),
        fact_key_strategy(),
        fact_value_strategy(),
        fact_value_strategy(),
        timestamp_strategy(),
        timestamp_strategy(),
        confidence_strategy(),
        confidence_strategy(),
    ).filter(lambda x: x[0] != x[1] and x[4] != x[5])  # Different IDs and values


# ============================================================================
# Property 2: Contradictions Detected and Resolved
# ============================================================================


class TestContradictionDetectionAndResolution:
    """**Validates: Requirements 1.5** - Contradictions detected and resolved."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_contradictions_always_detected(self, fact_data):
        """
        Property: For any two facts with same type/key but different values,
        the system SHALL detect the contradiction.
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
            "source": "test",
        }

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)

        # Verify contradiction is detected
        assert contradiction is not None, "Contradiction should be detected for different values"
        assert contradiction.fact1_id == fact1_id
        assert contradiction.fact2_id == fact2_id
        assert contradiction.fact1_value == value1
        assert contradiction.fact2_value == value2

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_resolution_always_produces_winner_and_loser(self, fact_data):
        """
        Property: For any contradiction, resolution SHALL always produce
        exactly one winner and one loser.
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Verify exactly one winner and one loser
        assert supersession is not None
        assert supersession.superseded_fact_id in [fact1_id, fact2_id]
        assert supersession.superseding_fact_id in [fact1_id, fact2_id]
        assert supersession.superseded_fact_id != supersession.superseding_fact_id

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_newer_fact_always_wins_with_newer_fact_strategy(self, fact_data):
        """
        Property: When using NEWER_FACT strategy, the fact with the newer
        timestamp SHALL always be the winner (superseding fact).
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Determine which fact is newer
        if ts2 > ts1:
            # fact2 is newer, should be the winner
            assert supersession.superseding_fact_id == fact2_id
            assert supersession.superseded_fact_id == fact1_id
        else:
            # fact1 is newer or equal, should be the winner
            assert supersession.superseding_fact_id == fact1_id
            assert supersession.superseded_fact_id == fact2_id

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_supersession_chain_always_consistent(self, fact_data):
        """
        Property: For any fact that has been superseded, the supersession
        chain SHALL be consistent (no cycles, always points to current fact).
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
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

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_superseded_fact_marked_correctly(self, fact_data):
        """
        Property: After resolution, the superseded fact SHALL be marked as
        superseded, and the superseding fact SHALL NOT be marked as superseded.
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
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

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_query_returns_current_fact_not_superseded(self, fact_data):
        """
        Property: When querying for a fact after resolution, the system
        SHALL return the current (superseding) fact, not the superseded one.
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
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
        current = self.engine.get_current_truth(fact_type, fact_key)

        # Verify current fact is the superseding fact
        assert current is not None
        assert current["id"] == supersession.superseding_fact_id
        assert current["id"] != supersession.superseded_fact_id

    @given(
        st.lists(
            contradicting_facts_strategy(),
            min_size=2,
            max_size=5,
            unique_by=lambda x: (x[0], x[1]),  # Unique fact pairs
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_multiple_contradictions_all_resolved(self, fact_data_list):
        """
        Property: When multiple contradictions exist, the system SHALL resolve
        all of them and establish a complete supersession chain.
        """
        # Create facts from data
        facts = []
        for i, fact_data in enumerate(fact_data_list):
            (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
                fact_data
            )

            # Create unique IDs for this test
            unique_id1 = f"fact_{i}_a"
            unique_id2 = f"fact_{i}_b"

            fact1 = {
                "id": unique_id1,
                "fact_type": fact_type,
                "fact_key": fact_key,
                "value": value1,
                "timestamp": ts1,
                "confidence": conf1,
                "source": "test",
            }

            fact2 = {
                "id": unique_id2,
                "fact_type": fact_type,
                "fact_key": fact_key,
                "value": value2,
                "timestamp": ts2,
                "confidence": conf2,
                "source": "test",
            }

            facts.append((fact1, fact2))
            self.engine.register_fact(fact1)
            self.engine.register_fact(fact2)

        # Resolve all contradictions
        for fact1, fact2 in facts:
            contradiction = self.detector.detect_contradiction(fact1, fact2)
            if contradiction:
                self.engine.resolve_contradiction(contradiction, ResolutionStrategy.NEWER_FACT)

        # Verify all contradictions are resolved
        all_events = self.engine.get_all_supersession_events()
        assert len(all_events) >= len(fact_data_list), (
            "Should have at least one event per contradiction"
        )

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_supersession_event_has_required_fields(self, fact_data):
        """
        Property: Every SUPERSESSION event SHALL have all required fields:
        event_id, superseded_fact_id, superseding_fact_id, reason, timestamp, hash.
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Verify all required fields
        assert supersession.event_id is not None
        assert len(supersession.event_id) > 0
        assert supersession.superseded_fact_id is not None
        assert supersession.superseding_fact_id is not None
        assert supersession.reason is not None
        assert supersession.timestamp is not None
        assert supersession.hash is not None
        assert len(supersession.hash) == 64  # SHA256 hex digest

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_contradiction_severity_classified(self, fact_data):
        """
        Property: Every contradiction SHALL be classified with a severity level
        (CRITICAL, HIGH, MEDIUM, or LOW).
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
            "source": "test",
        }

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)

        # Verify severity is classified
        assert contradiction is not None
        assert contradiction.severity in [
            ContradictionSeverity.CRITICAL,
            ContradictionSeverity.HIGH,
            ContradictionSeverity.MEDIUM,
            ContradictionSeverity.LOW,
        ]

    @given(contradicting_facts_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_contradiction_context_captured(self, fact_data):
        """
        Property: Every contradiction SHALL capture full context including
        both facts' details and any additional context.
        """
        (fact1_id, fact2_id, fact_type, fact_key, value1, value2, ts1, ts2, conf1, conf2) = (
            fact_data
        )

        fact1 = {
            "id": fact1_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value1,
            "timestamp": ts1,
            "confidence": conf1,
            "source": "test",
        }

        fact2 = {
            "id": fact2_id,
            "fact_type": fact_type,
            "fact_key": fact_key,
            "value": value2,
            "timestamp": ts2,
            "confidence": conf2,
            "source": "test",
        }

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)

        # Verify context is captured
        assert contradiction is not None
        assert contradiction.context is not None
        assert "fact1" in contradiction.context
        assert "fact2" in contradiction.context
        assert contradiction.context["fact1"]["id"] == fact1_id
        assert contradiction.context["fact2"]["id"] == fact2_id
