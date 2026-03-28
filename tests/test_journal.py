"""Tests for the journal system — save, search, link, FTS."""

from divineos.core.memory import init_memory_tables
from divineos.core.memory_journal import (
    journal_count,
    journal_link,
    journal_list,
    journal_save,
    journal_search,
)


class TestJournalBasics:
    def test_save_and_list(self):
        init_memory_tables()
        eid = journal_save("I learned something today", context="testing")
        assert eid
        entries = journal_list()
        assert len(entries) == 1
        assert entries[0]["content"] == "I learned something today"
        assert entries[0]["context"] == "testing"

    def test_save_with_tags(self):
        init_memory_tables()
        journal_save("Tagged entry", tags="reflection,learning")
        entries = journal_list()
        assert entries[0]["tags"] == "reflection,learning"

    def test_save_with_linked_knowledge(self):
        init_memory_tables()
        journal_save("Linked entry", linked_knowledge_id="k-123")
        entries = journal_list()
        assert entries[0]["linked_knowledge_id"] == "k-123"

    def test_count(self):
        init_memory_tables()
        assert journal_count() == 0
        journal_save("one")
        journal_save("two")
        assert journal_count() == 2

    def test_list_ordering(self):
        init_memory_tables()
        journal_save("first")
        journal_save("second")
        entries = journal_list()
        assert entries[0]["content"] == "second"  # newest first


class TestJournalSearch:
    def test_search_finds_content(self):
        init_memory_tables()
        journal_save("The testing framework works well")
        journal_save("I like pizza for lunch")
        results = journal_search("testing framework")
        assert len(results) >= 1
        assert "testing" in results[0]["content"].lower()

    def test_search_no_results(self):
        init_memory_tables()
        journal_save("Something completely different")
        results = journal_search("xyznonexistent")
        assert len(results) == 0

    def test_search_by_context(self):
        init_memory_tables()
        journal_save("A thought", context="debugging session")
        results = journal_search("debugging")
        assert len(results) >= 1

    def test_search_by_tags(self):
        init_memory_tables()
        journal_save("Reflection on work", tags="weekly-review")
        results = journal_search("weekly-review")
        assert len(results) >= 1

    def test_search_limit(self):
        init_memory_tables()
        for i in range(10):
            journal_save(f"Entry about testing number {i}")
        results = journal_search("testing", limit=3)
        assert len(results) <= 3


class TestJournalLink:
    def test_link_entry_to_knowledge(self):
        init_memory_tables()
        eid = journal_save("I noticed a pattern")
        assert journal_link(eid, "knowledge-abc-123")
        entries = journal_list()
        assert entries[0]["linked_knowledge_id"] == "knowledge-abc-123"

    def test_link_nonexistent_entry(self):
        init_memory_tables()
        assert not journal_link("nonexistent-id", "knowledge-abc")

    def test_link_updates_existing(self):
        init_memory_tables()
        eid = journal_save("Pattern observation", linked_knowledge_id="old-id")
        journal_link(eid, "new-id")
        entries = journal_list()
        assert entries[0]["linked_knowledge_id"] == "new-id"
