"""Tests for evidence-based confidence decay."""

import os
import time

from divineos.core.knowledge import (
    _get_connection,
    health_check,
    init_knowledge_table,
    store_knowledge,
)
from divineos.core.ledger import init_db
from divineos.core.memory import compute_importance


class TestAbandonedKnowledgeDecay:
    """Test that accessed-then-abandoned knowledge decays."""

    def test_abandoned_entry_decays(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="A fact that was accessed but then abandoned by the system",
                confidence=0.8,
            )
            # Set access_count > 0 and backdate updated_at
            conn = _get_connection()
            old_time = time.time() - (20 * 86400)  # 20 days ago
            conn.execute(
                "UPDATE knowledge SET access_count = 3, updated_at = ? WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            result = health_check()
            assert result["abandoned_decayed"] >= 1

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] < 0.8
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_recently_updated_not_abandoned(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="A fact that was recently accessed and updated today",
                confidence=0.8,
            )
            # access_count > 0 but updated_at is recent
            conn = _get_connection()
            conn.execute(
                "UPDATE knowledge SET access_count = 3 WHERE knowledge_id = ?",
                (kid,),
            )
            conn.commit()
            conn.close()

            health_check()

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 0.8  # no decay
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_directive_immune(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="DIRECTIVE",
                content="Always run tests after making code changes to verify",
                confidence=0.9,
            )
            conn = _get_connection()
            old_time = time.time() - (30 * 86400)
            conn.execute(
                "UPDATE knowledge SET access_count = 5, updated_at = ? WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            health_check()

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] == 0.9
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_abandoned_floor_at_minimum(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge(
                knowledge_type="FACT",
                content="A fact with already low confidence near the floor",
                confidence=0.3,
            )
            conn = _get_connection()
            old_time = time.time() - (20 * 86400)
            conn.execute(
                "UPDATE knowledge SET access_count = 2, updated_at = ? WHERE knowledge_id = ?",
                (old_time, kid),
            )
            conn.commit()
            conn.close()

            health_check()

            conn = _get_connection()
            row = conn.execute(
                "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
            conn.close()
            assert row[0] >= 0.3  # floor
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestImportanceMaturityAdjustments:
    """Test that maturity and low confidence affect importance scoring."""

    def test_confirmed_gets_bonus(self):
        entry = {
            "knowledge_type": "FACT",
            "confidence": 0.9,
            "access_count": 5,
            "source": "DEMONSTRATED",
            "maturity": "CONFIRMED",
        }
        score_confirmed = compute_importance(entry)

        entry["maturity"] = "RAW"
        score_raw = compute_importance(entry)

        assert score_confirmed > score_raw

    def test_hypothesis_gets_penalty(self):
        entry = {
            "knowledge_type": "FACT",
            "confidence": 0.9,
            "access_count": 5,
            "source": "DEMONSTRATED",
            "maturity": "HYPOTHESIS",
        }
        score_hypothesis = compute_importance(entry)

        entry["maturity"] = "RAW"
        score_raw = compute_importance(entry)

        assert score_hypothesis < score_raw

    def test_low_confidence_penalty(self):
        entry = {
            "knowledge_type": "FACT",
            "confidence": 0.2,
            "access_count": 5,
            "source": "DEMONSTRATED",
            "maturity": "RAW",
        }
        score_low = compute_importance(entry)

        entry["confidence"] = 0.8
        score_high = compute_importance(entry)

        assert score_low < score_high

    def test_importance_never_negative(self):
        entry = {
            "knowledge_type": "EPISODE",
            "confidence": 0.1,
            "access_count": 0,
            "source": "SYNTHESIZED",
            "maturity": "HYPOTHESIS",
        }
        score = compute_importance(entry)
        assert score >= 0.0
