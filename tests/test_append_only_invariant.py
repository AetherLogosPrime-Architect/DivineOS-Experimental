"""Tests for the append-only knowledge invariant.

CLAUDE.md rule: "The ledger and knowledge store never delete or update in
place. Supersede instead." This audit (2026-04-20) found three sites that
violated the invariant by mutating knowledge.content in place. Those have
been replaced with update_knowledge() supersession calls. These tests
lock the invariant so regressions are caught.

Locked invariants:

1. update_knowledge() with additional_tags unions old + new tags (no duplicates).
2. update_knowledge() with new_confidence_cap lowers confidence when old was higher.
3. update_knowledge() with new_confidence_cap leaves confidence alone when old was lower.
4. After update_knowledge, the old entry is marked superseded_by the new id.
5. The old entry's content is preserved (NOT mutated) — history intact.
"""

from __future__ import annotations

import pytest

from divineos.core.knowledge.crud import (
    get_knowledge,
    store_knowledge,
    update_knowledge,
)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    yield


class TestAdditionalTags:
    def test_new_tag_appended(self):
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Original content with enough words here",
            tags=["original-tag"],
        )
        new_id = update_knowledge(
            kid,
            new_content="Translated content with enough words here too",
            additional_tags=["sis-translated"],
        )
        assert new_id != kid

        # New entry has both tags
        new_entries = get_knowledge(limit=100)
        new_entry = next(e for e in new_entries if e["knowledge_id"] == new_id)
        assert "original-tag" in new_entry["tags"]
        assert "sis-translated" in new_entry["tags"]

    def test_duplicate_tag_not_re_added(self):
        """If old already had the additional tag, union produces no duplicate."""
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Original content already tagged here",
            tags=["sis-translated"],
        )
        new_id = update_knowledge(
            kid,
            new_content="New content with enough words here too",
            additional_tags=["sis-translated"],
        )
        new_entry = next(e for e in get_knowledge(limit=100) if e["knowledge_id"] == new_id)
        assert new_entry["tags"].count("sis-translated") == 1

    def test_no_additional_tags_leaves_old_tags_untouched(self):
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Original content with tags preserved here",
            tags=["keep-me", "me-too"],
        )
        new_id = update_knowledge(kid, new_content="New content with enough words here too")
        new_entry = next(e for e in get_knowledge(limit=100) if e["knowledge_id"] == new_id)
        assert set(new_entry["tags"]) == {"keep-me", "me-too"}


class TestConfidenceCap:
    def test_cap_lowers_when_old_higher(self):
        kid = store_knowledge(
            knowledge_type="FACT",
            content="High-confidence content with enough words here",
            confidence=0.9,
        )
        new_id = update_knowledge(
            kid,
            new_content="Quarantined content with enough words here too",
            new_confidence_cap=0.4,
        )
        new_entry = next(e for e in get_knowledge(limit=100) if e["knowledge_id"] == new_id)
        assert new_entry["confidence"] == 0.4

    def test_cap_leaves_low_alone(self):
        """If old was already under the cap, cap has no effect."""
        kid = store_knowledge(
            knowledge_type="FACT",
            content="Low confidence content with enough words here",
            confidence=0.2,
        )
        new_id = update_knowledge(
            kid,
            new_content="New content with enough words here too",
            new_confidence_cap=0.4,
        )
        new_entry = next(e for e in get_knowledge(limit=100) if e["knowledge_id"] == new_id)
        assert new_entry["confidence"] == 0.2


class TestHistoryPreserved:
    def test_old_entry_remains_with_original_content(self):
        """The core invariant: superseding creates a NEW row; the old row's
        content is NOT mutated. History is preserved."""
        original_content = "Original content that must NOT be mutated during update"
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content=original_content,
        )

        update_knowledge(
            kid,
            new_content="Completely different replacement content here",
        )

        # Read the old entry directly — it should still have its original content
        all_entries = get_knowledge(include_superseded=True, limit=100)
        old_entry = next(e for e in all_entries if e["knowledge_id"] == kid)
        assert old_entry["content"] == original_content, (
            "Old entry's content was mutated — append-only invariant broken"
        )

    def test_old_entry_marked_superseded_by_new(self):
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Original content with enough words to pass check",
        )
        new_id = update_knowledge(kid, new_content="New content with enough words here")

        all_entries = get_knowledge(include_superseded=True, limit=100)
        old_entry = next(e for e in all_entries if e["knowledge_id"] == kid)
        assert old_entry["superseded_by"] == new_id
