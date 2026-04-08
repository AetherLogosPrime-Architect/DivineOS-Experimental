"""Tests for goal staleness detection and culling."""

import time

from divineos.core.goal_cull import (
    _extract_goal_keywords,
    _STALENESS_THRESHOLD_DAYS,
    assess_goal_staleness,
)


class TestExtractKeywords:
    def test_strips_filler(self):
        kws = _extract_goal_keywords("Update the imports for all old modules")
        assert "the" not in kws
        assert "for" not in kws
        assert "imports" in kws

    def test_caps_at_8(self):
        kws = _extract_goal_keywords(
            "one two three four five six seven eight nine ten eleven twelve"
        )
        assert len(kws) <= 8

    def test_handles_dots_and_commas(self):
        kws = _extract_goal_keywords("fix these issues.. also the big one")
        assert "fix" in kws
        assert "issues" in kws


class TestAssessStaleness:
    def test_fresh_goal_not_stale(self):
        now = time.time()
        goal = {"text": "Do something", "added_at": now - 3600}  # 1 hour ago
        result = assess_goal_staleness(goal, now)
        assert result["stale"] is False
        assert result["age_days"] == 0

    def test_old_goal_is_stale(self):
        now = time.time()
        goal = {
            "text": "Do something obscure and unique xyz123",
            "added_at": now - (_STALENESS_THRESHOLD_DAYS + 1) * 86400,
        }
        result = assess_goal_staleness(goal, now)
        assert result["stale"] is True
        assert result["age_days"] >= _STALENESS_THRESHOLD_DAYS

    def test_old_goal_with_evidence(self, tmp_path, monkeypatch):
        from divineos.core.decision_journal import record_decision

        record_decision(content="Fixed the widget system", reasoning="needed fixing")

        now = time.time()
        goal = {
            "text": "Fix the widget system",
            "added_at": now - (_STALENESS_THRESHOLD_DAYS + 1) * 86400,
        }
        result = assess_goal_staleness(goal, now)
        assert result["stale"] is True
        # Should find the decision as evidence
        has_decision_evidence = any("Decision:" in e for e in result["evidence"])
        assert has_decision_evidence

    def test_age_in_evidence(self):
        now = time.time()
        goal = {
            "text": "Something old xyz unique",
            "added_at": now - 10 * 86400,
        }
        result = assess_goal_staleness(goal, now)
        assert result["stale"] is True
        assert any("Age:" in e for e in result["evidence"])
