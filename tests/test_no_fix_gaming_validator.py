"""Tests for src/divineos/core/no_fix_gaming_validator.py.

Aletheia F100 (2026-07-29): the load-bearing validator of the session-
07-29 batch shipped with zero tests. Her priority per the F100 report:
the internal-error fail direction — a validator gating a bypass that
fails open is a bypass with extra steps. Writing that first, plus the
three other cases she named:

  1. No-fix invocation with no exhaustion section → blocked (base case)
  2. No-fix invocation with empty exhaustion section → blocked (cheapest
     gaming route: heading with nothing under it)
  3. Valid exhaustion → passes AND writes the system-redesign obligation
     (if the escalation silently fails, the valid path becomes free —
     the whole cost model collapses)
  4. Validator errors internally → which way does it fail? (priority per
     F100 — the difference between a gate and a decoration)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from divineos.core.no_fix_gaming_validator import (
    NoFixDisciplineError,
    validate_correction_body,
)


# ---------- 1. base case: no exhaustion section → blocked ----------


def test_no_fix_invocation_without_exhaustion_blocks():
    """Bare no-fix invocation with no options and no evidence must raise."""
    with pytest.raises(NoFixDisciplineError) as exc_info:
        validate_correction_body("This is a habit-side issue with no structural fix possible.")
    msg = str(exc_info.value)
    assert "NO-FIX GAMING VALIDATOR" in msg
    assert "exhaustion discipline" in msg


def test_no_fix_invocation_with_only_one_option_blocks():
    """Below-threshold enumeration must raise (< MIN_OPTIONS)."""
    with pytest.raises(NoFixDisciplineError):
        validate_correction_body(
            "No structural fix possible for this instance.\n\n"
            "1. Only option: rewrite the whole thing — not viable, too big."
        )


# ---------- 2. empty exhaustion section → blocked ----------


def test_no_fix_with_option_headers_but_no_exhaustion_markers_blocks():
    """The cheapest gaming route: three numbered headers, no evidence
    text explaining why each option was rejected."""
    body = "No fix possible for this class.\n\n1. Option one.\n2. Option two.\n3. Option three."
    with pytest.raises(NoFixDisciplineError) as exc_info:
        validate_correction_body(body)
    msg = str(exc_info.value)
    # Should report both counts so the operator sees the specific gap
    assert "0 exhaustion-evidence" in msg or "exhaustion-evidence" in msg


# ---------- 3. valid exhaustion → passes AND escalates ----------


def test_valid_exhaustion_passes_and_writes_obligation():
    """Full 3+3 discipline passes, and the escalation subprocess is
    invoked to write the system-redesign obligation. If the escalation
    silently fails, the valid path becomes free — this test pins that
    the escalation call is actually made."""
    valid_body = (
        "Class of failure with no per-instance fix possible.\n\n"
        "1. Option A: raise threshold — not viable, would over-fire on legit cases.\n"
        "2. Option B: add regex — cannot be implemented without violating anti-pattern.\n"
        "3. Option C: manual review — tested and failed under time pressure.\n\n"
        "All solutions exhausted. No structural fix available."
    )
    # subprocess is imported inside _escalate_to_system_redesign, so
    # patch at the standard-library path where the call resolves
    with patch("subprocess.run") as mock_run:
        # Validate should not raise
        validate_correction_body(valid_body)
        # Escalation must have been called — otherwise the valid path
        # is a free pass and the cost-currency principle collapses
        assert mock_run.called, (
            "Valid no-fix invocation must trigger system-redesign "
            "obligation escalation; without it, the cost model is broken"
        )
        # Verify the escalation targets the backlog command
        call_args = mock_run.call_args
        cmd_list = call_args[0][0] if call_args and call_args[0] else []
        assert "divineos" in cmd_list
        assert "backlog" in cmd_list
        assert "add" in cmd_list


# ---------- 4. PRIORITY (Aletheia F100): internal-error fail direction ----------


def test_validator_fails_CLOSED_when_internal_error_raises():
    """PRIORITY per Aletheia F100 (2026-07-29): if the validator raises
    an internal exception (regex crash, unicode weirdness, etc.), which
    way does it fail?

    A validator gating a bypass that fails OPEN is a bypass with extra
    steps. This test pins the fail direction as CLOSED — when internal
    error occurs during validation, the correction filing must NOT
    proceed. The safe direction is to surface the error (or raise), NOT
    silently succeed.

    Currently no_fix_gaming_validator uses `_NO_FIX_RE.search(text)` and
    similar direct regex ops with no wrapping try/except in
    validate_correction_body. So an internal error propagates as an
    exception — which the CLI wrapper in cli/correction_commands.py
    catches (`except Exception as validator_error`) and translates to
    exit-2. That IS fail-closed at the CLI layer. This test pins that
    the module-level function does NOT swallow errors silently.
    """
    # Replace _NO_FIX_RE with a mock whose .search raises. Can't patch
    # the read-only .search attribute of a compiled re.Pattern directly,
    # so patch the whole _NO_FIX_RE name in the module namespace.
    from unittest.mock import MagicMock

    fake_pattern = MagicMock()
    fake_pattern.search.side_effect = RuntimeError("simulated crash")
    with patch(
        "divineos.core.no_fix_gaming_validator._NO_FIX_RE",
        fake_pattern,
    ):
        # The validator must NOT return silently — it must raise
        with pytest.raises((RuntimeError, NoFixDisciplineError)):
            validate_correction_body("any text with no fix language")


# ---------- silent-pass cases (validator inactive) ----------


def test_no_invocation_at_all_passes_silently():
    """Correction body with no no-fix invocation phrases must not raise."""
    validate_correction_body(
        "Fixed the wallclock prime broadening. Root cause: prime trigger too narrow."
    )


def test_empty_text_passes_silently():
    """Empty or whitespace-only text passes without raising."""
    validate_correction_body("")
    validate_correction_body("   \n\n  ")


def test_none_or_empty_returns_early():
    """None-input handling (module accepts falsy text)."""
    # Should not crash on empty string
    validate_correction_body("")
    # None is not a documented input; skip that case
