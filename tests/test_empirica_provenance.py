"""Tests for EMPIRICA corroboration provenance (prereg-0fc072a8e787).

Audit finding find-35a47dbbf923: the bare ``corroboration_count``
integer was Goodhart-vulnerable — same actor accessing the same
claim multiple times inflated the count. Provenance events solve
it by recording WHO/WHAT, and the distinct-actor count excludes
ACCESS and LEGACY kinds.

Locked invariants:

* Same actor corroborating same claim multiple times counts as 1
  distinct actor, not N.
* ACCESS and LEGACY events are tracked but excluded from
  distinct-corroborator count by default.
* Backfill is idempotent: running it twice produces the same
  count of LEGACY events, not double.
* Self-corroboration can be excluded via ``exclude_actor`` param.
"""

from __future__ import annotations

import os

import pytest

from divineos.core.empirica.provenance import (
    CorroborationEvent,
    CorroborationKind,
    backfill_from_legacy_counter,
    count_by_kind,
    count_distinct_corroborators,
    get_corroboration_events,
    init_provenance_table,
    record_corroboration,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "provenance-test.db")
    try:
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        init_provenance_table()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


class TestCorroborationKindEnum:
    def test_six_kinds_defined(self):
        assert len(list(CorroborationKind)) == 6

    def test_kind_is_str_subclass(self):
        """String-subclass so sqlite/json roundtrip cleanly."""
        assert isinstance(CorroborationKind.USER, str)

    def test_string_values_stable(self):
        """Values are serialized to DB; if they change, old rows
        can't be read back."""
        assert CorroborationKind.USER.value == "user"
        assert CorroborationKind.COUNCIL.value == "council"
        assert CorroborationKind.EXTERNAL_AUDIT.value == "external_audit"
        assert CorroborationKind.OUTCOME_VERIFICATION.value == "outcome_verification"
        assert CorroborationKind.ACCESS.value == "access"
        assert CorroborationKind.LEGACY.value == "legacy"


class TestRecordCorroboration:
    def test_returns_event_with_id(self):
        ev = record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        assert ev.event_id.startswith("corrob-")
        assert ev.knowledge_id == "k1"
        assert ev.actor == "user:andrew"
        assert ev.kind == CorroborationKind.USER

    def test_multiple_events_for_same_knowledge_all_recorded(self):
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        record_corroboration("k1", "council:popper", CorroborationKind.COUNCIL)
        record_corroboration("k1", "audit:grok", CorroborationKind.EXTERNAL_AUDIT)
        events = get_corroboration_events("k1")
        assert len(events) == 3

    def test_events_ordered_oldest_first(self):
        e1 = record_corroboration("k1", "a1", CorroborationKind.USER)
        e2 = record_corroboration("k1", "a2", CorroborationKind.USER)
        events = get_corroboration_events("k1")
        assert [e.event_id for e in events] == [e1.event_id, e2.event_id]

    def test_evidence_pointer_stored(self):
        record_corroboration(
            "k1",
            "outcome:tests",
            CorroborationKind.OUTCOME_VERIFICATION,
            evidence_pointer="commit-abc123",
        )
        events = get_corroboration_events("k1")
        assert events[0].evidence_pointer == "commit-abc123"


class TestDistinctCorroboratorCount:
    def test_same_actor_multiple_times_counts_once(self):
        """The whole point: repeat access by same actor is NOT evidence."""
        for _ in range(5):
            record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        assert count_distinct_corroborators("k1") == 1

    def test_different_actors_each_count(self):
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        record_corroboration("k1", "council:popper", CorroborationKind.COUNCIL)
        record_corroboration("k1", "audit:grok", CorroborationKind.EXTERNAL_AUDIT)
        assert count_distinct_corroborators("k1") == 3

    def test_access_kind_excluded_by_default(self):
        """Access bumps are tracked but NOT evidence."""
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        for _ in range(10):
            record_corroboration("k1", "session:auto", CorroborationKind.ACCESS)
        assert count_distinct_corroborators("k1") == 1  # just the user

    def test_access_kind_included_when_asked(self):
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        record_corroboration("k1", "session:auto", CorroborationKind.ACCESS)
        assert count_distinct_corroborators("k1", include_access=True) == 2

    def test_legacy_kind_excluded_by_default(self):
        record_corroboration("k1", "legacy-backfill", CorroborationKind.LEGACY)
        record_corroboration("k1", "legacy-backfill", CorroborationKind.LEGACY)
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        assert count_distinct_corroborators("k1") == 1

    def test_legacy_kind_included_when_asked(self):
        record_corroboration("k1", "legacy-backfill", CorroborationKind.LEGACY)
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        assert count_distinct_corroborators("k1", include_legacy=True) == 2

    def test_exclude_actor_prevents_self_corroboration(self):
        """If the claim's creator counts as corroborator, they're
        grading their own paper."""
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        record_corroboration("k1", "council:popper", CorroborationKind.COUNCIL)
        assert (
            count_distinct_corroborators("k1", exclude_actor="user:andrew") == 1
        )  # only council remains

    def test_empty_knowledge_returns_zero(self):
        assert count_distinct_corroborators("k-nonexistent") == 0


class TestCountByKind:
    def test_groups_by_kind(self):
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        record_corroboration("k1", "user:bob", CorroborationKind.USER)
        record_corroboration("k1", "council:popper", CorroborationKind.COUNCIL)
        counts = count_by_kind("k1")
        assert counts[CorroborationKind.USER] == 2
        assert counts[CorroborationKind.COUNCIL] == 1

    def test_kinds_with_zero_events_absent(self):
        record_corroboration("k1", "user:andrew", CorroborationKind.USER)
        counts = count_by_kind("k1")
        assert CorroborationKind.COUNCIL not in counts
        assert CorroborationKind.ACCESS not in counts


class TestBackfillFromLegacyCounter:
    def _seed_knowledge_with_count(self, knowledge_id: str, count: int) -> None:
        """Helper: insert a knowledge row with given corroboration_count."""
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            import time

            conn.execute(
                "INSERT INTO knowledge "
                "(knowledge_id, created_at, updated_at, knowledge_type, content, "
                "confidence, source_events, tags, access_count, content_hash, "
                "source, maturity, corroboration_count, contradiction_count) "
                "VALUES (?, ?, ?, 'FACT', 'test', 0.5, '[]', '[]', 0, ?, 'test', "
                "'RAW', ?, 0)",
                (knowledge_id, time.time(), time.time(), f"hash-{knowledge_id}", count),
            )
            conn.commit()
        finally:
            conn.close()

    def test_backfill_creates_one_legacy_event_per_count(self):
        self._seed_knowledge_with_count("k1", 3)
        inserted = backfill_from_legacy_counter()
        assert inserted == 3
        events = get_corroboration_events("k1")
        assert len(events) == 3
        assert all(e.kind == CorroborationKind.LEGACY for e in events)

    def test_backfill_is_idempotent(self):
        self._seed_knowledge_with_count("k1", 3)
        first = backfill_from_legacy_counter()
        second = backfill_from_legacy_counter()
        assert first == 3
        assert second == 0  # nothing new
        assert len(get_corroboration_events("k1")) == 3

    def test_backfill_does_not_affect_distinct_count_by_default(self):
        """LEGACY events preserve history but don't count as evidence."""
        self._seed_knowledge_with_count("k1", 5)
        backfill_from_legacy_counter()
        assert count_distinct_corroborators("k1") == 0
        assert count_distinct_corroborators("k1", include_legacy=True) == 1

    def test_backfill_skips_rows_with_zero_count(self):
        self._seed_knowledge_with_count("k1", 0)
        inserted = backfill_from_legacy_counter()
        assert inserted == 0

    def test_backfill_tops_up_delta(self):
        """If someone bumps corroboration_count after backfill ran
        once, the next backfill adds only the new units."""
        self._seed_knowledge_with_count("k1", 2)
        backfill_from_legacy_counter()
        # Simulate the bare counter ticking up (as it does today)
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            conn.execute("UPDATE knowledge SET corroboration_count = 5 WHERE knowledge_id = 'k1'")
            conn.commit()
        finally:
            conn.close()
        delta = backfill_from_legacy_counter()
        assert delta == 3
        events = get_corroboration_events("k1")
        assert len(events) == 5


class TestEventImmutability:
    """The events table is append-only by contract. No update/delete
    functions are exposed from the module."""

    def test_module_exposes_no_delete(self):
        import divineos.core.empirica.provenance as mod

        assert not hasattr(mod, "delete_corroboration")
        assert not hasattr(mod, "remove_corroboration")

    def test_module_exposes_no_update(self):
        import divineos.core.empirica.provenance as mod

        assert not hasattr(mod, "update_corroboration")
        assert not hasattr(mod, "edit_corroboration")


class TestCorroborationEventDataclass:
    def test_event_is_frozen(self):
        """dataclass(frozen=True) — can't be mutated after creation."""
        ev = CorroborationEvent(
            event_id="corrob-test",
            knowledge_id="k1",
            actor="a",
            kind=CorroborationKind.USER,
            evidence_pointer=None,
            recorded_at=1000.0,
            notes=None,
        )
        with pytest.raises((AttributeError, Exception)):
            ev.actor = "different-actor"  # type: ignore[misc]
