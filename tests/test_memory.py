"""Tests for the personal memory system."""

import pytest
from divineos.ledger import init_db
from divineos.consolidation import init_knowledge_table, store_knowledge
from divineos.memory import (
    CORE_SLOTS,
    init_memory_tables,
    set_core,
    get_core,
    clear_core,
    format_core,
    compute_importance,
    promote_to_active,
    demote_from_active,
    get_active_memory,
    refresh_active_memory,
    recall,
    format_recall,
)
import divineos.ledger as ledger_mod
import divineos.memory as memory_mod


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    monkeypatch.setattr(memory_mod, "DB_PATH", test_db)
    init_db()
    init_knowledge_table()
    init_memory_tables()
    yield
    if test_db.exists():
        test_db.unlink()


# ─── Core Memory ─────────────────────────────────────────────────────


class TestCoreMemory:
    def test_set_and_get_slot(self):
        set_core("user_identity", "A vibecoder learning real engineering")
        result = get_core("user_identity")
        assert result == {"user_identity": "A vibecoder learning real engineering"}

    def test_get_nonexistent_slot(self):
        result = get_core("user_identity")
        assert result == {}

    def test_get_all_slots(self):
        set_core("user_identity", "Test user")
        set_core("project_purpose", "Test project")
        result = get_core()
        assert len(result) == 2
        assert result["user_identity"] == "Test user"
        assert result["project_purpose"] == "Test project"

    def test_overwrite_slot(self):
        set_core("user_identity", "Old value")
        set_core("user_identity", "New value")
        result = get_core("user_identity")
        assert result == {"user_identity": "New value"}

    def test_invalid_slot_raises(self):
        with pytest.raises(ValueError, match="Unknown slot"):
            set_core("not_a_real_slot", "content")

    def test_clear_slot(self):
        set_core("user_identity", "Something")
        assert clear_core("user_identity") is True
        assert get_core("user_identity") == {}

    def test_clear_nonexistent_slot(self):
        assert clear_core("user_identity") is False

    def test_clear_invalid_slot_raises(self):
        with pytest.raises(ValueError, match="Unknown slot"):
            clear_core("bogus_slot")

    def test_format_core_empty(self):
        assert format_core() == ""

    def test_format_core_with_data(self):
        set_core("user_identity", "A tester")
        set_core("project_purpose", "Testing things")
        output = format_core()
        assert "Core Memory" in output
        assert "User" in output
        assert "A tester" in output
        assert "Project" in output
        assert "Testing things" in output

    def test_all_slot_names_valid(self):
        """Every slot in CORE_SLOTS should be settable."""
        for slot in CORE_SLOTS:
            set_core(slot, f"test content for {slot}")
        result = get_core()
        assert len(result) == len(CORE_SLOTS)


# ─── Importance Scoring ──────────────────────────────────────────────


class TestImportanceScoring:
    def test_boundary_and_mistake_score_highest_type(self):
        for ktype in ("BOUNDARY", "MISTAKE"):
            entry = {"knowledge_type": ktype, "confidence": 0.0, "access_count": 0}
            score = compute_importance(entry)
            # 0.30 type + 0.02 source(default) = 0.32
            assert abs(score - 0.32) < 0.01, f"{ktype} scored {score}"

    def test_principle_scores_high(self):
        entry = {"knowledge_type": "PRINCIPLE", "confidence": 0.0, "access_count": 0}
        score = compute_importance(entry)
        # 0.28 type + 0.02 source = 0.30
        assert abs(score - 0.30) < 0.01

    def test_episode_scores_lowest_type_weight(self):
        entry = {"knowledge_type": "EPISODE", "confidence": 0.0, "access_count": 0}
        score = compute_importance(entry)
        # 0.05 type + 0.02 source = 0.07
        assert abs(score - 0.07) < 0.01

    def test_confidence_contributes_25_percent(self):
        entry = {"knowledge_type": "FACT", "confidence": 1.0, "access_count": 0}
        score = compute_importance(entry)
        # 0.10 type + 0.25 confidence + 0.02 source = 0.37
        assert abs(score - 0.37) < 0.01

    def test_corrected_source_bonus(self):
        base = {"knowledge_type": "FACT", "confidence": 0.0, "access_count": 0}
        corrected = {
            "knowledge_type": "FACT",
            "confidence": 0.0,
            "access_count": 0,
            "source": "CORRECTED",
        }
        diff = compute_importance(corrected) - compute_importance(base)
        # CORRECTED=0.10 vs default=0.02 → 0.08 difference
        assert abs(diff - 0.08) < 0.01

    def test_lesson_connection_adds_20_percent(self):
        entry = {"knowledge_type": "FACT", "confidence": 0.0, "access_count": 0}
        without = compute_importance(entry, has_active_lesson=False)
        with_lesson = compute_importance(entry, has_active_lesson=True)
        assert abs(with_lesson - without - 0.20) < 0.01

    def test_usage_logarithmic(self):
        """More access = higher score, with diminishing returns at the top."""
        zero = compute_importance({"knowledge_type": "FACT", "confidence": 0.0, "access_count": 0})
        low = compute_importance({"knowledge_type": "FACT", "confidence": 0.0, "access_count": 1})
        mid = compute_importance({"knowledge_type": "FACT", "confidence": 0.0, "access_count": 10})
        high = compute_importance({"knowledge_type": "FACT", "confidence": 0.0, "access_count": 20})
        # Each should increase
        assert zero < low < mid < high
        # Gap from 0->1 should be larger than 10->20 (diminishing returns)
        gap_early = low - zero
        gap_late = high - mid
        assert gap_early > gap_late

    def test_max_score_capped_at_1(self):
        entry = {"knowledge_type": "MISTAKE", "confidence": 1.0, "access_count": 100}
        score = compute_importance(entry, has_active_lesson=True)
        assert score <= 1.0

    def test_no_time_decay(self):
        """Score should not depend on any time field."""
        entry = {"knowledge_type": "MISTAKE", "confidence": 0.8, "access_count": 5}
        score = compute_importance(entry)
        # Same entry, no matter when — same score
        assert score == compute_importance(entry)


# ─── Active Memory ───────────────────────────────────────────────────


class TestActiveMemory:
    def _store_fact(self, content="Test fact"):
        return store_knowledge("FACT", content, confidence=0.8)

    def test_promote_and_retrieve(self):
        kid = self._store_fact()
        mid = promote_to_active(kid, "test reason")
        assert isinstance(mid, str)

        active = get_active_memory()
        assert len(active) == 1
        assert active[0]["knowledge_id"] == kid
        assert active[0]["reason"] == "test reason"

    def test_promote_same_twice_updates(self):
        kid = self._store_fact()
        mid1 = promote_to_active(kid, "first reason", importance=0.5)
        mid2 = promote_to_active(kid, "updated reason", importance=0.9)
        assert mid1 == mid2  # same memory_id

        active = get_active_memory()
        assert len(active) == 1
        assert active[0]["reason"] == "updated reason"
        assert active[0]["importance"] == 0.9

    def test_demote(self):
        kid = self._store_fact()
        promote_to_active(kid, "test")
        assert demote_from_active(kid) is True
        assert get_active_memory() == []

    def test_demote_nonexistent(self):
        assert demote_from_active("nonexistent_id") is False

    def test_pinned_cannot_be_demoted(self):
        kid = self._store_fact()
        promote_to_active(kid, "pinned test", pinned=True)
        assert demote_from_active(kid) is False
        assert len(get_active_memory()) == 1

    def test_ranked_by_importance(self):
        kid1 = self._store_fact("Low importance fact")
        kid2 = self._store_fact("High importance fact")
        promote_to_active(kid1, "low", importance=0.2)
        promote_to_active(kid2, "high", importance=0.9)

        active = get_active_memory()
        assert len(active) == 2
        assert active[0]["knowledge_id"] == kid2  # highest first

    def test_active_memory_joins_knowledge(self):
        kid = store_knowledge("MISTAKE", "Don't code without reading", confidence=0.9)
        promote_to_active(kid, "critical lesson")

        active = get_active_memory()
        assert active[0]["content"] == "Don't code without reading"
        assert active[0]["knowledge_type"] == "MISTAKE"
        assert active[0]["confidence"] == 0.9


class TestRefreshActiveMemory:
    def test_promotes_above_threshold(self):
        # Store a high-confidence mistake — should pass threshold
        store_knowledge("MISTAKE", "Always read before editing", confidence=1.0)
        result = refresh_active_memory(importance_threshold=0.3)
        assert result["promoted"] >= 1

    def test_demotes_below_threshold(self):
        # Store a low-importance item and manually promote it
        kid = store_knowledge("EPISODE", "Session summary", confidence=0.1)
        promote_to_active(kid, "manual", importance=0.1)

        # Refresh with high threshold — should demote it
        result = refresh_active_memory(importance_threshold=0.9)
        assert result["demoted"] >= 1

    def test_pinned_survives_refresh(self):
        kid = store_knowledge("EPISODE", "Pinned episode", confidence=0.1)
        promote_to_active(kid, "pinned", importance=0.1, pinned=True)

        # Even with impossibly high threshold, pinned stays
        refresh_active_memory(importance_threshold=0.99)
        active = get_active_memory()
        pinned_ids = [a["knowledge_id"] for a in active if a["pinned"]]
        assert kid in pinned_ids

    def test_no_hard_cap(self):
        """All entries above threshold should be promoted — no arbitrary limit."""
        # Store 50 high-confidence mistakes
        for i in range(50):
            store_knowledge("MISTAKE", f"Mistake number {i}", confidence=1.0)

        refresh_active_memory(importance_threshold=0.3)
        active = get_active_memory()
        # All 50 should be in active memory
        assert len(active) >= 50


# ─── Recall ──────────────────────────────────────────────────────────


class TestRecall:
    def test_recall_empty(self):
        result = recall()
        assert result["core"] == ""
        assert result["active"] == []
        assert result["relevant"] == []

    def test_recall_with_core_memory(self):
        set_core("user_identity", "A curious developer")
        result = recall()
        assert "A curious developer" in result["core"]

    def test_recall_with_active_memory(self):
        kid = store_knowledge("FACT", "Python is great", confidence=0.9)
        promote_to_active(kid, "test")
        result = recall()
        assert len(result["active"]) == 1
        assert result["active"][0]["content"] == "Python is great"

    def test_recall_with_context_hint_boosts(self):
        kid1 = store_knowledge("FACT", "Python testing works", confidence=0.5)
        kid2 = store_knowledge("FACT", "Database migrations exist", confidence=0.5)
        promote_to_active(kid1, "test", importance=0.5)
        promote_to_active(kid2, "test", importance=0.5)

        result = recall(context_hint="testing")
        # The testing-related item should be boosted to the top
        assert result["active"][0]["content"] == "Python testing works"

    def test_recall_increments_surface_count(self):
        kid = store_knowledge("FACT", "Surface test", confidence=0.9)
        promote_to_active(kid, "test")

        recall()  # first recall
        recall()  # second recall

        active = get_active_memory()
        assert active[0]["surface_count"] == 2

    def test_format_recall_empty(self):
        result = recall()
        assert format_recall(result) == "No memories yet."

    def test_format_recall_with_data(self):
        set_core("user_identity", "Tester")
        kid = store_knowledge("MISTAKE", "Don't skip tests", confidence=0.9)
        promote_to_active(kid, "critical", importance=0.8)

        result = recall()
        text = format_recall(result)
        assert "Core Memory" in text
        assert "Active Memory" in text
        assert "Don't skip tests" in text
