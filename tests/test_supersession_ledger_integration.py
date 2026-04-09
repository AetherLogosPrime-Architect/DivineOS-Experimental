"""Tests for ledger integration with supersession."""

from divineos.supersession.ledger_integration import (
    LedgerIntegration,
    get_ledger_integration,
    query_facts,
    query_supersession_events,
    store_fact,
    store_supersession_event,
)


class TestLedgerIntegration:
    """Tests for LedgerIntegration class."""

    def test_ledger_integration_creation(self):
        """Test creating a LedgerIntegration instance."""
        integration = LedgerIntegration()

        assert integration is not None

    def test_ledger_integration_availability_check(self):
        """Test that LedgerIntegration checks availability."""
        integration = LedgerIntegration()

        # Should be able to check availability
        assert isinstance(integration._is_available(), bool)


class TestStoreFact:
    """Tests for storing facts."""

    def test_store_fact(self):
        """Test storing a fact."""
        fact = {
            "id": "fact_391",
            "fact_type": "mathematical_operation",
            "fact_key": "17_times_23",
            "value": 391,
            "timestamp": "2026-03-19T17:00:00Z",
        }

        fact_id = store_fact(fact)

        assert fact_id == "fact_391"

    def test_store_multiple_facts(self):
        """Test storing multiple facts."""
        facts = [
            {
                "id": "fact_1",
                "fact_type": "test",
                "fact_key": "test",
                "value": 1,
            },
            {
                "id": "fact_2",
                "fact_type": "test",
                "fact_key": "test",
                "value": 2,
            },
        ]

        for fact in facts:
            fact_id = store_fact(fact)
            assert fact_id == fact["id"]


class TestStoreSupersessionEvent:
    """Tests for storing supersession events."""

    def test_store_supersession_event(self):
        """Test storing a supersession event."""
        event = {
            "event_id": "supersession_001",
            "event_type": "SUPERSESSION",
            "superseded_fact_id": "fact_391",
            "superseding_fact_id": "fact_500",
            "reason": "newer_fact",
            "timestamp": "2026-03-19T17:05:01Z",
            "hash": "abc123",
        }

        event_id = store_supersession_event(event)

        assert event_id == "supersession_001"

    def test_store_multiple_supersession_events(self):
        """Test storing multiple supersession events."""
        events = [
            {
                "event_id": "supersession_001",
                "event_type": "SUPERSESSION",
                "superseded_fact_id": "fact_391",
                "superseding_fact_id": "fact_500",
                "reason": "newer_fact",
                "timestamp": "2026-03-19T17:05:01Z",
                "hash": "abc123",
            },
            {
                "event_id": "supersession_002",
                "event_type": "SUPERSESSION",
                "superseded_fact_id": "fact_500",
                "superseding_fact_id": "fact_600",
                "reason": "higher_confidence",
                "timestamp": "2026-03-19T17:10:01Z",
                "hash": "def456",
            },
        ]

        for event in events:
            event_id = store_supersession_event(event)
            assert event_id == event["event_id"]


class TestQueryFacts:
    """Tests for querying facts."""

    def test_query_facts_no_filter(self):
        """Test querying facts without filter."""
        facts = query_facts()

        # Should return empty list or list of facts
        assert isinstance(facts, list)

    def test_query_facts_by_type(self):
        """Test querying facts by type."""
        facts = query_facts(fact_type="mathematical_operation")

        assert isinstance(facts, list)

    def test_query_facts_by_key(self):
        """Test querying facts by key."""
        facts = query_facts(fact_key="17_times_23")

        assert isinstance(facts, list)

    def test_query_facts_by_type_and_key(self):
        """Test querying facts by type and key."""
        facts = query_facts(fact_type="mathematical_operation", fact_key="17_times_23")

        assert isinstance(facts, list)


class TestQuerySupersessionEvents:
    """Tests for querying supersession events."""

    def test_query_supersession_events_no_filter(self):
        """Test querying supersession events without filter."""
        events = query_supersession_events()

        assert isinstance(events, list)

    def test_query_supersession_events_by_superseded_fact(self):
        """Test querying supersession events by superseded fact ID."""
        events = query_supersession_events(superseded_fact_id="fact_391")

        assert isinstance(events, list)

    def test_query_supersession_events_by_superseding_fact(self):
        """Test querying supersession events by superseding fact ID."""
        events = query_supersession_events(superseding_fact_id="fact_500")

        assert isinstance(events, list)

    def test_query_supersession_events_by_both_facts(self):
        """Test querying supersession events by both fact IDs."""
        events = query_supersession_events(
            superseded_fact_id="fact_391", superseding_fact_id="fact_500"
        )

        assert isinstance(events, list)


class TestGetLedgerIntegration:
    """Tests for getting ledger integration instance."""

    def test_get_ledger_integration(self):
        """Test getting ledger integration instance."""
        integration = get_ledger_integration()

        assert integration is not None
        assert isinstance(integration, LedgerIntegration)

    def test_get_ledger_integration_singleton(self):
        """Test that get_ledger_integration returns singleton."""
        integration1 = get_ledger_integration()
        integration2 = get_ledger_integration()

        assert integration1 is integration2


class TestLedgerIntegrationEdgeCases:
    """Tests for edge cases in ledger integration."""

    def test_store_fact_with_missing_id(self):
        """Test storing fact with missing ID."""
        fact = {
            "fact_type": "test",
            "fact_key": "test",
            "value": 1,
        }

        # Should handle gracefully
        fact_id = store_fact(fact)
        assert fact_id is None

    def test_store_supersession_event_with_missing_id(self):
        """Test storing supersession event with missing ID generates one."""
        event = {
            "event_type": "SUPERSESSION",
            "superseded_fact_id": "fact_391",
            "superseding_fact_id": "fact_500",
            "reason": "newer_fact",
        }

        # Should generate a UUID when event_id is missing
        event_id = store_supersession_event(event)
        assert event_id is not None

    def test_query_facts_with_invalid_type(self):
        """Test querying facts with invalid type."""
        facts = query_facts(fact_type="nonexistent_type")

        assert isinstance(facts, list)

    def test_query_supersession_events_with_invalid_id(self):
        """Test querying supersession events with invalid ID."""
        events = query_supersession_events(superseded_fact_id="nonexistent_id")

        assert isinstance(events, list)
