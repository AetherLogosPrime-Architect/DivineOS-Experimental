"""Tests for the warrant storage system."""

import pytest
from divineos.core.ledger import init_db
from divineos.core.knowledge._base import init_knowledge_table, _get_connection, compute_hash
from divineos.core.logic.warrants import (
    WARRANT_TYPES,
    Warrant,
    count_valid_warrants,
    create_warrant,
    defeat_warrant,
    get_warrant_by_id,
    get_warrants,
    has_valid_warrant,
    init_warrant_table,
    withdraw_warrant,
)

import time
import uuid


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    init_warrant_table()
    yield


def _insert_knowledge(content="test knowledge"):
    """Helper to insert a knowledge entry for warrant tests."""
    kid = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO knowledge
               (knowledge_id, created_at, updated_at, knowledge_type, content,
                confidence, source_events, tags, access_count, content_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kid,
                time.time(),
                time.time(),
                "FACT",
                content,
                1.0,
                "[]",
                "[]",
                0,
                compute_hash(content),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return kid


class TestCreateWarrant:
    def test_create_empirical_warrant(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "EMPIRICAL", "Observed in test output")
        assert w.warrant_id
        assert w.knowledge_id == kid
        assert w.warrant_type == "EMPIRICAL"
        assert w.grounds == "Observed in test output"
        assert w.status == "ACTIVE"

    def test_create_testimonial_warrant(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "TESTIMONIAL", "User stated this directly", source_session="sess-1")
        assert w.warrant_type == "TESTIMONIAL"
        assert w.source_session == "sess-1"

    def test_create_inferential_warrant_with_backing(self):
        kid1 = _insert_knowledge("premise")
        kid2 = _insert_knowledge("conclusion")
        w = create_warrant(kid2, "INFERENTIAL", "Derived from premise", backing_ids=[kid1])
        assert w.backing_ids == [kid1]

    def test_create_inherited_warrant(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "INHERITED", "From seed data")
        assert w.warrant_type == "INHERITED"

    def test_invalid_warrant_type_raises(self):
        kid = _insert_knowledge()
        with pytest.raises(ValueError, match="Invalid warrant type"):
            create_warrant(kid, "MAGICAL_THINKING", "vibes only")

    def test_all_warrant_types_accepted(self):
        kid = _insert_knowledge()
        for wtype in WARRANT_TYPES:
            w = create_warrant(kid, wtype, f"grounds for {wtype}")
            assert w.warrant_type == wtype


class TestGetWarrants:
    def test_get_warrants_for_entry(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "first")
        create_warrant(kid, "TESTIMONIAL", "second")
        warrants = get_warrants(kid)
        assert len(warrants) == 2

    def test_get_warrants_filtered_by_status(self):
        kid = _insert_knowledge()
        w1 = create_warrant(kid, "EMPIRICAL", "will be defeated")
        create_warrant(kid, "TESTIMONIAL", "stays active")
        defeat_warrant(w1.warrant_id, "contradicted")

        active = get_warrants(kid, status="ACTIVE")
        defeated = get_warrants(kid, status="DEFEATED")
        assert len(active) == 1
        assert len(defeated) == 1

    def test_get_warrant_by_id(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "EMPIRICAL", "test grounds")
        retrieved = get_warrant_by_id(w.warrant_id)
        assert retrieved is not None
        assert retrieved.grounds == "test grounds"

    def test_get_nonexistent_warrant(self):
        result = get_warrant_by_id("nonexistent-id")
        assert result is None

    def test_no_warrants_returns_empty(self):
        kid = _insert_knowledge()
        assert get_warrants(kid) == []


class TestDefeatWarrant:
    def test_defeat_changes_status(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "EMPIRICAL", "fragile claim")
        assert defeat_warrant(w.warrant_id, "new evidence contradicts")
        updated = get_warrant_by_id(w.warrant_id)
        assert updated.status == "DEFEATED"

    def test_defeat_records_reason(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "EMPIRICAL", "claim")
        defeat_warrant(w.warrant_id, "reason one")
        updated = get_warrant_by_id(w.warrant_id)
        assert "reason one" in updated.defeaters

    def test_defeat_nonexistent_returns_false(self):
        assert defeat_warrant("nonexistent", "reason") is False


class TestWithdrawWarrant:
    def test_withdraw_changes_status(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "TESTIMONIAL", "claim")
        assert withdraw_warrant(w.warrant_id)
        updated = get_warrant_by_id(w.warrant_id)
        assert updated.status == "WITHDRAWN"

    def test_withdraw_nonexistent_returns_false(self):
        assert withdraw_warrant("nonexistent") is False


class TestValidityChecks:
    def test_has_valid_warrant_true(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "solid evidence")
        assert has_valid_warrant(kid) is True

    def test_has_valid_warrant_false_no_warrants(self):
        kid = _insert_knowledge()
        assert has_valid_warrant(kid) is False

    def test_has_valid_warrant_false_all_defeated(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "EMPIRICAL", "fragile")
        defeat_warrant(w.warrant_id, "nope")
        assert has_valid_warrant(kid) is False

    def test_empty_grounds_not_valid(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "")
        assert has_valid_warrant(kid) is False

    def test_count_valid_warrants(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "evidence 1")
        create_warrant(kid, "TESTIMONIAL", "user said so")
        w3 = create_warrant(kid, "INHERITED", "from seed")
        defeat_warrant(w3.warrant_id, "outdated")
        assert count_valid_warrants(kid) == 2


class TestWarrantDataclass:
    def test_is_valid_active_with_grounds(self):
        w = Warrant(
            warrant_id="w1",
            knowledge_id="k1",
            warrant_type="EMPIRICAL",
            grounds="real evidence",
            status="ACTIVE",
        )
        assert w.is_valid() is True

    def test_is_valid_defeated(self):
        w = Warrant(
            warrant_id="w1",
            knowledge_id="k1",
            warrant_type="EMPIRICAL",
            grounds="evidence",
            status="DEFEATED",
        )
        assert w.is_valid() is False

    def test_is_valid_empty_grounds(self):
        w = Warrant(
            warrant_id="w1",
            knowledge_id="k1",
            warrant_type="EMPIRICAL",
            grounds="   ",
            status="ACTIVE",
        )
        assert w.is_valid() is False
