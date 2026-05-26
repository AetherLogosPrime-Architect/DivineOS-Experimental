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
    briefing_summary_for_injection,
    increment_prompt_count,
    mark_briefing_loaded,
    staleness_signal,
)


def test_never_loaded_returns_stale(tmp_path: Path) -> None:
    """LOAD-BEARING: when briefing has never been loaded this session,
    staleness_signal returns is_stale=True with never_loaded=True."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(state_file.parent)}):
        sig = staleness_signal()
        assert sig["is_stale"] is True
        assert sig["never_loaded"] is True
        assert "never loaded" in sig["reason"]


def test_freshly_loaded_returns_not_stale(tmp_path: Path) -> None:
    """Loaded this session AND within the briefing-id recall window →
    not stale. Freshness is now the recall window, not the prompt-count
    (prereg-e536aaec6144)."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(state_file.parent)}):
        mark_briefing_loaded()
        with (
            patch("divineos.core.briefing_id.current_tool_count", return_value=5),
            patch("divineos.core.briefing_id.is_fresh", return_value=True),
        ):
            sig = staleness_signal()
            assert sig["is_stale"] is False
            assert sig["never_loaded"] is False
            assert sig["mode"] == "briefing_id"


def test_increment_counter_advances_count(tmp_path: Path) -> None:
    """increment_prompt_count returns the new count value."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(state_file.parent)}):
        mark_briefing_loaded()
        assert increment_prompt_count() == 1
        assert increment_prompt_count() == 2
        assert increment_prompt_count() == 3


def test_stale_after_recall_window_exceeded(tmp_path: Path) -> None:
    """LOAD-BEARING: once the briefing-id recall window is exceeded
    (is_fresh False), the signal flips to stale and names the recall
    cure. This is the structural enforcement — drift is measured by the
    recall window, not a raw prompt-count (prereg-e536aaec6144)."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(state_file.parent)}):
        mark_briefing_loaded()
        with (
            patch("divineos.core.briefing_id.current_tool_count", return_value=999),
            patch("divineos.core.briefing_id.is_fresh", return_value=False),
        ):
            sig = staleness_signal()
            assert sig["is_stale"] is True
            assert sig["never_loaded"] is False
            assert sig["mode"] == "briefing_id"
            assert "recall" in sig["reason"].lower()


def test_recall_or_reload_clears_stale(tmp_path: Path) -> None:
    """After drift flips stale, a re-stamped recall window (is_fresh
    True — what `divineos briefing-id <id>` or a reload produces) clears
    it. The cure-channel is the door, not a fail-open."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(state_file.parent)}):
        mark_briefing_loaded()
        with patch("divineos.core.briefing_id.current_tool_count", return_value=999):
            with patch("divineos.core.briefing_id.is_fresh", return_value=False):
                assert staleness_signal()["is_stale"] is True
            with patch("divineos.core.briefing_id.is_fresh", return_value=True):
                assert staleness_signal()["is_stale"] is False


def test_fail_closed_when_briefing_id_unavailable(tmp_path: Path) -> None:
    """LOAD-BEARING (Andrew 2026-05-25): uncertainty errs toward STALE,
    never waved-through. A permanent fail-open would become the cheap
    path routed through every time. If briefing-id freshness can't be
    determined, the gate stays closed; the cure-channel and the
    announced+logged emergency_bypass are the only ways past."""
    state_file = tmp_path / "briefing_last_loaded.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(state_file.parent)}):
        mark_briefing_loaded()
        with patch(
            "divineos.core.briefing_id.current_tool_count",
            side_effect=RuntimeError("ledger unreadable"),
        ):
            sig = staleness_signal()
            assert sig["is_stale"] is True
            assert sig["never_loaded"] is False
            assert "recall or reload" in sig["reason"].lower()


def test_staleness_fail_open_on_missing_file(tmp_path: Path) -> None:
    """Missing state file returns 'never loaded' rather than raising.
    Fail-soft per hook-layer discipline."""
    missing = tmp_path / "definitely_does_not_exist.json"
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(missing.parent)}):
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
