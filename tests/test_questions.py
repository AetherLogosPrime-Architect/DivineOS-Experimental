"""Tests for the open questions system."""

import pytest

from divineos.core.questions import (
    abandon_question,
    add_question,
    answer_question,
    check_auto_answers,
    get_open_questions_summary,
    get_questions,
    init_questions_table,
)


@pytest.fixture(autouse=True)
def _temp_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DIVINEOS_DB", db_path)
    from divineos.core.knowledge import init_knowledge_table

    init_knowledge_table()
    init_questions_table()
    yield


class TestAddQuestion:
    def test_add_returns_uuid(self):
        qid = add_question("Why does X happen?")
        assert len(qid) == 36  # UUID format

    def test_add_with_context(self):
        add_question("Why does X happen?", context="Saw it during testing")
        questions = get_questions()
        assert len(questions) == 1
        assert questions[0]["context"] == "Saw it during testing"

    def test_add_with_tags(self):
        add_question("Why does X happen?", tags=["testing", "bugs"])
        questions = get_questions()
        assert questions[0]["tags"] == ["testing", "bugs"]

    def test_add_default_status_open(self):
        add_question("Why?")
        questions = get_questions()
        assert questions[0]["status"] == "OPEN"


class TestGetQuestions:
    def test_empty_returns_empty(self):
        assert get_questions() == []

    def test_returns_all_by_default(self):
        add_question("Q1")
        add_question("Q2")
        add_question("Q3")
        assert len(get_questions()) == 3

    def test_filter_by_status(self):
        q1 = add_question("Q1")
        add_question("Q2")
        answer_question(q1, "Because A")
        assert len(get_questions(status="OPEN")) == 1
        assert len(get_questions(status="ANSWERED")) == 1

    def test_limit(self):
        for i in range(10):
            add_question(f"Question {i}")
        assert len(get_questions(limit=5)) == 5

    def test_ordered_by_recency(self):
        add_question("Old question")
        add_question("New question")
        questions = get_questions()
        assert "New" in questions[0]["question"]


class TestAnswerQuestion:
    def test_answer_marks_answered(self):
        qid = add_question("Why X?")
        result = answer_question(qid, "Because Y")
        assert result is True
        questions = get_questions(status="ANSWERED")
        assert len(questions) == 1
        assert questions[0]["resolution"] == "Because Y"
        assert questions[0]["resolved_at"] is not None

    def test_answer_nonexistent_returns_false(self):
        assert answer_question("nonexistent-id", "answer") is False


class TestAbandonQuestion:
    def test_abandon_marks_abandoned(self):
        qid = add_question("Why X?")
        result = abandon_question(qid, "No longer relevant")
        assert result is True
        questions = get_questions(status="ABANDONED")
        assert len(questions) == 1
        assert questions[0]["resolution"] == "No longer relevant"

    def test_abandon_without_reason(self):
        qid = add_question("Why X?")
        abandon_question(qid)
        questions = get_questions(status="ABANDONED")
        assert questions[0]["resolution"] == "abandoned"

    def test_abandon_nonexistent_returns_false(self):
        assert abandon_question("nonexistent-id") is False


class TestAutoAnswers:
    def test_finds_matching_question(self):
        add_question("How does the database connection pooling work?")
        candidates = check_auto_answers(
            "The database connection pooling uses a shared pool with max 10 connections",
            "new-knowledge-id",
            threshold=0.3,
        )
        assert len(candidates) >= 1
        assert candidates[0]["question"].startswith("How does")

    def test_ignores_low_overlap(self):
        add_question("How does the database connection pooling work?")
        candidates = check_auto_answers(
            "The weather is sunny today",
            "new-knowledge-id",
            threshold=0.4,
        )
        assert len(candidates) == 0

    def test_ignores_answered_questions(self):
        qid = add_question("How does X work?")
        answer_question(qid, "Like this")
        candidates = check_auto_answers(
            "X works by doing Y and Z",
            "new-knowledge-id",
            threshold=0.2,
        )
        assert len(candidates) == 0


class TestSummary:
    def test_empty_returns_empty_string(self):
        assert get_open_questions_summary() == ""

    def test_formats_questions(self):
        add_question("How does X work?")
        add_question("Why is Y slow?")
        summary = get_open_questions_summary()
        assert "OPEN QUESTIONS" in summary
        assert "How does X work?" in summary
        assert "Why is Y slow?" in summary

    def test_truncates_long_questions(self):
        add_question("A" * 200)
        summary = get_open_questions_summary()
        assert "..." in summary

    def test_respects_max_items(self):
        for i in range(10):
            add_question(f"Question number {i}")
        summary = get_open_questions_summary(max_items=3)
        assert "...and more" in summary
