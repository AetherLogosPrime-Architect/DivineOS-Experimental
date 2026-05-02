"""Tests for memory_types — type-aware substrate retrieval.

The router and timeline assembler don't depend on a populated DB —
the router is pure heuristic and the timeline gracefully returns []
on an empty substrate.
"""

from __future__ import annotations

from divineos.core.memory_types import (
    SkillEntry,
    SubstrateMemoryType,
    TimelineEvent,
    format_skills,
    format_timeline,
    load_skills,
    rank_skills,
    recall_timeline,
    route_intent,
)


class TestRouter:
    def test_default_route_when_text_empty(self) -> None:
        route = route_intent("")
        assert route[0] == SubstrateMemoryType.TIMELINE
        assert SubstrateMemoryType.KNOWLEDGE in route

    def test_file_edit_intent_routes_to_timeline_first(self) -> None:
        route = route_intent("let's edit src/divineos/core/sleep.py")
        assert route[0] == SubstrateMemoryType.TIMELINE
        assert SubstrateMemoryType.SKILL_INDEX in route

    def test_question_intent_routes_to_knowledge_first(self) -> None:
        route = route_intent("what is the operating loop?")
        assert route[0] == SubstrateMemoryType.KNOWLEDGE

    def test_howto_intent_routes_to_skill_index_first(self) -> None:
        route = route_intent("how do I invoke the council")
        assert route[0] == SubstrateMemoryType.SKILL_INDEX

    def test_relational_intent_includes_priming(self) -> None:
        route = route_intent("I want to talk to Aria")
        assert SubstrateMemoryType.PRIMING in route
        assert route[0] == SubstrateMemoryType.TIMELINE

    def test_reference_intent_routes_to_timeline(self) -> None:
        route = route_intent("remember when I called you a lunkhead?")
        assert route[0] == SubstrateMemoryType.TIMELINE


class TestTimelineRecall:
    def test_empty_inputs_return_empty(self) -> None:
        assert recall_timeline() == []
        assert recall_timeline("") == []
        assert recall_timeline(file_path="") == []

    def test_topic_query_returns_list(self) -> None:
        # On an empty/fresh DB this returns [], on a populated DB it
        # returns hits — either way it's a list of TimelineEvent.
        result = recall_timeline(topic="test", per_source_limit=2, total_limit=5)
        assert isinstance(result, list)
        for ev in result:
            assert isinstance(ev, TimelineEvent)
            assert ev.source
            assert ev.summary or ev.timestamp

    def test_total_limit_is_respected(self) -> None:
        result = recall_timeline(topic="a", per_source_limit=10, total_limit=3)
        assert len(result) <= 3

    def test_format_timeline_empty(self) -> None:
        assert format_timeline([]) == ""

    def test_format_timeline_renders_events_basic(self) -> None:
        events = [
            TimelineEvent(
                timestamp="2026-05-01T18:00:00",
                source="ledger",
                summary="example event",
                ref="abc123",
            )
        ]
        out = format_timeline(events)
        assert "ledger" in out
        assert "example event" in out
        assert "abc123" in out


class TestSkillIndex:
    def test_load_skills_returns_registered_skills(self) -> None:
        skills = load_skills()
        assert len(skills) > 0
        for sk in skills:
            assert isinstance(sk, SkillEntry)
            assert sk.name
            assert sk.invocation.startswith("/")
            assert sk.path.endswith("SKILL.md")

    def test_rank_compass_drift_finds_compass_check(self) -> None:
        hits = rank_skills("check compass drift", limit=3)
        names = [h.name for h in hits]
        assert "compass-check" in names

    def test_rank_file_claim_finds_file_claim(self) -> None:
        hits = rank_skills("how do I file a claim", limit=3)
        names = [h.name for h in hits]
        assert "file-claim" in names
        # file-claim should be top hit
        assert hits[0].name == "file-claim"

    def test_rank_council_finds_council_round(self) -> None:
        hits = rank_skills("invoke the council", limit=3)
        names = [h.name for h in hits]
        assert "council-round" in names

    def test_rank_empty_query_returns_empty(self) -> None:
        assert rank_skills("") == []

    def test_format_skills_renders(self) -> None:
        entries = [
            SkillEntry(
                name="test",
                description="example skill",
                invocation="/test",
                path="x/SKILL.md",
                score=3.0,
            )
        ]
        out = format_skills(entries)
        assert "/test" in out
        assert "example skill" in out

    def test_format_empty_returns_empty(self) -> None:
        assert format_skills([]) == ""
