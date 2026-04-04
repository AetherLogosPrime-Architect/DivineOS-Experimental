"""Extended tests for proactive patterns — covering _get_positive_patterns and scoring."""

import pytest

from divineos.core.knowledge import get_connection, init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()
    init_memory_tables()


class TestGetPositivePatterns:
    """Test the pattern collection from various sources."""

    def test_collects_principles(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Always test after code changes for reliability.",
            confidence=0.8,
        )
        patterns = _get_positive_patterns()
        knowledge_patterns = [p for p in patterns if p["source"] == "knowledge"]
        assert len(knowledge_patterns) >= 1
        assert knowledge_patterns[0]["type"] == "PRINCIPLE"

    def test_collects_procedures(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        store_knowledge(
            knowledge_type="PROCEDURE",
            content="Run pytest before committing changes.",
            confidence=0.7,
        )
        patterns = _get_positive_patterns()
        proc_patterns = [
            p for p in patterns if p["source"] == "knowledge" and p["type"] == "PROCEDURE"
        ]
        assert len(proc_patterns) >= 1

    def test_skips_low_confidence(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Uncertain principle that should be skipped.",
            confidence=0.3,
        )
        patterns = _get_positive_patterns()
        uncertain = [p for p in patterns if "Uncertain principle" in p.get("text", "")]
        assert len(uncertain) == 0

    def test_skips_superseded(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        kid1 = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Old principle superseded for proactive test.",
            confidence=0.9,
        )
        kid2 = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="New principle replacing old one.",
            confidence=0.9,
        )
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                (kid2, kid1),
            )
            conn.commit()
        finally:
            conn.close()

        patterns = _get_positive_patterns()
        old = [p for p in patterns if "Old principle superseded" in p.get("text", "")]
        assert len(old) == 0

    def test_weight_calculated(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Weighted principle for proactive test.",
            confidence=0.8,
        )
        patterns = _get_positive_patterns()
        for p in patterns:
            assert "weight" in p
            assert p["weight"] > 0

    def test_collects_opinions_if_available(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        try:
            from divineos.core.opinion_store import init_opinion_table, store_opinion

            init_opinion_table()
            store_opinion(
                topic="testing",
                position="Mutation testing catches bugs that coverage misses.",
                confidence=0.8,
            )
            patterns = _get_positive_patterns()
            opinion_patterns = [p for p in patterns if p["source"] == "opinion"]
            assert len(opinion_patterns) >= 1
            assert opinion_patterns[0]["type"] == "OPINION"
        except ImportError:
            pytest.skip("opinion_store not available")

    def test_collects_decisions_if_available(self):
        from divineos.core.proactive_patterns import _get_positive_patterns

        try:
            from divineos.core.decision_journal import init_decision_journal, record_decision

            init_decision_journal()
            record_decision(
                content="Chose pytest-cov for coverage.",
                reasoning="Best information-to-effort ratio.",
                tension="coverage vs speed",
            )
            patterns = _get_positive_patterns()
            decision_patterns = [p for p in patterns if p["source"] == "decision"]
            assert len(decision_patterns) >= 1
        except ImportError:
            pytest.skip("decision_journal not available")


class TestRecommendScoring:
    """Scoring logic — overlap, signal boost, access boost."""

    def test_keyword_match_boosts_relevance(self):
        from divineos.core.proactive_patterns import recommend

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Database sqlite connections should use context managers for cleanup.",
            confidence=0.8,
        )
        recs = recommend("sqlite database connection handling")
        if recs:
            assert recs[0]["relevance"] > 0.3

    def test_access_count_boosts_relevance(self):
        from divineos.core.proactive_patterns import recommend

        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Frequently accessed principle about testing quality assurance.",
            confidence=0.8,
        )
        # Bump access count
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET access_count = 20 WHERE knowledge_id = ?",
                (kid,),
            )
            conn.commit()
        finally:
            conn.close()

        recs = recommend("testing quality assurance principles")
        if recs:
            assert any("well-tested" in r.get("reason", "") for r in recs)

    def test_relevance_capped_at_1(self):
        from divineos.core.proactive_patterns import recommend

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Testing testing testing quality quality quality assurance assurance.",
            confidence=0.99,
        )
        recs = recommend("testing quality assurance")
        for r in recs:
            assert r["relevance"] <= 1.0

    def test_reason_includes_content_match(self):
        from divineos.core.proactive_patterns import recommend

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Append only ledger integrity verification should happen at session end.",
            confidence=0.9,
        )
        recs = recommend("append only ledger integrity verification at session end")
        if recs:
            matching = [r for r in recs if "content match" in r.get("reason", "")]
            assert len(matching) >= 1


class TestFormatRecommendations:
    """Format rendering."""

    def test_high_confidence_star(self):
        from divineos.core.proactive_patterns import format_recommendations

        recs = [
            {
                "text": "High conf principle",
                "relevance": 0.9,
                "source": "knowledge",
                "type": "PRINCIPLE",
                "id": "k1",
                "confidence": 0.9,
                "reason": "content match",
            }
        ]
        output = format_recommendations(recs)
        assert "★" in output

    def test_low_confidence_open_star(self):
        from divineos.core.proactive_patterns import format_recommendations

        recs = [
            {
                "text": "Lower conf observation",
                "relevance": 0.5,
                "source": "knowledge",
                "type": "OBSERVATION",
                "id": "k2",
                "confidence": 0.6,
                "reason": "keyword match",
            }
        ]
        output = format_recommendations(recs)
        assert "☆" in output

    def test_shows_source_and_type(self):
        from divineos.core.proactive_patterns import format_recommendations

        recs = [
            {
                "text": "Some principle",
                "relevance": 0.7,
                "source": "opinion",
                "type": "OPINION",
                "id": "o1",
                "confidence": 0.8,
                "reason": "keyword match",
            }
        ]
        output = format_recommendations(recs)
        assert "opinion" in output
        assert "OPINION" in output

    def test_truncates_long_text(self):
        from divineos.core.proactive_patterns import format_recommendations

        long_text = "A" * 200
        recs = [
            {
                "text": long_text,
                "relevance": 0.7,
                "source": "knowledge",
                "type": "PRINCIPLE",
                "id": "k3",
                "confidence": 0.8,
                "reason": "test",
            }
        ]
        output = format_recommendations(recs)
        # Text should be truncated to 150 chars
        assert len(long_text) > 150
        assert "A" * 151 not in output


class TestGetFullContextAdvice:
    """Combined anticipation + recommendations."""

    def test_returns_string_with_data(self):
        from divineos.core.proactive_patterns import get_full_context_advice

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Database connections require proper cleanup and context managers.",
            confidence=0.9,
        )
        result = get_full_context_advice("database connection cleanup")
        assert isinstance(result, str)

    def test_empty_context_returns_empty(self):
        from divineos.core.proactive_patterns import get_full_context_advice

        result = get_full_context_advice("")
        assert result == ""
