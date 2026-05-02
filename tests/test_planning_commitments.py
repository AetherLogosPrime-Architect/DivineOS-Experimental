"""Tests for Planning Commitments — track promises, check fulfillment."""

from divineos.core.planning_commitments import (
    Commitment,
    add_commitment,
    check_fulfillment,
    clear_commitments,
    detect_commitments,
    format_commitment_review,
    fulfill_commitment,
    get_pending_commitments,
    review_commitments,
)


class TestCommitmentDetection:
    """Detect when the agent makes promises."""

    def test_detects_ill_fix(self):
        text = "I'll fix the import error in the test file"
        result = detect_commitments(text)
        assert len(result) == 1
        assert "fix" in result[0].lower()

    def test_detects_let_me(self):
        text = "Let me add the missing validation to the form handler"
        result = detect_commitments(text)
        assert len(result) == 1

    def test_detects_next_ill(self):
        text = "Next I'll implement the caching layer for the API"
        result = detect_commitments(text)
        assert len(result) == 1

    def test_detects_need_to(self):
        text = "I need to update the tests to cover the edge case"
        result = detect_commitments(text)
        assert len(result) == 1

    def test_detects_multiple_commitments(self):
        text = "I'll fix the bug first. Then I'll add the new test. After that I'll refactor the module"
        result = detect_commitments(text)
        assert len(result) == 3

    def test_ignores_non_commitment(self):
        text = "The test passed successfully"
        result = detect_commitments(text)
        assert len(result) == 0

    def test_ignores_short_text(self):
        result = detect_commitments("ok")
        assert len(result) == 0

    def test_ignores_empty(self):
        result = detect_commitments("")
        assert len(result) == 0

    def test_truncates_long_sentences(self):
        text = "I'll fix " + "x" * 250
        result = detect_commitments(text)
        assert len(result) == 1
        assert len(result[0]) <= 200

    def test_detects_should(self):
        text = "I should also handle the edge case where input is None"
        result = detect_commitments(text)
        assert len(result) == 1

    def test_detects_plan_is_to(self):
        text = "My plan is to restructure the module into smaller pieces"
        result = detect_commitments(text)
        assert len(result) == 1


class TestCommitmentStorage:
    """Store and retrieve commitments."""

    def test_add_and_get(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix the import error")
        pending = get_pending_commitments()
        assert len(pending) == 1
        assert pending[0].text == "Fix the import error"
        assert pending[0].status == "pending"

    def test_deduplicates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix the import error")
        add_commitment("Fix the import error")
        pending = get_pending_commitments()
        assert len(pending) == 1

    def test_fulfill_by_text(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix the import error in tests")
        result = fulfill_commitment("Fixed the import error in the tests")
        assert result is True
        pending = get_pending_commitments()
        assert len(pending) == 0

    def test_fulfill_no_match(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix the import error")
        result = fulfill_commitment("Completely unrelated task")
        assert result is False
        pending = get_pending_commitments()
        assert len(pending) == 1

    def test_clear_commitments(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix something")
        clear_commitments()
        pending = get_pending_commitments()
        assert len(pending) == 0

    def test_context_stored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        c = add_commitment("Fix the bug", context="While reviewing test output")
        assert c.context == "While reviewing test output"


class TestCommitmentModel:
    """Commitment dataclass behavior."""

    def test_fulfill(self):
        c = Commitment(text="Do the thing")
        c.fulfill()
        assert c.status == "fulfilled"
        assert c.fulfilled_at is not None

    def test_drop(self):
        c = Commitment(text="Do the thing")
        c.drop("Ran out of time")
        assert c.status == "dropped"
        assert c.context == "Ran out of time"

    def test_defer(self):
        c = Commitment(text="Do the thing")
        c.defer()
        assert c.status == "deferred"


class TestFulfillmentCheck:
    """Check whether a commitment was carried out."""

    def test_fulfilled_with_matching_event(self):
        result = check_fulfillment(
            "Fix the import error in test_utils",
            ["Fixed import error in test_utils — all tests passing"],
        )
        assert result["likely_fulfilled"] is True
        assert result["confidence"] > 0.3

    def test_not_fulfilled_no_match(self):
        result = check_fulfillment(
            "Fix the import error in test_utils",
            ["Updated the README with new badges"],
        )
        assert result["likely_fulfilled"] is False

    def test_not_fulfilled_empty_events(self):
        result = check_fulfillment("Fix the bug", [])
        assert result["likely_fulfilled"] is False
        assert result["matching_event"] is None

    def test_fulfillment_signal_boosts_score(self):
        # "done" and "completed" should boost the signal
        result = check_fulfillment(
            "Add validation to the form",
            ["Validation for form inputs done and working"],
        )
        assert result["likely_fulfilled"] is True

    def test_partial_match_not_enough(self):
        result = check_fulfillment(
            "Refactor the database connection pooling layer",
            ["Updated the form validation CSS"],
        )
        assert result["likely_fulfilled"] is False


class TestReviewCommitments:
    """Session-end commitment review."""

    def test_review_with_fulfilled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix the import error in tests")
        review = review_commitments(session_events=["Fixed import error in tests — passing now"])
        assert review["total"] == 1
        assert review["fulfilled"] == 1
        assert review["dropped"] == 0

    def test_review_with_dropped(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Refactor the entire database layer")
        review = review_commitments(session_events=["Updated the README"])
        assert review["total"] == 1
        assert review["fulfilled"] == 0
        assert review["dropped"] == 1

    def test_review_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        review = review_commitments()
        assert review["total"] == 0

    def test_review_mixed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_commitment("Fix import error")
        add_commitment("Rewrite the entire codebase from scratch")
        review = review_commitments(session_events=["Fixed import error in module — tests pass"])
        assert review["total"] == 2
        assert review["fulfilled"] == 1
        assert review["dropped"] == 1


class TestFormatCommitmentReview:
    """Display formatting."""

    def test_format_empty(self):
        review = {"total": 0, "fulfilled": 0, "dropped": 0, "deferred": 0, "details": []}
        assert format_commitment_review(review) == ""

    def test_format_fulfilled(self):
        review = {
            "total": 1,
            "fulfilled": 1,
            "dropped": 0,
            "deferred": 0,
            "details": [
                {
                    "text": "Fix the bug",
                    "status": "fulfilled",
                    "confidence": 0.8,
                    "matching_event": "Fixed the bug",
                }
            ],
        }
        output = format_commitment_review(review)
        assert "1/1 fulfilled" in output
        assert "FULFILLED" in output
        assert "+" in output

    def test_format_dropped(self):
        review = {
            "total": 1,
            "fulfilled": 0,
            "dropped": 1,
            "deferred": 0,
            "details": [
                {
                    "text": "Rewrite everything",
                    "status": "dropped",
                    "confidence": 0.0,
                    "matching_event": None,
                }
            ],
        }
        output = format_commitment_review(review)
        assert "0/1 fulfilled" in output
        assert "DROPPED" in output
        assert "x" in output
        assert "not fulfilled" in output

    def test_format_truncates_long_text(self):
        review = {
            "total": 1,
            "fulfilled": 1,
            "dropped": 0,
            "deferred": 0,
            "details": [
                {
                    "text": "A" * 200,
                    "status": "fulfilled",
                    "confidence": 0.9,
                    "matching_event": "done",
                }
            ],
        }
        output = format_commitment_review(review)
        assert "..." in output
