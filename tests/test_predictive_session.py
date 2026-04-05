"""Tests for Predictive Session Model — anticipate user needs."""

from divineos.core.predictive_session import (
    detect_recurring_patterns,
    detect_session_profile,
    format_predictions,
    predict_session_needs,
)


class TestSessionProfileDetection:
    """Classify sessions by activity type."""

    def test_detects_build_session(self):
        events = ["Create new module", "Add function to handler", "Implement the cache layer"]
        result = detect_session_profile(events)
        assert result["profile"] == "build"
        assert result["confidence"] > 0

    def test_detects_fix_session(self):
        events = ["Fix import error", "Bug in the test file", "Error handling broken"]
        result = detect_session_profile(events)
        assert result["profile"] == "fix"

    def test_detects_test_session(self):
        events = ["Run pytest", "Add assert for edge case", "Verify coverage"]
        result = detect_session_profile(events)
        assert result["profile"] == "test"

    def test_detects_refactor_session(self):
        events = ["Refactor the module", "Extract helper function", "Clean up imports"]
        result = detect_session_profile(events)
        assert result["profile"] == "refactor"

    def test_detects_review_session(self):
        events = ["Audit the codebase", "Review test coverage", "Inspect the output"]
        result = detect_session_profile(events)
        assert result["profile"] == "review"

    def test_detects_explore_session(self):
        events = ["Research cognitive architectures", "Explore the API", "Investigate the bug"]
        result = detect_session_profile(events)
        assert result["profile"] == "explore"

    def test_unknown_for_empty_events(self):
        result = detect_session_profile([])
        assert result["profile"] == "unknown"
        assert result["confidence"] == 0.0

    def test_unknown_for_unrecognizable(self):
        result = detect_session_profile(["hello world", "goodbye"])
        assert result["profile"] == "unknown"

    def test_typical_next_included(self):
        events = ["Create new module", "Build the handler"]
        result = detect_session_profile(events)
        assert "typical_next" in result
        if result["profile"] == "build":
            assert "test" in result["typical_next"]

    def test_confidence_capped_at_one(self):
        events = ["fix bug fix error fix broken fix fail fix patch"] * 10
        result = detect_session_profile(events)
        assert result["confidence"] <= 1.0


class TestRecurringPatterns:
    """Detect patterns across session history."""

    def test_detects_recurring_activity(self):
        history = [
            {"content": "Fixed 3 bugs in the test suite"},
            {"content": "Fixed import error and broken assertion"},
            {"content": "Fixed the validation bug"},
            {"content": "Fixed timeout in CI"},
        ]
        patterns = detect_recurring_patterns(history)
        assert len(patterns) >= 1
        assert patterns[0]["activity"] == "fix"
        assert patterns[0]["frequency"] >= 3

    def test_no_patterns_with_few_sessions(self):
        history = [{"content": "Did some work"}, {"content": "More work"}]
        patterns = detect_recurring_patterns(history)
        assert len(patterns) == 0

    def test_empty_history(self):
        patterns = detect_recurring_patterns([])
        assert len(patterns) == 0

    def test_mixed_activities(self):
        history = [
            {"content": "Built new feature and ran tests"},
            {"content": "Created module and added tests"},
            {"content": "Implemented handler with test coverage"},
            {"content": "Explored the API documentation"},
        ]
        patterns = detect_recurring_patterns(history)
        # build and test should both appear frequently
        activities = [p["activity"] for p in patterns]
        assert "build" in activities or "test" in activities


class TestPredictions:
    """Full prediction pipeline."""

    def test_predicts_with_events(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = predict_session_needs(current_events=["Create new module", "Add handler function"])
        assert result["current_profile"]["profile"] == "build"
        assert isinstance(result["predictions"], list)

    def test_predicts_empty_events(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = predict_session_needs(current_events=[])
        assert result["current_profile"]["profile"] == "unknown"

    def test_predictions_sorted_by_confidence(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = predict_session_needs(current_events=["Fix import error", "Bug in test"])
        preds = result["predictions"]
        if len(preds) >= 2:
            assert preds[0]["confidence"] >= preds[1]["confidence"]

    def test_max_five_predictions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = predict_session_needs(
            current_events=["fix bug", "test assert", "build create", "review audit"]
        )
        assert len(result["predictions"]) <= 5


class TestFormatPredictions:
    """Display formatting."""

    def test_format_with_predictions(self):
        result = {
            "current_profile": {
                "profile": "build",
                "confidence": 0.8,
                "description": "Building new features",
            },
            "recurring_patterns": [],
            "predictions": [
                {
                    "prediction": "After building, you typically test",
                    "confidence": 0.56,
                    "source": "session_profile",
                    "action": "test",
                }
            ],
            "session_count": 5,
        }
        output = format_predictions(result)
        assert "Building new features" in output
        assert "Predictions:" in output

    def test_format_with_recurring(self):
        result = {
            "current_profile": {"profile": "unknown", "confidence": 0.0, "description": ""},
            "recurring_patterns": [
                {
                    "activity": "fix",
                    "frequency": 4,
                    "out_of": 5,
                    "description": "Fixing bugs",
                    "typical_next": ["test"],
                }
            ],
            "predictions": [],
            "session_count": 5,
        }
        output = format_predictions(result)
        assert "Recurring patterns:" in output
        assert "4/5" in output

    def test_format_empty(self):
        result = {
            "current_profile": {"profile": "unknown", "confidence": 0.0, "description": ""},
            "recurring_patterns": [],
            "predictions": [],
            "session_count": 0,
        }
        output = format_predictions(result)
        assert "Not enough" in output
