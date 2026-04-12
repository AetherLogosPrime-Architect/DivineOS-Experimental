"""Tests for knowledge inference — deriving new knowledge from existing knowledge."""

import time

from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.knowledge.edges import init_edge_table
from divineos.core.knowledge.inference import (
    infer_boundaries_from_mistakes,
    promote_confirmed_patterns,
    run_inference_cycle,
    synthesize_lesson_insights,
)


def _setup():
    init_knowledge_table()
    init_edge_table()


class TestInferBoundariesFromMistakes:
    """Recurring mistakes should produce boundaries."""

    def test_three_similar_mistakes_produce_boundary(self):
        _setup()
        for i in range(3):
            store_knowledge(
                knowledge_type="MISTAKE",
                content=f"I edited files without reading them first and broke the code in session {i}",
                confidence=0.8,
            )

        created = infer_boundaries_from_mistakes(min_occurrences=3)
        assert len(created) >= 1

        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        row = conn.execute(
            "SELECT knowledge_type, source FROM knowledge WHERE knowledge_id = ?",
            (created[0],),
        ).fetchone()
        conn.close()
        assert row[0] == "BOUNDARY"
        assert row[1] == "SYNTHESIZED"

    def test_too_few_mistakes_no_inference(self):
        _setup()
        store_knowledge(
            knowledge_type="MISTAKE",
            content="I made one mistake about file editing",
            confidence=0.8,
        )
        created = infer_boundaries_from_mistakes(min_occurrences=3)
        assert created == []

    def test_dissimilar_mistakes_no_cluster(self):
        _setup()
        store_knowledge(
            knowledge_type="MISTAKE",
            content="I edited files without reading them first",
            confidence=0.8,
        )
        store_knowledge(
            knowledge_type="MISTAKE",
            content="The database connection timed out during testing",
            confidence=0.8,
        )
        store_knowledge(
            knowledge_type="MISTAKE",
            content="Import paths were wrong in the module configuration",
            confidence=0.8,
        )
        created = infer_boundaries_from_mistakes(min_occurrences=3)
        assert created == []

    def test_existing_boundary_prevents_duplicate(self):
        _setup()
        # Boundary uses same core words as the mistakes so overlap is high
        store_knowledge(
            knowledge_type="BOUNDARY",
            content="I keep making a recurring mistake: I edited files without reading them first and broke the code. This pattern must stop.",
            confidence=0.9,
        )
        for i in range(3):
            store_knowledge(
                knowledge_type="MISTAKE",
                content=f"I edited files without reading them first and broke the code in session {i}",
                confidence=0.8,
            )

        created = infer_boundaries_from_mistakes(min_occurrences=3)
        assert created == []

    def test_creates_derived_from_edges(self):
        _setup()
        for i in range(3):
            store_knowledge(
                knowledge_type="MISTAKE",
                content=f"I retried the same failing command without investigating the error in session {i}",
                confidence=0.8,
            )

        created = infer_boundaries_from_mistakes(min_occurrences=3)
        if created:
            from divineos.core.knowledge.edges import get_edges

            edges = get_edges(created[0])
            derived = [e for e in edges if e.edge_type == "DERIVED_FROM"]
            assert len(derived) >= 1


class TestPromoteConfirmedPatterns:
    """Confirmed patterns should become principles."""

    def test_confirmed_pattern_becomes_principle(self):
        _setup()
        from divineos.core.knowledge._base import _get_connection

        kid = store_knowledge(
            knowledge_type="PATTERN",
            content="I consistently show good test coverage in my sessions",
            confidence=0.9,
        )
        conn = _get_connection()
        conn.execute(
            "UPDATE knowledge SET maturity = 'CONFIRMED', corroboration_count = 5 "
            "WHERE knowledge_id = ?",
            (kid,),
        )
        conn.commit()
        conn.close()

        created = promote_confirmed_patterns()
        assert len(created) >= 1

        conn = _get_connection()
        row = conn.execute(
            "SELECT knowledge_type, source FROM knowledge WHERE knowledge_id = ?",
            (created[0],),
        ).fetchone()
        conn.close()
        assert row[0] == "PRINCIPLE"
        assert row[1] == "SYNTHESIZED"

    def test_unconfirmed_pattern_not_promoted(self):
        _setup()
        store_knowledge(
            knowledge_type="PATTERN",
            content="I showed good code quality once",
            confidence=0.9,
        )
        created = promote_confirmed_patterns()
        assert created == []

    def test_existing_principle_prevents_duplicate(self):
        _setup()
        from divineos.core.knowledge._base import _get_connection

        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I reliably demonstrate good test coverage in my sessions",
            confidence=0.9,
        )
        kid = store_knowledge(
            knowledge_type="PATTERN",
            content="I consistently show good test coverage in my sessions",
            confidence=0.9,
        )
        conn = _get_connection()
        conn.execute(
            "UPDATE knowledge SET maturity = 'CONFIRMED', corroboration_count = 5 "
            "WHERE knowledge_id = ?",
            (kid,),
        )
        conn.commit()
        conn.close()

        created = promote_confirmed_patterns()
        assert created == []


class TestSynthesizeLessonInsights:
    """Lesson clusters should produce insights."""

    def test_category_cluster_produces_insight(self):
        _setup()
        from divineos.core.knowledge._base import _get_connection, compute_hash

        conn = _get_connection()
        # lesson_tracking created by init_knowledge_table() in _setup()
        now = time.time()
        for i in range(3):
            desc = f"Retried without investigating error {i}"
            conn.execute(
                "INSERT INTO lesson_tracking "
                "(lesson_id, created_at, category, description, first_session, "
                "occurrences, last_seen, status, content_hash) "
                "VALUES (?, ?, ?, ?, ?, 2, ?, 'active', ?)",
                (
                    f"lesson-{i}",
                    now,
                    "blind_retry",
                    desc,
                    "test-session",
                    now,
                    compute_hash(desc),
                ),
            )
        conn.commit()
        conn.close()

        created = synthesize_lesson_insights()
        assert len(created) >= 1

        conn = _get_connection()
        row = conn.execute(
            "SELECT knowledge_type, source FROM knowledge WHERE knowledge_id = ?",
            (created[0],),
        ).fetchone()
        conn.close()
        assert row[0] == "OBSERVATION"
        assert row[1] == "SYNTHESIZED"

    def test_no_cluster_no_insight(self):
        _setup()
        created = synthesize_lesson_insights()
        assert created == []


class TestRunInferenceCycle:
    """Full inference cycle runs all steps."""

    def test_empty_store_no_crash(self):
        _setup()
        results = run_inference_cycle()
        assert "boundaries" in results
        assert "principles" in results
        assert "insights" in results

    def test_returns_dict_of_lists(self):
        _setup()
        results = run_inference_cycle()
        for value in results.values():
            assert isinstance(value, list)


class TestSourceTagging:
    """Existing inference paths use SYNTHESIZED source."""

    def test_store_knowledge_accepts_synthesized(self):
        _setup()
        from divineos.core.knowledge._base import _get_connection

        kid = store_knowledge(
            knowledge_type="OBSERVATION",
            content="This is a synthesized observation about patterns",
            confidence=0.7,
            source="SYNTHESIZED",
        )
        conn = _get_connection()
        row = conn.execute("SELECT source FROM knowledge WHERE knowledge_id = ?", (kid,)).fetchone()
        conn.close()
        assert row[0] == "SYNTHESIZED"
