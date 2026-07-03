"""Fable audit Round 8 (2026-07-03) — briefing freshness fail-soft-to-0 inversion.

Fable's exact finding: ``current_tool_count()`` fails soft to 0 on
internal error. ``is_fresh(n)`` computes ``(n - last_verified) < expiry``.
When the count is 0 and the briefing was verified at a nonzero count,
the delta goes negative, ``negative < expiry`` is True, and the briefing
reports FRESH despite being arbitrarily stale. The outer fail-closed
guard in ``staleness_signal`` never sees the exception because the
inner helper swallows it before it propagates.

Fable's exact reproduction (executed by the auditor):
    healthy, count=45:      is_fresh = True   (correct — 5 tools since stamp)
    healthy, count=60:      is_fresh = False  (correct — 20 tools since stamp)
    LEDGER→0, count=0:      is_fresh = True   (WRONG — reports fresh; 0-40=-40 < 10)

Fix (both applied per Fable's preferred + minimum):
- ``current_tool_count`` propagates exceptions instead of returning 0 →
  outer ``staleness_signal`` try/except catches it and reports stale.
- ``is_fresh`` clamps negative deltas (current < last → False) as
  defense-in-depth against any future path where current reads below last.

Two independent barriers to the same spurious-fresh-pass class.
"""

from __future__ import annotations


from divineos.core import briefing_id, briefing_freshness


def test_is_fresh_returns_false_on_negative_delta_fable_reproduction(tmp_path, monkeypatch):
    """Fable's exact reproduction: current=0, last_verified=40, expiry=10.

    OLD behavior: (0 - 40) < 10 = -40 < 10 = True → FRESH (WRONG).
    FIXED behavior: current (0) < last (40) → clamp returns False → STALE.
    """
    # Isolate the truth file to this test.
    truth_file = tmp_path / "briefing_id_truth.json"
    monkeypatch.setattr(briefing_id, "_truth_path", lambda: truth_file)

    # Seed a valid briefing-id stamp at tool_count=40.
    briefing_id.issue_briefing_id(tool_count=40, session_id="test-session")

    # Simulate the ledger→0 condition: current_tool_count returns 0.
    assert briefing_id.is_fresh(current_tool_count=0, expiry=10) is False, (
        "Fable Round 8 regression: is_fresh with current=0 and last=40 "
        "must return False (clamp on negative delta). Old logic reported "
        "TRUE because (0-40) < 10 is True."
    )


def test_is_fresh_healthy_fresh_case_still_works(tmp_path, monkeypatch):
    """Regression: within-window still returns True."""
    truth_file = tmp_path / "briefing_id_truth.json"
    monkeypatch.setattr(briefing_id, "_truth_path", lambda: truth_file)
    briefing_id.issue_briefing_id(tool_count=40, session_id="test-session")

    # 5 tools since stamp, expiry 10 → fresh
    assert briefing_id.is_fresh(current_tool_count=45, expiry=10) is True


def test_is_fresh_healthy_stale_case_still_works(tmp_path, monkeypatch):
    """Regression: past-expiry (positive delta ≥ expiry) still returns False."""
    truth_file = tmp_path / "briefing_id_truth.json"
    monkeypatch.setattr(briefing_id, "_truth_path", lambda: truth_file)
    briefing_id.issue_briefing_id(tool_count=40, session_id="test-session")

    # 20 tools since stamp, expiry 10 → stale
    assert briefing_id.is_fresh(current_tool_count=60, expiry=10) is False


def test_is_fresh_at_exact_expiry_boundary(tmp_path, monkeypatch):
    """Boundary: delta == expiry is STALE (strict less-than semantics)."""
    truth_file = tmp_path / "briefing_id_truth.json"
    monkeypatch.setattr(briefing_id, "_truth_path", lambda: truth_file)
    briefing_id.issue_briefing_id(tool_count=40, session_id="test-session")

    # Exactly at expiry: (50 - 40) < 10 = 10 < 10 = False
    assert briefing_id.is_fresh(current_tool_count=50, expiry=10) is False


def test_current_tool_count_propagates_ledger_exception(monkeypatch):
    """Fable Round 8 primary fix: ledger read failure raises, not returns 0.

    Under OLD behavior the exception was swallowed and 0 returned. That
    hid the failure from staleness_signal's outer try/except and produced
    the spurious-fresh-pass. Under FIXED behavior the exception propagates
    upward where the outer guard can catch it and report stale.
    """

    def broken_count_events():
        raise RuntimeError("simulated ledger read failure")

    monkeypatch.setattr("divineos.core.ledger.count_events", broken_count_events)

    # Must raise, not return 0.
    try:
        result = briefing_id.current_tool_count()
    except RuntimeError:
        return  # correct behavior
    raise AssertionError(
        "Fable Round 8 regression: current_tool_count silently returned "
        f"{result} instead of propagating the ledger error. The fail-soft-"
        "to-0 was the exact silent-strand that produced the spurious-fresh-"
        "pass."
    )


def test_staleness_signal_reports_stale_on_current_tool_count_failure(tmp_path, monkeypatch):
    """Integration: outer fail-closed guard catches propagated exception.

    Confirms the two fixes compose. current_tool_count raises (primary
    fix). The outer try/except in staleness_signal (already existed) now
    catches it and correctly reports is_stale: True.
    """
    # Point state file at tmp so we can seed a "loaded this session" state.
    state_file = tmp_path / "briefing_freshness_state.json"
    monkeypatch.setattr(briefing_freshness, "_state_path", lambda: state_file)

    # Seed state as if briefing was loaded this session.
    briefing_freshness._write_state({"last_loaded_ts": 1234567890.0, "prompts_since_load": 0})

    # Break the ledger read.
    def broken_count_events():
        raise RuntimeError("simulated ledger read failure")

    monkeypatch.setattr("divineos.core.ledger.count_events", broken_count_events)

    result = briefing_freshness.staleness_signal()

    # The outer guard catches the propagated exception; result is stale
    # with the "briefing-id freshness unavailable" reason.
    assert result["is_stale"] is True, (
        f"staleness_signal must report is_stale=True when current_tool_count raises. Got {result}"
    )
    assert "unavailable" in result["reason"], (
        f"reason should name the freshness-unavailable failure, got: {result['reason']}"
    )
