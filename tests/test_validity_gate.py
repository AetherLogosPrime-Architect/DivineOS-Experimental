"""Tests for the validity gate — warrant-aware maturity promotion."""

import pytest
import time
import uuid

from divineos.core.ledger import init_db
from divineos.core.knowledge._base import init_knowledge_table, _get_connection, compute_hash
from divineos.core.logic.warrants import init_warrant_table, create_warrant, defeat_warrant
from divineos.core.logic.relations import init_relation_table
from divineos.core.logic.validity_gate import (
    ValidityVerdict,
    can_promote,
    check_validity_for_promotion,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    init_warrant_table()
    init_relation_table()
    yield


def _insert_knowledge(content="test"):
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


class TestRawToHypothesis:
    def test_always_allowed(self):
        kid = _insert_knowledge()
        verdict = check_validity_for_promotion(kid, "RAW", "HYPOTHESIS")
        assert verdict.passed is True

    def test_allowed_without_warrants(self):
        kid = _insert_knowledge()
        assert can_promote(kid, "RAW", "HYPOTHESIS") is True


class TestHypothesisToTested:
    def test_passes_with_one_warrant(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "observed in test")
        verdict = check_validity_for_promotion(kid, "HYPOTHESIS", "TESTED")
        assert verdict.passed is True
        assert verdict.warrant_count >= 1

    def test_fails_without_warrants(self):
        kid = _insert_knowledge()
        verdict = check_validity_for_promotion(kid, "HYPOTHESIS", "TESTED")
        assert verdict.passed is False

    def test_fails_with_only_defeated_warrants(self):
        kid = _insert_knowledge()
        w = create_warrant(kid, "EMPIRICAL", "was true once")
        defeat_warrant(w.warrant_id, "no longer true")
        assert can_promote(kid, "HYPOTHESIS", "TESTED") is False


class TestTestedToConfirmed:
    def test_passes_with_two_different_types(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "test output confirmed")
        create_warrant(kid, "TESTIMONIAL", "user verified")
        verdict = check_validity_for_promotion(kid, "TESTED", "CONFIRMED")
        assert verdict.passed is True
        assert verdict.warrant_count >= 2
        assert len(verdict.warrant_types) >= 2

    def test_fails_with_one_warrant(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "only one source")
        verdict = check_validity_for_promotion(kid, "TESTED", "CONFIRMED")
        assert verdict.passed is False

    def test_fails_with_same_type_twice(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "evidence A")
        create_warrant(kid, "EMPIRICAL", "evidence B")
        verdict = check_validity_for_promotion(kid, "TESTED", "CONFIRMED")
        assert verdict.passed is False
        assert "2+ warrant types" in verdict.reason

    def test_fails_with_no_warrants(self):
        kid = _insert_knowledge()
        assert can_promote(kid, "TESTED", "CONFIRMED") is False

    def test_defeated_warrants_dont_count(self):
        kid = _insert_knowledge()
        w1 = create_warrant(kid, "EMPIRICAL", "evidence")
        create_warrant(kid, "TESTIMONIAL", "user said")
        defeat_warrant(w1.warrant_id, "outdated")
        verdict = check_validity_for_promotion(kid, "TESTED", "CONFIRMED")
        assert verdict.passed is False


class TestUnknownTransitions:
    def test_unknown_transition_allowed(self):
        kid = _insert_knowledge()
        verdict = check_validity_for_promotion(kid, "CONFIRMED", "REVISED")
        assert verdict.passed is True
        assert "No validity rule" in verdict.reason


class TestCanPromote:
    def test_quick_check_true(self):
        kid = _insert_knowledge()
        create_warrant(kid, "EMPIRICAL", "evidence")
        assert can_promote(kid, "HYPOTHESIS", "TESTED") is True

    def test_quick_check_false(self):
        kid = _insert_knowledge()
        assert can_promote(kid, "HYPOTHESIS", "TESTED") is False


class TestValidityVerdict:
    def test_verdict_fields(self):
        v = ValidityVerdict(
            passed=True,
            current_maturity="RAW",
            target_maturity="HYPOTHESIS",
            reason="test",
            warrant_count=0,
            warrant_types=[],
        )
        assert v.passed is True
        assert v.current_maturity == "RAW"
