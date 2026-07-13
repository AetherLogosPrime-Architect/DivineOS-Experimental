"""Tests for substrate_monitor — detects filing-cabinet-only OS use."""

from __future__ import annotations

from divineos.core.self_monitor.substrate_monitor import (
    SubstrateKind,
    ToolInvocation,
    evaluate_substrate,
)


class TestSubstrateMonitor:
    def test_clean_use_with_edits_no_flags(self) -> None:
        invs = [
            ToolInvocation(tool="recall"),
            ToolInvocation(tool="ask", args="hedge monitor"),
        ]
        verdict = evaluate_substrate(invs, edits_in_window=4)
        kinds = {f.kind for f in verdict.flags}
        assert SubstrateKind.FILING_CABINET not in kinds

    def test_filing_cabinet_fires(self) -> None:
        invs = [
            ToolInvocation(tool="recall"),
            ToolInvocation(tool="ask", args="patterns"),
            ToolInvocation(tool="learn", args="something"),
            ToolInvocation(tool="feel", args="-v 0.5"),
        ]
        verdict = evaluate_substrate(invs, edits_in_window=0)
        kinds = {f.kind for f in verdict.flags}
        assert SubstrateKind.FILING_CABINET in kinds

    def test_recall_not_referenced_fires(self) -> None:
        invs = [
            ToolInvocation(tool="recall", output="Distinctive Theaterprone Substrate"),
            ToolInvocation(tool="learn", args="x"),
            ToolInvocation(tool="ask", args="y"),
        ]
        verdict = evaluate_substrate(
            invs,
            edits_in_window=0,
            subsequent_text="moving on to other things now",
        )
        kinds = {f.kind for f in verdict.flags}
        assert SubstrateKind.RECALL_NOT_REFERENCED in kinds

    def test_learn_as_last_action_exempt(self) -> None:
        invs = [
            ToolInvocation(tool="learn", args="final lesson"),
        ]
        verdict = evaluate_substrate(invs, edits_in_window=0)
        kinds = {f.kind for f in verdict.flags}
        assert SubstrateKind.LEARN_WITHOUT_BEHAVIOR_CHANGE not in kinds

    def test_falsifier_note_present(self) -> None:
        invs = [
            ToolInvocation(tool="recall"),
            ToolInvocation(tool="ask"),
            ToolInvocation(tool="learn"),
            ToolInvocation(tool="feel"),
        ]
        verdict = evaluate_substrate(invs, edits_in_window=0)
        assert len(verdict.flags) > 0
        for f in verdict.flags:
            assert len(f.falsifier_note) > 20
