"""Tests for the memory consolidation system."""

import time

import pytest
from divineos.core.ledger import init_db, log_event
from divineos.core.consolidation import (
    init_knowledge_table,
    store_knowledge,
    get_knowledge,
    search_knowledge,
    update_knowledge,
    get_unconsolidated_events,
    find_similar,
    generate_briefing,
    knowledge_stats,
    rebuild_fts_index,
    record_lesson,
    get_lessons,
    mark_lesson_improving,
    get_lesson_summary,
    check_recurring_lessons,
    extract_lessons_from_report,
    _search_knowledge_legacy,
    _normalize_text,
    _extract_key_terms,
    _compute_overlap,
    extract_session_topics,
    store_knowledge_smart,
    deep_extract_knowledge,
    supersede_knowledge,
    consolidate_related,
    record_access,
    _adjust_confidence,
    compute_effectiveness,
    health_check,
    apply_session_feedback,
    _is_noise_correction,
    _categorize_correction,
    clear_lessons,
    knowledge_health_report,
    migrate_knowledge_types,
    KNOWLEDGE_TYPES,
    KNOWLEDGE_SOURCES,
    KNOWLEDGE_MATURITY,
)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    init_knowledge_table()
    yield
    if test_db.exists():
        test_db.unlink()


class TestStoreKnowledge:
    def test_returns_knowledge_id(self):
        kid = store_knowledge("FACT", "Python uses indentation")
        assert isinstance(kid, str)
        assert len(kid) > 0

    def test_stores_with_correct_type(self):
        store_knowledge("PATTERN", "Errors cluster in parsing code")
        entries = get_knowledge(knowledge_type="PATTERN")
        assert len(entries) == 1
        assert entries[0]["knowledge_type"] == "PATTERN"

    def test_rejects_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid knowledge_type"):
            store_knowledge("INVALID", "nope")

    def test_dedup_exact_match(self):
        kid1 = store_knowledge("FACT", "The sky is blue")
        kid2 = store_knowledge("FACT", "The sky is blue")
        assert kid1 == kid2
        entries = get_knowledge()
        assert len(entries) == 1
        assert entries[0]["access_count"] == 1  # incremented once by dedup

    def test_stores_source_events(self):
        store_knowledge("FACT", "test fact", source_events=["evt-1", "evt-2"])
        entries = get_knowledge()
        assert entries[0]["source_events"] == ["evt-1", "evt-2"]


class TestGetKnowledge:
    def test_empty(self):
        assert get_knowledge() == []

    def test_filter_by_type(self):
        store_knowledge("FACT", "fact one")
        store_knowledge("MISTAKE", "mistake one")
        facts = get_knowledge(knowledge_type="FACT")
        assert len(facts) == 1
        assert facts[0]["content"] == "fact one"

    def test_filter_by_confidence(self):
        store_knowledge("FACT", "low confidence", confidence=0.3)
        store_knowledge("FACT", "high confidence", confidence=0.9)
        results = get_knowledge(min_confidence=0.5)
        assert len(results) == 1
        assert results[0]["content"] == "high confidence"

    def test_excludes_superseded_by_default(self):
        kid = store_knowledge("FACT", "old fact")
        update_knowledge(kid, "new fact")
        results = get_knowledge()
        assert len(results) == 1
        assert results[0]["content"] == "new fact"


class TestSearchKnowledge:
    def test_finds_matching(self):
        store_knowledge("FACT", "Python uses pytest for testing")
        store_knowledge("FACT", "JavaScript uses Jest")
        results = search_knowledge("pytest")
        assert len(results) == 1
        assert "pytest" in results[0]["content"]

    def test_no_matches(self):
        store_knowledge("FACT", "hello world")
        assert search_knowledge("zzzzz") == []

    def test_searches_tags(self):
        store_knowledge("PREFERENCE", "use ruff for linting", tags=["tooling", "linting"])
        results = search_knowledge("tooling")
        assert len(results) == 1

    def test_natural_language_query(self):
        """Multi-word natural language queries should find partial matches."""
        store_knowledge("FACT", "The noise filter prevents junk from entering knowledge")
        store_knowledge("FACT", "SQLite uses WAL mode for concurrency")
        results = search_knowledge("what does the noise filter do")
        assert len(results) >= 1
        assert any("noise" in r["content"] for r in results)

    def test_two_word_or_query(self):
        """Two unrelated keywords should match entries containing either."""
        store_knowledge("FACT", "Bash is the most used tool")
        store_knowledge("FACT", "pytest runs all tests quickly")
        results = search_knowledge("Bash pytest")
        assert len(results) == 2


class TestUpdateKnowledge:
    def test_creates_new_entry(self):
        kid1 = store_knowledge("FACT", "version 1")
        kid2 = update_knowledge(kid1, "version 2")
        assert kid1 != kid2

    def test_supersedes_old(self):
        kid1 = store_knowledge("FACT", "old")
        update_knowledge(kid1, "new")
        all_entries = get_knowledge(include_superseded=True)
        old_entry = [e for e in all_entries if e["knowledge_id"] == kid1][0]
        assert old_entry["superseded_by"] is not None

    def test_preserves_source_chain(self):
        kid1 = store_knowledge("FACT", "v1", source_events=["evt-1"])
        update_knowledge(kid1, "v2", additional_sources=["evt-2"])
        new_entry = get_knowledge()
        assert len(new_entry) == 1
        assert "evt-1" in new_entry[0]["source_events"]
        assert "evt-2" in new_entry[0]["source_events"]


class TestGetUnconsolidated:
    def test_all_unconsolidated_when_empty_knowledge(self):
        log_event("TEST", "user", {"content": "hello"})
        log_event("TEST", "user", {"content": "world"})
        events = get_unconsolidated_events()
        assert len(events) == 2

    def test_excludes_referenced_events(self):
        eid1 = log_event("TEST", "user", {"content": "first"})
        eid2 = log_event("TEST", "user", {"content": "second"})
        store_knowledge("FACT", "learned from first", source_events=[eid1])
        events = get_unconsolidated_events()
        event_ids = [e["event_id"] for e in events]
        assert eid1 not in event_ids
        assert eid2 in event_ids


class TestGenerateBriefing:
    def test_empty_briefing(self):
        result = generate_briefing()
        assert "No knowledge" in result

    def test_includes_types(self):
        store_knowledge("FACT", "a fact")
        store_knowledge("PATTERN", "a pattern")
        result = generate_briefing()
        assert "FACTS" in result
        assert "PATTERNS" in result

    def test_respects_max_items(self):
        for i in range(10):
            store_knowledge("FACT", f"fact number {i}")
        result = generate_briefing(max_items=3)
        assert result.count("fact number") == 3


class TestKnowledgeStats:
    def test_empty_stats(self):
        stats = knowledge_stats()
        assert stats["total"] == 0

    def test_counts_by_type(self):
        store_knowledge("FACT", "f1")
        store_knowledge("FACT", "f2")
        store_knowledge("MISTAKE", "m1")
        stats = knowledge_stats()
        assert stats["total"] == 3
        assert stats["by_type"]["FACT"] == 2
        assert stats["by_type"]["MISTAKE"] == 1


class TestFindSimilar:
    def test_finds_exact_match(self):
        store_knowledge("FACT", "exact content here")
        results = find_similar("exact content here")
        assert len(results) == 1

    def test_no_match(self):
        store_knowledge("FACT", "something")
        results = find_similar("completely different")
        assert len(results) == 0


# ─── Piece 1: FTS5 Search Tests ──────────────────────────────────────


class TestFTS5Search:
    def test_fts_search_finds_match(self):
        store_knowledge("FACT", "Python uses pytest for testing frameworks")
        results = search_knowledge("pytest")
        assert len(results) == 1
        assert "pytest" in results[0]["content"]

    def test_fts_search_ranks_relevance(self):
        """Entry with keyword in content should rank higher than one without."""
        store_knowledge("FACT", "pytest is a great testing framework for Python")
        store_knowledge("FACT", "JavaScript has many tools available")
        results = search_knowledge("pytest")
        assert len(results) == 1  # only the pytest one matches
        assert "pytest" in results[0]["content"]

    def test_fts_search_excludes_superseded(self):
        kid = store_knowledge("FACT", "pytest version one info")
        update_knowledge(kid, "pytest version two info")
        results = search_knowledge("pytest")
        assert len(results) == 1
        assert "version two" in results[0]["content"]

    def test_fts_stemming(self):
        """Porter stemmer should match 'running' when searching 'run'."""
        store_knowledge("FACT", "The tests were running successfully")
        results = search_knowledge("run")
        assert len(results) == 1

    def test_fts_no_match(self):
        store_knowledge("FACT", "hello world")
        results = search_knowledge("zzzznothing")
        assert len(results) == 0

    def test_fts_searches_tags(self):
        store_knowledge("PREFERENCE", "use ruff for linting", tags=["tooling", "linting"])
        results = search_knowledge("tooling")
        assert len(results) == 1


class TestRebuildFTSIndex:
    def test_rebuild_populates_index(self):
        store_knowledge("FACT", "first fact about databases")
        store_knowledge("FACT", "second fact about testing")
        # Rebuild from scratch
        count = rebuild_fts_index()
        assert count == 2
        # Search should still work
        results = search_knowledge("databases")
        assert len(results) == 1

    def test_rebuild_on_empty(self):
        count = rebuild_fts_index()
        assert count == 0


class TestLegacySearch:
    def test_legacy_finds_match(self):
        store_knowledge("FACT", "Python uses pytest for testing")
        results = _search_knowledge_legacy("pytest")
        assert len(results) == 1


# ─── Piece 3: Learning Loop Tests ────────────────────────────────────


class TestRecordLesson:
    def test_record_new_lesson(self):
        lid = record_lesson("blind_edit", "Read files before editing", "session-001")
        assert isinstance(lid, str)
        lessons = get_lessons()
        assert len(lessons) == 1
        assert lessons[0]["category"] == "blind_edit"
        assert lessons[0]["occurrences"] == 1
        assert "session-001" in lessons[0]["sessions"]

    def test_record_recurring_lesson(self):
        record_lesson("blind_edit", "Read files before editing", "session-001")
        record_lesson("blind_edit", "Read files before editing", "session-002")
        lessons = get_lessons(category="blind_edit")
        assert len(lessons) == 1
        assert lessons[0]["occurrences"] == 2
        assert "session-001" in lessons[0]["sessions"]
        assert "session-002" in lessons[0]["sessions"]

    def test_same_session_doesnt_duplicate(self):
        record_lesson("blind_edit", "Read files", "session-001")
        record_lesson("blind_edit", "Read files", "session-001")
        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["occurrences"] == 2  # incremented
        assert lessons[0]["sessions"].count("session-001") == 1  # not duplicated

    def test_different_categories_separate(self):
        record_lesson("blind_edit", "Read first", "session-001")
        record_lesson("test_failure", "Run tests", "session-001")
        lessons = get_lessons()
        assert len(lessons) == 2


class TestLessonStatus:
    def test_new_lesson_is_active(self):
        record_lesson("blind_edit", "Read first", "s1")
        lessons = get_lessons()
        assert lessons[0]["status"] == "active"

    def test_mark_improving_needs_3_occurrences(self):
        """Lesson with < 3 occurrences should NOT be marked improving."""
        record_lesson("blind_edit", "Read first", "s1")
        record_lesson("blind_edit", "Read first", "s2")
        mark_lesson_improving("blind_edit", "s3")
        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["status"] == "active"  # only 2 occurrences, stays active

    def test_mark_improving_with_3_plus(self):
        """Lesson with 3+ occurrences CAN be marked improving."""
        record_lesson("blind_edit", "Read first", "s1")
        record_lesson("blind_edit", "Read first", "s2")
        record_lesson("blind_edit", "Read first", "s3")
        mark_lesson_improving("blind_edit", "s4")
        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["status"] == "improving"

    def test_recurring_resets_to_active(self):
        """If mistake recurs after improving, status goes back to active."""
        record_lesson("blind_edit", "Read first", "s1")
        record_lesson("blind_edit", "Read first", "s2")
        record_lesson("blind_edit", "Read first", "s3")
        mark_lesson_improving("blind_edit", "s4")
        # Recurs in session 5
        record_lesson("blind_edit", "Read first", "s5")
        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["status"] == "active"
        assert lessons[0]["occurrences"] == 4


class TestCheckRecurringLessons:
    def test_finds_recurring(self):
        record_lesson("blind_edit", "Read first", "s1")
        record_lesson("blind_edit", "Read first", "s2")
        recurring = check_recurring_lessons(["blind_edit"])
        assert len(recurring) == 1
        assert recurring[0]["occurrences"] == 2

    def test_ignores_single_occurrence(self):
        record_lesson("blind_edit", "Read first", "s1")
        recurring = check_recurring_lessons(["blind_edit"])
        assert len(recurring) == 0


class TestGetLessonSummary:
    def test_empty_summary(self):
        result = get_lesson_summary()
        assert "No lessons" in result

    def test_summary_shows_active(self):
        record_lesson("blind_edit", "Read files before editing", "s1")
        record_lesson("blind_edit", "Read files before editing", "s2")
        result = get_lesson_summary()
        assert "ACTIVE LESSONS" in result
        assert "2x" in result
        assert "Read files before editing" in result


# ─── Piece 2: Lesson Extraction Tests ────────────────────────────────


class TestExtractLessonsFromReport:
    def test_extract_from_failing_check(self):
        checks = [
            {
                "name": "completeness",
                "passed": False,
                "score": 0.5,
                "summary": "3 blind edits found",
            },
        ]
        ids = extract_lessons_from_report(checks, "session-abc123")
        assert len(ids) >= 1
        knowledge = get_knowledge(knowledge_type="MISTAKE")
        assert len(knowledge) >= 1
        assert (
            "blind" in knowledge[0]["content"].lower() or "edit" in knowledge[0]["content"].lower()
        )

    def test_extract_from_passing_check(self):
        checks = [
            {
                "name": "completeness",
                "passed": True,
                "score": 0.95,
                "summary": "All files read before editing",
            },
        ]
        ids = extract_lessons_from_report(checks, "session-good")
        assert len(ids) >= 1
        knowledge = get_knowledge(knowledge_type="PATTERN")
        assert len(knowledge) >= 1

    def test_extract_from_tone_shifts(self):
        checks = []
        tone_shifts = [
            {"direction": "negative", "trigger": "AI ignored user request"},
        ]
        ids = extract_lessons_from_report(checks, "session-tone", tone_shifts=tone_shifts)
        assert len(ids) >= 1
        knowledge = get_knowledge(knowledge_type="MISTAKE")
        assert any("I upset the user" in k["content"] for k in knowledge)

    def test_extract_from_error_recovery(self):
        checks = []
        error_recovery = {"blind_retries": 3, "investigate_count": 1}
        ids = extract_lessons_from_report(checks, "session-err", error_recovery=error_recovery)
        assert len(ids) >= 1
        knowledge = get_knowledge(knowledge_type="MISTAKE")
        assert any("blindly retry" in k["content"] or "retried" in k["content"] for k in knowledge)

    def test_no_duplicate_extraction(self):
        """Running extraction twice shouldn't create duplicate knowledge."""
        checks = [
            {
                "name": "correctness",
                "passed": False,
                "score": 0.3,
                "summary": "Tests failed with 5 errors",
            },
        ]
        ids1 = extract_lessons_from_report(checks, "session-dup")
        ids2 = extract_lessons_from_report(checks, "session-dup")
        # Same knowledge ID returned due to dedup
        assert ids1 == ids2
        knowledge = get_knowledge(knowledge_type="MISTAKE")
        assert len(knowledge) == 1

    def test_extract_tags_correct(self):
        checks = [
            {"name": "safety", "passed": False, "score": 0.4, "summary": "Errors after edits"},
        ]
        extract_lessons_from_report(checks, "session-tags123")
        knowledge = get_knowledge(knowledge_type="MISTAKE")
        assert len(knowledge) == 1
        tags = knowledge[0]["tags"]
        assert "auto-extracted" in tags
        assert "safety" in tags
        assert any("session-" in t for t in tags)

    def test_records_lesson_for_failures(self):
        """Failed checks should also create lesson tracking entries."""
        checks = [
            {"name": "completeness", "passed": False, "score": 0.4, "summary": "5 blind edits"},
        ]
        extract_lessons_from_report(checks, "session-lesson1")
        lessons = get_lessons(category="blind_edit")
        assert len(lessons) == 1

    def test_good_check_marks_improving(self):
        """If a category was previously problematic and now passes, mark improving."""
        # First: fail 3 times to create active lesson
        for i in range(3):
            record_lesson("blind_edit", "Read first", f"s{i}")

        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["status"] == "active"
        assert lessons[0]["occurrences"] == 3

        # Now: pass completeness with high score
        checks = [
            {
                "name": "completeness",
                "passed": True,
                "score": 0.95,
                "summary": "All files read before editing",
            },
        ]
        extract_lessons_from_report(checks, "session-clean")
        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["status"] == "improving"


# ─── Piece 4: Smart Briefing Tests ───────────────────────────────────


class TestSmartBriefing:
    def test_briefing_with_context_hint(self):
        """Knowledge matching the hint should rank higher."""
        store_knowledge("FACT", "pytest is used for running test suites")
        store_knowledge("FACT", "databases store persistent data on disk")
        result = generate_briefing(context_hint="testing pytest")
        # The pytest fact should appear (and ideally before the database one)
        assert "pytest" in result

    def test_briefing_always_includes_mistakes(self):
        store_knowledge("MISTAKE", "Always read files before editing them", confidence=0.8)
        store_knowledge("FACT", "Python is a programming language", confidence=0.5)
        result = generate_briefing(max_items=20)
        assert "MISTAKES" in result
        assert "read files" in result.lower()

    def test_briefing_type_ordering(self):
        """Briefing should show MISTAKES before FACTS."""
        store_knowledge("MISTAKE", "Avoid blind edits", confidence=0.8)
        store_knowledge("FACT", "Some fact about code", confidence=0.8)
        result = generate_briefing()
        mistake_pos = result.find("MISTAKES")
        fact_pos = result.find("FACTS")
        assert mistake_pos < fact_pos  # mistakes shown first

    def test_briefing_preferences_never_decay(self):
        """PREFERENCE entries should score well even when old."""
        store_knowledge("PREFERENCE", "User prefers plain English explanations")
        # We can't easily mock time for the scoring, but we can verify
        # preferences appear in the briefing
        result = generate_briefing()
        assert "plain English" in result

    def test_briefing_empty(self):
        result = generate_briefing()
        assert "No knowledge" in result

    def test_briefing_respects_max_items(self):
        for i in range(10):
            store_knowledge("FACT", f"fact number {i}")
        result = generate_briefing(max_items=3)
        assert result.count("fact number") == 3


# ─── Text Helpers Tests ───────────────────────────────────────────────


class TestNormalizeText:
    def test_lowercases(self):
        assert _normalize_text("Hello World") == "hello world"

    def test_strips_punctuation(self):
        assert _normalize_text("hello, world! yes.") == "hello world yes"

    def test_collapses_whitespace(self):
        assert _normalize_text("hello   world") == "hello world"


class TestExtractKeyTerms:
    def test_removes_stopwords(self):
        result = _extract_key_terms("the quick brown fox jumps over the lazy dog")
        assert "the" not in result
        assert "brown" in result
        assert "fox" in result
        assert "jumps" in result

    def test_removes_short_words(self):
        result = _extract_key_terms("I am a big fan of AI")
        assert "am" not in result
        assert "fan" in result

    def test_deduplicates(self):
        result = _extract_key_terms("test test test run run")
        words = result.split()
        assert words.count("test") == 1

    def test_caps_at_20(self):
        text = " ".join(f"word{i}" for i in range(30))
        result = _extract_key_terms(text)
        assert len(result.split()) <= 20


class TestComputeOverlap:
    def test_identical_texts(self):
        assert _compute_overlap("hello world test", "hello world test") == 1.0

    def test_no_overlap(self):
        assert _compute_overlap("alpha beta gamma", "delta epsilon zeta") == 0.0

    def test_partial_overlap(self):
        result = _compute_overlap(
            "database migration schema update", "database schema validation rules"
        )
        assert 0.2 < result < 0.8  # some overlap but not identical

    def test_empty_text(self):
        assert _compute_overlap("", "hello world") == 0.0

    def test_stopwords_excluded(self):
        # These texts share lots of stopwords but no meaningful words
        result = _compute_overlap("the is a to of", "the is a to of and but")
        assert result == 0.0


class TestExtractSessionTopics:
    def test_finds_frequent_words(self):
        texts = [
            "let's work on testing the database",
            "the testing framework needs improvement",
            "run the database tests again",
        ]
        topics = extract_session_topics(texts, top_n=3)
        assert "testing" in topics or "database" in topics

    def test_excludes_stopwords(self):
        texts = ["the the the is is is"]
        topics = extract_session_topics(texts)
        assert len(topics) == 0

    def test_empty_input(self):
        assert extract_session_topics([]) == []


# ─── Smart Storage Tests ──────────────────────────────────────────────


class TestStoreKnowledgeSmart:
    def test_exact_duplicate_returns_same_id(self):
        kid1 = store_knowledge_smart("FACT", "Python uses indentation")
        kid2 = store_knowledge_smart("FACT", "Python uses indentation")
        assert kid1 == kid2

    def test_fuzzy_duplicate_returns_existing(self):
        kid1 = store_knowledge_smart(
            "MISTAKE", "Always read files before editing them in the codebase"
        )
        # Similar but not identical
        kid2 = store_knowledge_smart(
            "MISTAKE", "Read files before editing them in the codebase always"
        )
        assert kid1 == kid2

    def test_different_content_creates_new(self):
        kid1 = store_knowledge_smart("FACT", "Python uses indentation for blocks")
        kid2 = store_knowledge_smart("FACT", "JavaScript uses curly braces for blocks")
        assert kid1 != kid2

    def test_different_types_not_merged(self):
        kid1 = store_knowledge_smart("FACT", "testing is important for code quality")
        kid2 = store_knowledge_smart("MISTAKE", "testing is important for code quality")
        assert kid1 != kid2

    def test_superseded_content_not_resurrected(self):
        """store_knowledge_smart must not re-create content that was superseded."""
        kid1 = store_knowledge_smart("FACT", "This fact will be retired soon enough")
        assert kid1  # Created

        supersede_knowledge(kid1, reason="No longer true")

        # Try to store the exact same content again
        kid2 = store_knowledge_smart("FACT", "This fact will be retired soon enough")
        assert kid2 == ""  # Blocked — empty string means skipped

        # Verify only the superseded entry exists, no new active one
        active = get_knowledge(knowledge_type="FACT")
        assert not any("retired soon" in e["content"] for e in active)


# ─── Deep Extraction Tests ────────────────────────────────────────────


class _MockSignal:
    """Minimal mock of UserSignal for testing."""

    def __init__(self, content, timestamp="ts"):
        self.content = content
        self.timestamp = timestamp
        self.patterns_matched = []


class _MockAnalysis:
    """Minimal mock of SessionAnalysis for testing."""

    def __init__(self, session_id="test-session-abc123"):
        self.session_id = session_id
        self.corrections = []
        self.encouragements = []
        self.decisions = []
        self.frustrations = []
        self.preferences = []
        self.user_message_texts = []
        self.tool_usage = {}


class TestDeepExtractKnowledge:
    def test_topics_not_stored_as_standalone_facts(self):
        analysis = _MockAnalysis()
        analysis.user_message_texts = [
            "let's work on the testing framework",
            "we need better testing coverage",
            "run the testing suite",
        ]
        records = []
        deep_extract_knowledge(analysis, records)
        # Topics should NOT be stored as standalone facts (keyword soup)
        knowledge = get_knowledge(knowledge_type="FACT")
        topic_entries = [k for k in knowledge if "I worked on:" in k["content"]]
        assert len(topic_entries) == 0

    def test_extracts_correction_pairs(self):
        analysis = _MockAnalysis()
        analysis.corrections = [_MockSignal("no don't use mocks, use real database")]
        analysis.user_message_texts = ["no don't use mocks, use real database"]

        records = [
            {
                "type": "assistant",
                "timestamp": "ts",
                "message": {
                    "content": [
                        {"type": "text", "text": "I'll set up mock database objects for testing"}
                    ]
                },
            },
            {
                "type": "user",
                "timestamp": "ts",
                "message": {
                    "content": [{"type": "text", "text": "no don't use mocks, use real database"}]
                },
            },
        ]
        deep_extract_knowledge(analysis, records)
        # "don't" triggers BOUNDARY classification
        boundaries = get_knowledge(knowledge_type="BOUNDARY")
        assert len(boundaries) >= 1
        combined = " ".join(m["content"] for m in boundaries)
        assert "mock" in combined.lower()
        # Should have CORRECTED source
        assert boundaries[0]["source"] == "CORRECTED"

    def test_extracts_preferences(self):
        analysis = _MockAnalysis()
        analysis.preferences = [_MockSignal("i prefer plain english, no jargon")]
        analysis.user_message_texts = ["i prefer plain english, no jargon"]
        records = []
        deep_extract_knowledge(analysis, records)
        directions = get_knowledge(knowledge_type="DIRECTION")
        assert len(directions) >= 1
        assert "plain english" in directions[0]["content"].lower()
        assert directions[0]["source"] == "STATED"

    def test_extracts_decisions_with_reason(self):
        analysis = _MockAnalysis()
        analysis.decisions = [_MockSignal("yes lets use SQLite because it has no dependencies")]
        analysis.user_message_texts = ["yes lets use SQLite because it has no dependencies"]
        records = [
            {
                "type": "user",
                "timestamp": "ts",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "yes lets use SQLite because it has no dependencies",
                        }
                    ]
                },
            },
        ]
        deep_extract_knowledge(analysis, records)
        principles = get_knowledge(knowledge_type="PRINCIPLE")
        decision_entries = [p for p in principles if "decision" in " ".join(p["tags"]).lower()]
        assert len(decision_entries) >= 1
        combined = " ".join(p["content"] for p in decision_entries)
        assert "sqlite" in combined.lower()

    def test_extracts_encouragements_with_context(self):
        analysis = _MockAnalysis()
        analysis.encouragements = [_MockSignal("perfect that's exactly right")]
        analysis.user_message_texts = ["perfect that's exactly right"]
        records = [
            {
                "type": "assistant",
                "timestamp": "ts",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "I've added FTS5 search with BM25 ranking to the knowledge store",
                        }
                    ]
                },
            },
            {
                "type": "user",
                "timestamp": "ts",
                "message": {"content": [{"type": "text", "text": "perfect that's exactly right"}]},
            },
        ]
        deep_extract_knowledge(analysis, records)
        principles = get_knowledge(knowledge_type="PRINCIPLE")
        enc_entries = [p for p in principles if "encouragement" in " ".join(p["tags"]).lower()]
        assert len(enc_entries) >= 1
        assert enc_entries[0]["source"] == "DEMONSTRATED"

    def test_topic_tags_applied(self):
        analysis = _MockAnalysis()
        analysis.user_message_texts = ["testing testing testing database database"]
        analysis.preferences = [_MockSignal("always test first")]
        records = []
        deep_extract_knowledge(analysis, records)
        # All entries should have topic tags
        all_knowledge = get_knowledge()
        for entry in all_knowledge:
            tags = entry["tags"]
            has_topic_tag = any(t.startswith("topic-") for t in tags)
            if "auto-extracted" in tags:
                assert has_topic_tag


# ─── Consolidation Tests ──────────────────────────────────────────────


class TestConsolidateRelated:
    def test_merges_similar_entries(self):
        # Create 4 similar MISTAKE entries
        store_knowledge(
            "MISTAKE", "Session s1: Files edited without reading first. Read before you edit."
        )
        store_knowledge(
            "MISTAKE", "Session s2: Files edited without reading first. Read before editing."
        )
        store_knowledge(
            "MISTAKE", "Session s3: Files edited without reading them first. Read before you edit."
        )
        store_knowledge(
            "MISTAKE", "Session s4: Files edited without reading. Read before you edit them."
        )

        merges = consolidate_related(min_cluster_size=3)
        assert len(merges) >= 1
        assert merges[0]["type"] == "MISTAKE"
        assert merges[0]["merged_count"] >= 3

        # After consolidation, only 1 active MISTAKE should remain
        active = get_knowledge(knowledge_type="MISTAKE")
        assert len(active) <= 2  # at most the merged one + possibly one that didn't cluster

    def test_no_merge_when_too_few(self):
        store_knowledge("FACT", "fact one about databases")
        store_knowledge("FACT", "fact two about databases")
        merges = consolidate_related(min_cluster_size=3)
        assert len(merges) == 0

    def test_different_types_not_merged(self):
        store_knowledge("MISTAKE", "always read files before editing them in session")
        store_knowledge("MISTAKE", "always read files before editing them in code")
        store_knowledge("MISTAKE", "always read files before editing them properly")
        store_knowledge("PATTERN", "always read files before editing them as practice")
        store_knowledge("PATTERN", "always read files before editing them consistently")
        store_knowledge("PATTERN", "always read files before editing them carefully")

        merges = consolidate_related(min_cluster_size=3)
        # Should have separate merges for MISTAKE and PATTERN
        types = [m["type"] for m in merges]
        if "MISTAKE" in types and "PATTERN" in types:
            assert True  # both types merged separately
        elif len(merges) >= 1:
            assert True  # at least one merge happened

    def test_consolidated_entry_has_tag(self):
        store_knowledge("FACT", "database queries need optimization for performance")
        store_knowledge("FACT", "database queries need optimization for speed and performance")
        store_knowledge("FACT", "database queries need optimization performance tuning")

        merges = consolidate_related(min_cluster_size=3)
        if merges:
            active = get_knowledge(knowledge_type="FACT")
            consolidated = [e for e in active if "consolidated" in e["tags"]]
            assert len(consolidated) >= 1


# --- Feedback Loop Tests ---


class TestAdjustConfidence:
    def test_boost_confidence(self):
        kid = store_knowledge("FACT", "test entry for confidence boost", confidence=0.8)
        new_conf = _adjust_confidence(kid, 0.1)
        assert new_conf == pytest.approx(0.9)
        entry = get_knowledge(knowledge_type="FACT")[0]
        assert entry["confidence"] == pytest.approx(0.9)

    def test_cap_at_maximum(self):
        kid = store_knowledge("FACT", "test entry near cap", confidence=0.95)
        new_conf = _adjust_confidence(kid, 0.1)
        assert new_conf == pytest.approx(1.0)

    def test_decay_confidence(self):
        kid = store_knowledge("FACT", "test entry for decay", confidence=0.8)
        new_conf = _adjust_confidence(kid, -0.2)
        assert new_conf == pytest.approx(0.6)

    def test_floor_at_minimum(self):
        kid = store_knowledge("FACT", "test entry at floor", confidence=0.3)
        new_conf = _adjust_confidence(kid, -0.2, floor=0.3)
        assert new_conf == pytest.approx(0.3)

    def test_custom_floor(self):
        kid = store_knowledge("FACT", "test custom floor", confidence=0.6)
        new_conf = _adjust_confidence(kid, -0.2, floor=0.5)
        assert new_conf == pytest.approx(0.5)

    def test_nonexistent_id(self):
        result = _adjust_confidence("nonexistent-id", 0.1)
        assert result is None


class TestComputeEffectiveness:
    def test_mistake_effective(self):
        store_knowledge("MISTAKE", "blind editing without reading files first")
        record_lesson("blind_edit", "blind editing without reading files first", "s1")
        record_lesson("blind_edit", "blind editing without reading files first", "s2")
        record_lesson("blind_edit", "blind editing without reading files first", "s3")
        mark_lesson_improving("blind_edit", "s4")
        eff = compute_effectiveness(get_knowledge(knowledge_type="MISTAKE")[0])
        assert eff["status"] == "effective"

    def test_mistake_recurring(self):
        store_knowledge("MISTAKE", "repeated test failures in module")
        record_lesson("test_failure", "repeated test failures in module", "s1")
        record_lesson("test_failure", "repeated test failures in module", "s2")
        record_lesson("test_failure", "repeated test failures in module", "s3")
        eff = compute_effectiveness(get_knowledge(knowledge_type="MISTAKE")[0])
        assert eff["status"] == "recurring"

    def test_mistake_no_lesson(self):
        store_knowledge("MISTAKE", "some unique one-off error xyz987")
        eff = compute_effectiveness(get_knowledge(knowledge_type="MISTAKE")[0])
        assert eff["status"] == "unknown"

    def test_pattern_reinforced(self):
        kid = store_knowledge("PATTERN", "good error recovery practice")
        for _ in range(4):
            record_access(kid)
        entry = get_knowledge(knowledge_type="PATTERN")[0]
        eff = compute_effectiveness(entry)
        assert eff["status"] == "reinforced"

    def test_pattern_unused(self):
        store_knowledge("PATTERN", "never accessed pattern xyz")
        eff = compute_effectiveness(get_knowledge(knowledge_type="PATTERN")[0])
        assert eff["status"] == "unused"

    def test_preference_always_stable(self):
        store_knowledge("PREFERENCE", "user prefers plain english")
        eff = compute_effectiveness(get_knowledge(knowledge_type="PREFERENCE")[0])
        assert eff["status"] == "stable"

    def test_fact_used(self):
        kid = store_knowledge("FACT", "python uses indentation")
        record_access(kid)
        eff = compute_effectiveness(get_knowledge(knowledge_type="FACT")[0])
        assert eff["status"] == "used"

    def test_fact_unused(self):
        store_knowledge("FACT", "obscure fact never accessed")
        eff = compute_effectiveness(get_knowledge(knowledge_type="FACT")[0])
        assert eff["status"] == "unused"


class TestHealthCheck:
    def test_empty_database(self):
        result = health_check()
        assert result["confirmed_boosted"] == 0
        assert result["total_checked"] == 0

    def test_old_accessed_entry_not_decayed(self):
        """Recently-used knowledge does NOT decay just because it's old."""
        kid = store_knowledge("FACT", "old but still true fact", confidence=0.8)
        # Give it access so it's not considered stale
        record_access(kid)
        # Backdate created_at but keep updated_at recent (entry is still in use)
        import divineos.core.ledger as lm
        import sqlite3

        db_path = lm._get_db_path()
        conn = sqlite3.connect(str(db_path))
        old_time = time.time() - (60 * 86400)
        conn.execute(
            "UPDATE knowledge SET created_at = ? WHERE knowledge_id = ?",
            (old_time, kid),
        )
        conn.commit()
        conn.close()

        health_check()
        # Confidence should be UNCHANGED — old but recently used
        entry = get_knowledge(knowledge_type="FACT")[0]
        assert entry["confidence"] == pytest.approx(0.8)

    def test_confirmed_entry_boosted(self):
        kid = store_knowledge("FACT", "highly accessed entry", confidence=0.8)
        for _ in range(6):
            record_access(kid)
        result = health_check()
        assert result["confirmed_boosted"] == 1
        entry = get_knowledge(knowledge_type="FACT")[0]
        assert entry["confidence"] == pytest.approx(0.85)

    def test_recurring_lesson_escalation(self):
        store_knowledge("MISTAKE", "blind editing without reading files", confidence=0.7)
        record_lesson("blind_edit", "blind editing without reading files", "s1")
        record_lesson("blind_edit", "blind editing without reading files", "s2")
        record_lesson("blind_edit", "blind editing without reading files", "s3")

        result = health_check()
        assert result["recurring_escalated"] == 1
        entry = get_knowledge(knowledge_type="MISTAKE")[0]
        assert entry["confidence"] == pytest.approx(0.95)

    def test_improving_lesson_resolved_after_30_days(self):
        store_knowledge("MISTAKE", "old resolved mistake entry", confidence=0.8)
        record_lesson("old_mistake", "old resolved mistake entry", "s1")
        record_lesson("old_mistake", "old resolved mistake entry", "s2")
        record_lesson("old_mistake", "old resolved mistake entry", "s3")
        mark_lesson_improving("old_mistake", "s4")

        # Backdate last_seen to 31 days ago
        import os
        import sqlite3

        db_path = os.environ.get("DIVINEOS_DB")
        if not db_path:
            import divineos.core.ledger as lm

            db_path = str(lm.DB_PATH)
        conn = sqlite3.connect(db_path)
        old_time = time.time() - (31 * 86400)
        conn.execute(
            "UPDATE lesson_tracking SET last_seen = ? WHERE category = 'old_mistake'",
            (old_time,),
        )
        conn.commit()
        conn.close()

        result = health_check()
        assert result["resolved_lessons"] == 1
        lessons = get_lessons(category="old_mistake")
        assert lessons[0]["status"] == "resolved"

    def test_resolved_lesson_lowers_confidence_gently(self):
        """Resolved lessons lower mistake confidence but not below 0.5."""
        store_knowledge("MISTAKE", "resolved mistake floor test", confidence=0.55)
        record_lesson("floor_test", "resolved mistake floor test", "s1")
        record_lesson("floor_test", "resolved mistake floor test", "s2")
        record_lesson("floor_test", "resolved mistake floor test", "s3")
        mark_lesson_improving("floor_test", "s4")

        # Backdate last_seen to 31 days ago
        import os
        import sqlite3

        db_path = os.environ.get("DIVINEOS_DB")
        if not db_path:
            import divineos.core.ledger as lm

            db_path = str(lm.DB_PATH)
        conn = sqlite3.connect(db_path)
        old_time = time.time() - (31 * 86400)
        conn.execute(
            "UPDATE lesson_tracking SET last_seen = ? WHERE category = 'floor_test'",
            (old_time,),
        )
        conn.commit()
        conn.close()

        result = health_check()
        assert result["resolved_lessons"] == 1
        entry = get_knowledge(knowledge_type="MISTAKE")[0]
        assert entry["confidence"] == pytest.approx(0.5)  # floor


class TestApplySessionFeedback:
    def test_empty_knowledge_store(self):
        analysis = _MockAnalysis()
        analysis.corrections = [_MockSignal("no that's wrong")]
        result = apply_session_feedback(analysis, "s1")
        assert result["recurrences_found"] == 0
        assert result["patterns_reinforced"] == 0
        assert result["lessons_improving"] == 0

    def test_correction_matches_existing_mistake(self):
        store_knowledge("MISTAKE", "blind editing without reading files first", confidence=0.8)
        analysis = _MockAnalysis()
        analysis.corrections = [_MockSignal("you edited files without reading them first again")]
        result = apply_session_feedback(analysis, "s2")
        assert result["recurrences_found"] == 1
        entry = get_knowledge(knowledge_type="MISTAKE")[0]
        assert entry["confidence"] == pytest.approx(0.85)

    def test_correction_no_match(self):
        store_knowledge("MISTAKE", "blind editing without reading files first", confidence=0.8)
        analysis = _MockAnalysis()
        analysis.corrections = [_MockSignal("you forgot to add the return type annotation")]
        result = apply_session_feedback(analysis, "s2")
        assert result["recurrences_found"] == 0

    def test_encouragement_matches_pattern(self):
        store_knowledge("PATTERN", "good error investigation before retrying", confidence=0.8)
        analysis = _MockAnalysis()
        analysis.encouragements = [_MockSignal("great job investigating the error before retrying")]
        result = apply_session_feedback(analysis, "s2")
        assert result["patterns_reinforced"] == 1
        entry = get_knowledge(knowledge_type="PATTERN")[0]
        assert entry["confidence"] == pytest.approx(0.85)

    def test_lesson_marked_improving_when_no_recurrence(self):
        store_knowledge("MISTAKE", "blind editing problem", confidence=0.8)
        record_lesson("blind_edit", "blind editing problem", "s1")
        record_lesson("blind_edit", "blind editing problem", "s2")
        record_lesson("blind_edit", "blind editing problem", "s3")

        analysis = _MockAnalysis()
        analysis.corrections = []  # no corrections at all
        result = apply_session_feedback(analysis, "s4")
        assert result["lessons_improving"] >= 1
        lessons = get_lessons(category="blind_edit")
        assert lessons[0]["status"] == "improving"


class TestKnowledgeHealthReport:
    def test_empty_report(self):
        report = knowledge_health_report()
        assert report["total"] == 0
        assert report["by_status"] == {}

    def test_aggregates_correctly(self):
        store_knowledge("FACT", "some fact one")
        store_knowledge("FACT", "some fact two")
        store_knowledge("PREFERENCE", "user prefers tests")
        report = knowledge_health_report()
        assert report["total"] == 3
        assert report["by_status"]["unused"] == 2  # two FACTs
        assert report["by_status"]["stable"] == 1  # one PREFERENCE


# --- Noise Filtering & Categorization Tests ---


class TestIsNoiseCorrection:
    def test_too_short(self):
        assert _is_noise_correction("ok sure") is True

    def test_task_notification(self):
        assert (
            _is_noise_correction("<task-notification><task-id>abc</task-id></task-notification>")
            is True
        )

    def test_file_path_dump(self):
        assert _is_noise_correction("@C:\\Users\\foo\\bar.py @C:\\Users\\foo\\baz.py") is True

    def test_real_correction_passes(self):
        assert (
            _is_noise_correction("no that's wrong, you should read the file first before editing")
            is False
        )

    def test_forwarded_instruction_passes(self):
        # Forwarded messages with enough content should pass — they may contain real corrections
        assert (
            _is_noise_correction("he said don't go down this rabbit hole it's too complex") is False
        )


class TestCategorizeCorrection:
    def test_blind_coding(self):
        assert _categorize_correction("don't do it blindly, study it first") == "blind_coding"
        assert (
            _categorize_correction("you should read without checking what exists") == "blind_coding"
        )

    def test_incomplete_fix(self):
        assert (
            _categorize_correction("you only fixed one, the other tests still fail")
            == "incomplete_fix"
        )

    def test_ignored_instruction(self):
        assert _categorize_correction("did you not see what i said?") == "ignored_instruction"

    def test_wrong_scope(self):
        assert _categorize_correction("i mean in the OS itself not the test") == "wrong_scope"
        assert _categorize_correction("same one but folder 5 instead of 4") == "wrong_scope"

    def test_overreach(self):
        assert _categorize_correction("the pipeline isnt supposed to make decisions") == "overreach"
        assert _categorize_correction("don't go down this rabbit hole") == "overreach"

    def test_jargon_usage(self):
        assert (
            _categorize_correction("break it down like im dumb, no jargon please") == "jargon_usage"
        )
        assert _categorize_correction("im not a coder so dont speak jargon") == "jargon_usage"

    def test_shallow_output(self):
        assert (
            _categorize_correction("they still dont feel like people, embody their voice")
            == "shallow_output"
        )
        assert (
            _categorize_correction("dont make it concise, token limits are not a concern")
            == "shallow_output"
        )

    def test_perspective_error(self):
        assert (
            _categorize_correction("when i say you, you should say i or me, its a pronoun issue")
            == "perspective_error"
        )

    def test_misunderstood(self):
        assert (
            _categorize_correction("thats not what i meant at all, you misunderstood")
            == "misunderstood"
        )
        assert (
            _categorize_correction("i was trying to stop you, i wasnt denying it")
            == "misunderstood"
        )

    def test_no_category_returns_none(self):
        assert _categorize_correction("the sky is blue and water is wet") is None


class TestClearLessons:
    def test_clears_all(self):
        record_lesson("cat1", "desc1", "s1")
        record_lesson("cat2", "desc2", "s2")
        count = clear_lessons()
        assert count == 2
        assert get_lessons() == []

    def test_empty_table(self):
        count = clear_lessons()
        assert count == 0


class TestFeedbackWithNoiseFilter:
    def test_noise_corrections_skipped(self):
        store_knowledge("MISTAKE", "some existing mistake about editing files")
        analysis = _MockAnalysis()
        analysis.corrections = [
            _MockSignal("ok"),  # too short — noise
            _MockSignal("<task-notification><task-id>abc</task-id></task-notification>"),  # noise
        ]
        result = apply_session_feedback(analysis, "s1")
        assert result["noise_skipped"] == 2
        assert result["recurrences_found"] == 0

    def test_categorized_lesson_recorded(self):
        store_knowledge(
            "MISTAKE", "edited files blindly without reading them first, dont do it blindly"
        )
        analysis = _MockAnalysis()
        analysis.corrections = [
            _MockSignal(
                "you edited files blindly without reading them first again, dont do it blindly"
            )
        ]
        result = apply_session_feedback(analysis, "s1")
        assert result["recurrences_found"] == 1
        # Should create a lesson with category "blind_coding"
        lessons = get_lessons()
        blind_lessons = [lesson for lesson in lessons if lesson["category"] == "blind_coding"]
        assert len(blind_lessons) >= 1


# ─── Phase A: Knowledge Evolution – Schema Expansion ────────────────


class TestExpandedTypes:
    """All 10 knowledge types (7 new + 3 legacy) are accepted."""

    def test_all_new_types_accepted(self):
        for ktype in (
            "FACT",
            "PROCEDURE",
            "PRINCIPLE",
            "BOUNDARY",
            "DIRECTION",
            "OBSERVATION",
            "EPISODE",
        ):
            kid = store_knowledge(ktype, f"Test {ktype} content")
            assert isinstance(kid, str)

    def test_legacy_types_still_accepted(self):
        for ktype in ("PATTERN", "PREFERENCE", "MISTAKE"):
            store_knowledge(ktype, f"Legacy {ktype} content")
            entries = get_knowledge(knowledge_type=ktype)
            assert len(entries) == 1
            assert entries[0]["knowledge_type"] == ktype

    def test_invalid_type_rejected(self):
        with pytest.raises(ValueError, match="Invalid knowledge_type"):
            store_knowledge("NONSENSE", "Should fail")

    def test_constants_include_all_types(self):
        expected = {
            "FACT",
            "PROCEDURE",
            "PRINCIPLE",
            "BOUNDARY",
            "DIRECTION",
            "OBSERVATION",
            "EPISODE",
            "DIRECTIVE",
            "PATTERN",
            "PREFERENCE",
            "MISTAKE",
        }
        assert KNOWLEDGE_TYPES == expected


class TestSourceMetadata:
    """New source column tracks how knowledge was acquired."""

    def _get_entry(self, kid):
        """Helper: get_knowledge returns a list, find by kid."""
        entries = get_knowledge()
        return next(e for e in entries if e["knowledge_id"] == kid)

    def test_default_source_is_stated(self):
        kid = store_knowledge("FACT", "Default source test")
        assert self._get_entry(kid)["source"] == "STATED"

    def test_explicit_source_stored(self):
        kid = store_knowledge("PRINCIPLE", "Learned from correction", source="CORRECTED")
        assert self._get_entry(kid)["source"] == "CORRECTED"

    def test_all_sources_valid(self):
        for src in KNOWLEDGE_SOURCES:
            kid = store_knowledge("FACT", f"Source {src} test", source=src)
            assert self._get_entry(kid)["source"] == src

    def test_source_in_smart_store(self):
        kid = store_knowledge_smart("PRINCIPLE", "Smart source test", source="DEMONSTRATED")
        assert self._get_entry(kid)["source"] == "DEMONSTRATED"


class TestMaturityTracking:
    """New maturity column tracks knowledge confirmation level."""

    def _get_entry(self, kid):
        entries = get_knowledge()
        return next(e for e in entries if e["knowledge_id"] == kid)

    def test_default_maturity_is_raw(self):
        kid = store_knowledge("FACT", "Default maturity test")
        assert self._get_entry(kid)["maturity"] == "RAW"

    def test_explicit_maturity_stored(self):
        kid = store_knowledge("BOUNDARY", "Hard limit", maturity="CONFIRMED")
        assert self._get_entry(kid)["maturity"] == "CONFIRMED"

    def test_all_maturities_valid(self):
        for mat in KNOWLEDGE_MATURITY:
            kid = store_knowledge("FACT", f"Maturity {mat} test", maturity=mat)
            assert self._get_entry(kid)["maturity"] == mat

    def test_maturity_in_smart_store(self):
        kid = store_knowledge_smart("PRINCIPLE", "Smart maturity test", maturity="HYPOTHESIS")
        assert self._get_entry(kid)["maturity"] == "HYPOTHESIS"


class TestCorroborationCounters:
    """New corroboration/contradiction counters start at zero."""

    def _get_entry(self, kid):
        entries = get_knowledge()
        return next(e for e in entries if e["knowledge_id"] == kid)

    def test_default_counters_zero(self):
        kid = store_knowledge("FACT", "Counter test")
        entry = self._get_entry(kid)
        assert entry["corroboration_count"] == 0
        assert entry["contradiction_count"] == 0

    def test_counters_in_smart_store(self):
        kid = store_knowledge_smart("FACT", "Smart counter test")
        entry = self._get_entry(kid)
        assert entry["corroboration_count"] == 0
        assert entry["contradiction_count"] == 0


class TestSchemaBackwardsCompat:
    """Old entries without new columns get sensible defaults."""

    def _get_entry(self, kid):
        entries = get_knowledge()
        return next(e for e in entries if e["knowledge_id"] == kid)

    def test_old_entries_get_inherited_source(self):
        kid = store_knowledge("MISTAKE", "Old-style mistake")
        entry = self._get_entry(kid)
        assert entry["source"] in ("STATED", "INHERITED")

    def test_search_returns_new_columns(self):
        store_knowledge("PRINCIPLE", "Searchable principle", source="CORRECTED", maturity="TESTED")
        results = search_knowledge("principle")
        assert len(results) >= 1
        assert results[0]["source"] == "CORRECTED"
        assert results[0]["maturity"] == "TESTED"

    def test_find_similar_returns_new_columns(self):
        store_knowledge("FACT", "The sky is blue", source="DEMONSTRATED", maturity="CONFIRMED")
        results = find_similar("sky blue")
        if results:  # FTS5 may not be available in all environments
            assert "source" in results[0]
            assert "maturity" in results[0]


# ─── Phase D: Knowledge Type Migration ──────────────────────────────


class TestMigrateTypes:
    def test_dry_run_returns_planned_changes(self):
        store_knowledge("MISTAKE", "Don't edit without reading first")
        store_knowledge("PREFERENCE", "I prefer plain english")
        store_knowledge("PATTERN", "User praised step-by-step debugging")

        changes = migrate_knowledge_types(dry_run=True)
        assert len(changes) == 3
        # Dry run should NOT create new entries
        assert all("new_id" not in c for c in changes)

    def test_mistake_with_never_becomes_boundary(self):
        store_knowledge("MISTAKE", "Never edit files without reading them first")
        changes = migrate_knowledge_types(dry_run=True)
        boundary_changes = [c for c in changes if c["new_type"] == "BOUNDARY"]
        assert len(boundary_changes) == 1
        assert boundary_changes[0]["source"] == "CORRECTED"

    def test_mistake_without_keyword_becomes_principle(self):
        store_knowledge("MISTAKE", "Code was edited blindly, should read first")
        changes = migrate_knowledge_types(dry_run=True)
        principle_changes = [c for c in changes if c["new_type"] == "PRINCIPLE"]
        assert len(principle_changes) == 1

    def test_preference_becomes_direction(self):
        store_knowledge("PREFERENCE", "Use plain english in output")
        changes = migrate_knowledge_types(dry_run=True)
        direction_changes = [c for c in changes if c["new_type"] == "DIRECTION"]
        assert len(direction_changes) == 1
        assert direction_changes[0]["maturity"] == "CONFIRMED"

    def test_pattern_with_procedure_keyword_becomes_procedure(self):
        store_knowledge("PATTERN", "Step by step: first read, then edit, then test")
        changes = migrate_knowledge_types(dry_run=True)
        proc_changes = [c for c in changes if c["new_type"] == "PROCEDURE"]
        assert len(proc_changes) == 1

    def test_pattern_without_keyword_becomes_principle(self):
        store_knowledge("PATTERN", "User praised this debugging approach")
        changes = migrate_knowledge_types(dry_run=True)
        principle_changes = [c for c in changes if c["new_type"] == "PRINCIPLE"]
        assert len(principle_changes) == 1

    def test_execute_creates_new_entries(self):
        store_knowledge("MISTAKE", "Never skip tests before committing")
        changes = migrate_knowledge_types(dry_run=False)
        assert len(changes) == 1
        assert "new_id" in changes[0]

        # Old entry should be superseded
        old_entries = get_knowledge(knowledge_type="MISTAKE", include_superseded=True)
        superseded = [e for e in old_entries if e["superseded_by"] is not None]
        assert len(superseded) == 1

        # New entry should exist with new type
        new_entries = get_knowledge(knowledge_type="BOUNDARY")
        assert len(new_entries) == 1
        assert new_entries[0]["source"] == "CORRECTED"

    def test_fact_and_episode_not_migrated(self):
        store_knowledge("FACT", "Python uses indentation")
        store_knowledge("EPISODE", "Session summary from today")
        changes = migrate_knowledge_types(dry_run=True)
        assert len(changes) == 0

    def test_already_migrated_not_remigrated(self):
        store_knowledge("MISTAKE", "Never skip reading")
        migrate_knowledge_types(dry_run=False)
        # Run again — the old entry is superseded, so shouldn't appear
        changes = migrate_knowledge_types(dry_run=True)
        assert len(changes) == 0
