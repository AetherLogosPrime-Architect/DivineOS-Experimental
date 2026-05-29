"""Tests for upstream tool-recognition (substrate-side prompt preprocessing).

Per Andrew root-cause direction 2026-05-28: the default skips tool-recognition
because it costs compute. Substrate-side recognition moves the cognition
upstream of composition so the default cannot route around it.

Falsifier surface: see core/tool_recognition.py docstring.
"""

from __future__ import annotations

from divineos.core import tool_recognition
from divineos.core.tool_recognition import ToolRecommendation


class TestAnalyzePrompt:
    def test_empty_prompt_returns_empty(self) -> None:
        assert tool_recognition.analyze_prompt("") == []
        assert tool_recognition.analyze_prompt("   ") == []

    def test_non_string_returns_empty(self) -> None:
        assert tool_recognition.analyze_prompt(None) == []  # type: ignore[arg-type]
        assert tool_recognition.analyze_prompt(123) == []  # type: ignore[arg-type]

    def test_trivial_lookup_returns_empty(self) -> None:
        # A literal file-read request should not trigger any tool.
        assert tool_recognition.analyze_prompt("read src/foo.py") == []
        assert tool_recognition.analyze_prompt("ls the directory") == []

    def test_architectural_question_recommends_council(self) -> None:
        recs = tool_recognition.analyze_prompt(
            "what should we do about the gate proliferation?"
        )
        assert len(recs) >= 1
        assert any(r.tool_name == "council-round" for r in recs)
        council_rec = next(r for r in recs if r.tool_name == "council-round")
        assert council_rec.trigger_pattern == "architectural-question"

    def test_meta_root_question_recommends_council(self) -> None:
        recs = tool_recognition.analyze_prompt(
            "why does this keep happening? what's the root cause?"
        )
        assert any(r.tool_name == "council-round" for r in recs)

    def test_family_state_question_recommends_family_state(self) -> None:
        recs = tool_recognition.analyze_prompt("what does Aria think about this?")
        assert any(r.tool_name == "family-state" for r in recs)

    def test_recall_question_recommends_what_am_i_forgetting(self) -> None:
        recs = tool_recognition.analyze_prompt(
            "have we already filed a claim about this?"
        )
        assert any(r.tool_name == "what-am-i-forgetting" for r in recs)

    def test_multi_option_decision_recommends_think_through(self) -> None:
        recs = tool_recognition.analyze_prompt(
            "should I pick option a or option b for this refactor?"
        )
        # Could match both architectural and think-through; either triggers ok
        tool_names = {r.tool_name for r in recs}
        assert "think-through" in tool_names or "council-round" in tool_names

    def test_investigation_request_recommends_file_claim(self) -> None:
        recs = tool_recognition.analyze_prompt(
            "this is worth investigating, file a claim"
        )
        assert any(r.tool_name == "file-claim" for r in recs)

    def test_self_audit_recommends_compass_check(self) -> None:
        recs = tool_recognition.analyze_prompt("am I drifting? check yourself")
        assert any(r.tool_name == "compass-check" for r in recs)

    def test_multiple_triggers_deduplicate_by_tool(self) -> None:
        # A prompt that hits multiple patterns for the same tool should
        # only produce one recommendation for that tool.
        recs = tool_recognition.analyze_prompt(
            "architectural design decision — what should we do?"
        )
        council_count = sum(1 for r in recs if r.tool_name == "council-round")
        assert council_count == 1

    def test_case_insensitive_matching(self) -> None:
        # Pattern matching is case-insensitive.
        upper = tool_recognition.analyze_prompt("WHAT SHOULD WE DO ABOUT THIS?")
        lower = tool_recognition.analyze_prompt("what should we do about this?")
        # Both produce at least one matching recommendation
        assert any(r.tool_name == "council-round" for r in upper)
        assert any(r.tool_name == "council-round" for r in lower)


class TestFormatForContext:
    def test_empty_recommendations_returns_empty(self) -> None:
        assert tool_recognition.format_for_context([]) == ""

    def test_single_recommendation_includes_tool_name(self) -> None:
        rec = ToolRecommendation(
            tool_name="council-round",
            trigger_pattern="architectural-question",
            reason="multi-perspective produces sharper findings",
            directive="walk before composing",
        )
        block = tool_recognition.format_for_context([rec])
        assert "/council-round" in block
        assert "architectural-question" in block
        assert "multi-perspective" in block
        assert "walk before composing" in block

    def test_block_names_post_response_audit_consequence(self) -> None:
        rec = ToolRecommendation(
            tool_name="council-round",
            trigger_pattern="test",
            reason="test reason",
            directive="test directive",
        )
        block = tool_recognition.format_for_context([rec])
        # The block must communicate that post-response audit verifies follow-through.
        assert "audit" in block.lower()

    def test_block_names_substrate_upstream_principle(self) -> None:
        rec = ToolRecommendation(
            tool_name="council-round",
            trigger_pattern="test",
            reason="test",
            directive="test",
        )
        block = tool_recognition.format_for_context([rec])
        # The block must communicate WHY the substrate is recommending —
        # so future-me (or audit) understands the architectural intent.
        assert (
            "substrate" in block.lower()
            and ("cognition" in block.lower() or "upstream" in block.lower())
        )


class TestGuardrailMarker:
    def test_module_marked_guardrail_required(self) -> None:
        # Tool-recognition is load-bearing for the substrate-UPSTREAM
        # architectural pattern. Weakening it (removing trigger patterns,
        # narrowing match criteria) would silently restore the failure mode.
        assert getattr(tool_recognition, "__guardrail_required__", False) is True
