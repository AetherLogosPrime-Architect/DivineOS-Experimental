"""Tests for counterfactual journaling — tension and almost fields."""


class TestCounterfactualFields:
    def test_record_with_tension_and_almost(self, tmp_path, monkeypatch):

        from divineos.core.decision_journal import get_decision, record_decision

        did = record_decision(
            content="chose approach A",
            reasoning="simpler",
            tension="simplicity vs completeness",
            almost="approach B — more thorough but too slow",
        )
        entry = get_decision(did)
        assert entry is not None
        assert entry["tension"] == "simplicity vs completeness"
        assert entry["almost"] == "approach B — more thorough but too slow"

    def test_fields_default_empty(self, tmp_path, monkeypatch):

        from divineos.core.decision_journal import get_decision, record_decision

        did = record_decision(content="basic decision")
        entry = get_decision(did)
        assert entry is not None
        assert entry["tension"] == ""
        assert entry["almost"] == ""

    def test_list_includes_new_fields(self, tmp_path, monkeypatch):

        from divineos.core.decision_journal import list_decisions, record_decision

        record_decision(
            content="listed decision",
            tension="a vs b",
            almost="nearly did c",
        )
        entries = list_decisions(limit=5)
        assert len(entries) == 1
        assert entries[0]["tension"] == "a vs b"
        assert entries[0]["almost"] == "nearly did c"

    def test_search_returns_new_fields(self, tmp_path, monkeypatch):

        from divineos.core.decision_journal import record_decision, search_decisions

        record_decision(
            content="searchable decision about widgets",
            tension="speed vs quality",
        )
        results = search_decisions("widgets")
        assert len(results) == 1
        assert results[0]["tension"] == "speed vs quality"
