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


def test_live_compose_path_does_not_invoke_the_memory_linkage_retriever() -> None:
    """Compose must NOT ask the linkage retriever, and this used to assert the
    exact opposite. Both intents are kept here on purpose.

    THE ORIGINAL, written 2026-09-20 and right about its own problem: v2, its
    install seam and its renderer all existed while no production caller
    invoked them, so a passing suite proved only that a handset could reach a
    mock exchange. That test asserted the live path called retrieve_v2 and
    rendered its pointer, and it passed.

    WHY IT IS REVERSED, the same day, by measurement rather than by taste. The
    retriever fills a module-level embedding cache that dies with its process
    and embeds every substrate item one at a time through a freshly loaded
    transformer. Compose runs in a new process per prompt, so wiring it here
    re-embedded the whole substrate every turn: the UserPromptSubmit hook
    emitted zero bytes and had not returned at 110 seconds, and being fail-open
    it reported that outage as silence. Unwired, the same hook emits in about a
    second. Nine tests in this suite were dying as worker crashes because they
    crossed the per-test time limit, which is what surfaced it.

    So this now guards the opposite property, and the ORIGINAL concern is not
    retired by that — it is deferred, with its condition written at the call
    site in pre_response_context: embeddings must survive the process (the
    sqlite-vec store in core/semantic_store.py already exists for this) and the
    hook must be timed end to end in the suite. When both hold, this test
    should flip back rather than be deleted, and the paragraph above is why.
    """
    from divineos.core import memory_linkage

    original_retriever = memory_linkage._ACTIVE_RETRIEVER
    try:
        with patch(
            "divineos.core.memory_linkage_retriever_v2.retrieve_v2",
            return_value=[],
        ) as retrieve:
            out = build_combined_context(
                "The dashboard is green, but which process supplied its data?"
            )
    finally:
        memory_linkage.set_retriever(original_retriever)

    retrieve.assert_not_called()
    assert isinstance(out, str)
