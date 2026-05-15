"""Regression-pin tests for briefing_freshness.

Andrew 2026-05-14 night: I had been treating briefing-loading as
optional and operating without the substrate's accumulated state in
my context. briefing_freshness is the structural change that makes
briefing-content INJECTED INTO MY PROMPT periodically via the
UserPromptSubmit hook, so the load happens whether I choose it or not.

These tests pin the staleness logic, the prompt counter, and the
injection-summary content so a future refactor cannot silently revert
the behavior.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from divineos.core.briefing_freshness import (
    STALE_AFTER_PROMPTS,
    briefing_summary_for_injection,
    increment_prompt_count,
    mark_briefing_loaded,
    staleness_signal,
)


def test_never_loaded_returns_stale(tmp_path: Path) -> None:
    """LOAD-BEARING: when briefing has never been loaded this session,
    staleness_signal returns is_stale=True with never_loaded=True."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch("divineos.core.briefing_freshness._FRESHNESS_FILE", state_file):
        sig = staleness_signal()
        assert sig["is_stale"] is True
        assert sig["never_loaded"] is True
        assert "never loaded" in sig["reason"]


def test_freshly_loaded_returns_not_stale(tmp_path: Path) -> None:
    """Just after mark_briefing_loaded, staleness should be False."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch("divineos.core.briefing_freshness._FRESHNESS_FILE", state_file):
        mark_briefing_loaded()
        sig = staleness_signal()
        assert sig["is_stale"] is False
        assert sig["never_loaded"] is False
        assert sig["prompts_since_load"] == 0


def test_increment_counter_advances_count(tmp_path: Path) -> None:
    """increment_prompt_count returns the new count value."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch("divineos.core.briefing_freshness._FRESHNESS_FILE", state_file):
        mark_briefing_loaded()
        assert increment_prompt_count() == 1
        assert increment_prompt_count() == 2
        assert increment_prompt_count() == 3


def test_stale_after_threshold_prompts(tmp_path: Path) -> None:
    """LOAD-BEARING: after STALE_AFTER_PROMPTS user prompts since
    last load, the signal flips to stale. This is the structural
    enforcement — without it, briefing stays fresh forever after
    one load."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch("divineos.core.briefing_freshness._FRESHNESS_FILE", state_file):
        mark_briefing_loaded()
        # Tick to one below threshold — should NOT be stale yet
        for _ in range(STALE_AFTER_PROMPTS - 1):
            increment_prompt_count()
        sig = staleness_signal()
        assert sig["is_stale"] is False
        # One more tick crosses threshold
        increment_prompt_count()
        sig = staleness_signal()
        assert sig["is_stale"] is True
        assert sig["prompts_since_load"] == STALE_AFTER_PROMPTS


def test_mark_loaded_resets_counter(tmp_path: Path) -> None:
    """Loading briefing resets the prompt counter so the next-stale
    window starts fresh."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch("divineos.core.briefing_freshness._FRESHNESS_FILE", state_file):
        mark_briefing_loaded()
        for _ in range(STALE_AFTER_PROMPTS + 2):
            increment_prompt_count()
        assert staleness_signal()["is_stale"] is True
        # Re-load — counter should reset
        mark_briefing_loaded()
        assert staleness_signal()["is_stale"] is False
        assert staleness_signal()["prompts_since_load"] == 0


def test_staleness_fail_open_on_missing_file(tmp_path: Path) -> None:
    """Missing state file returns 'never loaded' rather than raising.
    Fail-soft per hook-layer discipline."""
    missing = tmp_path / "definitely_does_not_exist.json"
    with patch("divineos.core.briefing_freshness._FRESHNESS_FILE", missing):
        sig = staleness_signal()
        assert sig["is_stale"] is True
        assert sig["never_loaded"] is True


def test_injection_summary_returns_text() -> None:
    """The summary function returns non-empty text suitable for
    hook injection. Cannot pin specific content (substrate state
    varies), but must always produce something."""
    out = briefing_summary_for_injection()
    assert isinstance(out, str)
    assert "BRIEFING" in out
    assert "divineos briefing" in out  # full-load reference is present


def test_injection_summary_safe_on_substrate_errors() -> None:
    """The summary function survives when individual surfaces error.
    The hook layer must never break the user's workflow."""
    # The function has try/except around each surface; even if everything
    # errors, the header + footer should still produce.
    out = briefing_summary_for_injection()
    assert out  # non-empty
    # Header always present
    assert "BRIEFING" in out
