"""Tests for the knowledge maturity lifecycle."""

import os

from divineos.core.constants import (
    MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE,
    MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION,
    MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE,
    MATURITY_RAW_TO_HYPOTHESIS_CORROBORATION,
    MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE,
    MATURITY_TESTED_TO_CONFIRMED_CORROBORATION,
)
from divineos.core.knowledge import (
    _get_connection,
    init_knowledge_table,
    store_knowledge,
    store_knowledge_smart,
)
from divineos.core.knowledge_maintenance import (
    check_promotion,
    increment_corroboration,
    promote_maturity,
    run_maturity_cycle,
)
from divineos.core.ledger import init_db


class TestCheckPromotion:
    """Test promotion logic in isolation — thresholds from constants.py."""

    def test_raw_to_hypothesis(self):
        entry = {
            "maturity": "RAW",
            "corroboration_count": MATURITY_RAW_TO_HYPOTHESIS_CORROBORATION,
            "confidence": MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE + 0.1,
        }
        assert check_promotion(entry) == "HYPOTHESIS"

    def test_raw_needs_corroboration(self):
        entry = {"maturity": "RAW", "corroboration_count": 0, "confidence": 0.9}
        assert check_promotion(entry) is None

    def test_hypothesis_to_tested(self):
        entry = {
            "maturity": "HYPOTHESIS",
            "corroboration_count": MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION,
            "confidence": MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE + 0.1,
        }
        assert check_promotion(entry) == "TESTED"

    def test_hypothesis_below_threshold(self):
        """HYPOTHESIS needs both corroboration AND confidence to promote."""
        entry = {
            "maturity": "HYPOTHESIS",
            "corroboration_count": max(0, MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION - 1),
            "confidence": 0.9,
        }
        assert check_promotion(entry) is None

    def test_tested_to_confirmed(self):
        entry = {
            "maturity": "TESTED",
            "corroboration_count": MATURITY_TESTED_TO_CONFIRMED_CORROBORATION,
            "confidence": MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE + 0.1,
        }
        assert check_promotion(entry) == "CONFIRMED"

    def test_tested_needs_high_confidence(self):
        entry = {
            "maturity": "TESTED",
            "corroboration_count": MATURITY_TESTED_TO_CONFIRMED_CORROBORATION,
            "confidence": MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE - 0.15,
        }
        assert check_promotion(entry) is None

    def test_tested_needs_enough_corroborations(self):
        entry = {
            "maturity": "TESTED",
            "corroboration_count": max(0, MATURITY_TESTED_TO_CONFIRMED_CORROBORATION - 1),
            "confidence": 0.9,
        }
        assert check_promotion(entry) is None

    def test_confirmed_no_further_promotion(self):
        entry = {"maturity": "CONFIRMED", "corroboration_count": 100, "confidence": 1.0}
        assert check_promotion(entry) is None


class TestPromoteMaturity:
    """Integration tests with database."""

    def test_promote_raw_to_hypothesis(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Python three twelve added type parameter syntax for generics",
                confidence=0.7,
                maturity="RAW",
            )
            # Set corroboration_count to 1
            conn = _get_connection()
            conn.execute(
                "UPDATE knowledge SET corroboration_count = 1 WHERE knowledge_id = ?",
                (kid,),
            )
            conn.commit()
            conn.close()

            result = promote_maturity(kid)
            assert result == "HYPOTHESIS"

            conn = _get_connection()
            row = conn.execute(
                "SELECT maturity FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == "HYPOTHESIS"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_no_promotion_when_not_ready(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Some fact about database schemas and table design",
                confidence=0.7,
                maturity="RAW",
            )
            result = promote_maturity(kid)
            assert result is None
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestIncrementCorroboration:
    def test_increments(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="Knowledge entries need corroboration tracking for maturity",
                confidence=0.7,
            )
            count = increment_corroboration(kid)
            assert count == 1
            count = increment_corroboration(kid)
            assert count == 2
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestRunMaturityCycle:
    def test_batch_promotions(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid1 = store_knowledge(
                knowledge_type="FACT",
                content="First fact about system architecture design patterns",
                confidence=0.7,
                maturity="RAW",
            )
            kid2 = store_knowledge(
                knowledge_type="FACT",
                content="Second fact about database indexing optimization strategies",
                confidence=0.7,
                maturity="HYPOTHESIS",
            )
            # Set corroboration for promotions
            conn = _get_connection()
            conn.execute(
                "UPDATE knowledge SET corroboration_count = 1 WHERE knowledge_id = ?",
                (kid1,),
            )
            conn.execute(
                "UPDATE knowledge SET corroboration_count = 3 WHERE knowledge_id = ?",
                (kid2,),
            )
            conn.commit()
            conn.close()

            from divineos.core.knowledge import get_knowledge

            entries = get_knowledge(limit=100)
            promotions = run_maturity_cycle(entries)

            assert promotions.get("HYPOTHESIS", 0) >= 1
            assert promotions.get("TESTED", 0) >= 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestCorroborationInSmartStore:
    """Test that store_knowledge_smart increments corroboration on NOOP."""

    def test_noop_increments_corroboration(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Store once
            kid = store_knowledge_smart("FACT", "Python uses indentation for code blocks")
            # Store same thing again (NOOP)
            kid2 = store_knowledge_smart("FACT", "Python uses indentation for code blocks")
            assert kid == kid2

            conn = _get_connection()
            row = conn.execute(
                "SELECT corroboration_count FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] >= 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)
