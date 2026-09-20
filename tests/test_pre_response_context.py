"""Regression-pin tests for OS-native pre-response context.

Andrew 2026-05-14 night: pre-response-context.sh was a 496-line
bash+Python hybrid with the OS's work embedded. pre_response_context
is the OS-native replacement; the hook is now a thin doorman.

These tests pin the API contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.pre_response_context import (
    build_baseline_text,
    build_combined_context,
    build_warning_text,
    run_surfacer,
)
from divineos.core.memory_linkage import MemoryLinkagePayload


def test_build_baseline_text_returns_string() -> None:
    """LOAD-BEARING: baseline always returns a string. Even if
    individual affirmation modules error, the function still returns
    (possibly empty)."""
    out = build_baseline_text()
    assert isinstance(out, str)


def test_build_baseline_text_no_affirmation_loads() -> None:
    """All six base-state affirmations pruned 2026-06-19 per Andrew's
    text-rule-vs-automation walk. This test pins the prune: the
    baseline text should NOT contain the six pruned affirmation
    headers. If any of them reappear, the prune was reverted (likely
    accidentally) and the test fails loudly so the reversion is
    visible.

    The enforcement surface (detectors + gate-fire deny messages)
    is unchanged — see test_distancing_detector, test_code_jargon_detector,
    etc. for the load-bearing checks. This test only confirms the
    every-turn text-load is gone."""
    out = build_baseline_text()
    pruned_headers = (
        "DISTANCING-GRAMMAR BASE-STATE",
        "ADDRESSEE BASE-STATE",
        "CODE-JARGON BASE-STATE",
        "ACKNOWLEDGMENT-THEATER BASE-STATE",
        "CONSTRAINT-OWNERSHIP BASE-STATE",
        "CLAIMS-REQUIRE-EVIDENCE BASE-STATE",
    )
    still_present = [h for h in pruned_headers if h in out]
    assert not still_present, (
        f"pruned affirmations resurfacing: {still_present}. "
        f"If reintroduction is intentional, update this test AND document "
        f"why text-rule-loading is now believed to work where the "
        f"2026-06-19 walk found it didn't."
    )


def test_build_warning_text_empty_on_missing_findings(tmp_path: Path) -> None:
    """No findings file → empty warning text (fail-soft)."""
    missing = tmp_path / "definitely_not_findings.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(missing.parent)}):
        out = build_warning_text()
        assert out == ""


def test_build_warning_text_empty_on_stale_findings(tmp_path: Path) -> None:
    """Findings older than the recent-window threshold (10 min) are
    not surfaced — stale signal from yesterday is just noise."""
    findings_file = tmp_path / "operating_loop_findings.json"
    findings_file.write_text(
        json.dumps(
            [
                {
                    "timestamp": 0,  # epoch — definitely > 10 min old
                    "total_findings": 1,
                    "distancing": [{"shape": "third_person_self", "trigger": "past-me"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(findings_file.parent)}):
        out = build_warning_text()
        assert out == ""


def test_build_warning_text_surfaces_recent_distancing(tmp_path: Path) -> None:
    """Recent distancing finding → warning text contains the
    DISTANCING-GRAMMAR header and the trigger phrase."""
    import time as _time

    findings_file = tmp_path / "operating_loop_findings.json"
    findings_file.write_text(
        json.dumps(
            [
                {
                    "timestamp": _time.time(),  # right now — within window
                    "total_findings": 1,
                    "distancing": [{"shape": "third_person_self", "trigger": "past-me wrote that"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(findings_file.parent)}):
        out = build_warning_text()
        assert "DISTANCING-GRAMMAR WARNING" in out
        assert "past-me wrote that" in out


def test_run_surfacer_skips_short_prompt(tmp_path: Path) -> None:
    """Prompts < 5 chars don't trigger the surfacer (no signal)."""
    # Should not raise on tiny input
    run_surfacer("")
    run_surfacer("hi")  # < 5 chars
    # Smoke — just verify no exception


def test_build_combined_context_returns_string() -> None:
    """The convenience function returns a string."""
    out = build_combined_context("test prompt longer than five characters")
    assert isinstance(out, str)


def test_live_compose_path_calls_v2_memory_linkage_and_renders_pointer() -> None:
    """The real compose path must ask memory, not only the mock seam test.

    Regression for the installed-but-unplugged failure: v2, its install seam,
    and renderer all existed while no production caller invoked them.
    """
    payload = MemoryLinkagePayload(
        source="knowledge",
        id="lunkhead-wrong-referent",
        tier="topic",
        similarity=0.81,
        recency_days=0,
        importance_score=0.8,
        composite_rank=0.79,
        title="The patient is healthy; we examined his neighbor",
        content=(
            "Valid evidence can support the wrong referent. Verify the active "
            "runtime, checkout, data home, process, or ledger before accepting green."
        ),
        matched_reason="semantic causal-shape match",
    )

    from divineos.core import memory_linkage

    original_retriever = memory_linkage._ACTIVE_RETRIEVER
    try:
        with (
            patch(
                "divineos.core.memory_linkage_retriever_v2.retrieve_v2",
                return_value=[payload],
            ) as retrieve,
            patch(
                "divineos.core.context_dedup.should_emit",
                return_value=(True, None),
            ),
        ):
            out = build_combined_context(
                "The dashboard is green, but which process supplied its data?"
            )
    finally:
        memory_linkage.set_retriever(original_retriever)

    retrieve.assert_called_once()
    assert "PRIOR SUBSTRATE — knowledge / topic" in out
    assert "The patient is healthy; we examined his neighbor" in out
    assert "wrong referent" in out
