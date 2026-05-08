"""Tests for moral_compass.py silent-pass → logger.warning conversion.

Round-2 audit (2026-05-07) called out three silent-pass sites in
moral_compass.py: CONTRACT_DUAL_RUN_DISCREPANCY emit, RUDDER_ACK_RETRACTED
emit, and fire-id rejection record_failure. When these failed, the
audit-trail entry just disappeared with no log line — exactly the
silent-degradation failure-mode the architecture claims it doesn't
have.

The fix: ``except Exception as e: logger.warning(...)`` instead of
``except Exception: pass``. Fail-soft semantics preserved (function
still returns normally); audit trail of the failure preserved (the
warning lands in loguru's stream).

These tests pin both halves: (a) failure no longer crashes the caller,
(b) failure no longer is silent.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import moral_compass


class TestEmitFailuresAreLoggedNotSilent:
    """When an audit-trail emit raises, the function still returns
    cleanly AND a warning is logged. Both halves matter."""

    def test_dual_run_discrepancy_fail_soft_and_logs(self, caplog):
        """_emit_dual_run_discrepancy: emit raises → warning logged, no exception."""
        with patch.object(moral_compass, "logger") as mock_logger:
            with patch(
                "divineos.core.ledger.log_event",
                side_effect=RuntimeError("simulated emit failure"),
            ):
                # Should not raise
                moral_compass._emit_dual_run_discrepancy(
                    spectrum="precision",
                    legacy_ok=True,
                    legacy_stage="virtue",
                    contract_ok=False,
                    contract_stage="excess",
                    contract_reason="test",
                    fire_id="abc123",
                    parsed_wired="yes",
                )
            # Warning was emitted
            assert mock_logger.warning.called, (
                "Expected logger.warning when emit fails — silent pass is the regression"
            )

    def test_rudder_ack_retracted_fail_soft_and_logs(self, caplog):
        with patch.object(moral_compass, "logger") as mock_logger:
            with patch(
                "divineos.core.ledger.log_event",
                side_effect=RuntimeError("simulated emit failure"),
            ):
                moral_compass._emit_rudder_ack_retracted(
                    spectrum="precision",
                    fire_id="abc123",
                    observation_id="obs-456",
                    artifact_reference=None,
                    next_plan=None,
                    depends_on=None,
                )
            assert mock_logger.warning.called

    def test_fire_id_rejection_fail_soft_and_logs(self, caplog):
        with patch.object(moral_compass, "logger") as mock_logger:
            with patch(
                "divineos.core.failure_diagnostics.record_failure",
                side_effect=RuntimeError("simulated record failure"),
            ):
                moral_compass._record_fire_id_rejection(
                    fire_id="abc123",
                    spectrum="precision",
                    reason="test reason",
                )
            assert mock_logger.warning.called


class TestNoSilentPassRegression:
    """Source-level regression test: confirm the three sites that round-2
    audit flagged are no longer silent. Catches accidental revert."""

    def test_three_warning_calls_in_emit_functions(self):
        """moral_compass.py should have at least 3 logger.warning calls
        (one per audit-trail emit function: _emit_dual_run_discrepancy,
        _emit_rudder_ack_retracted, _record_fire_id_rejection).

        Round-2 audit had 3 silent-pass sites. The patch replaced all
        3 with logger.warning calls. This pins the count.
        """
        from pathlib import Path

        src = Path(moral_compass.__file__).read_text(encoding="utf-8")
        warning_count = src.count("logger.warning")
        assert warning_count >= 3, (
            f"Expected at least 3 logger.warning calls in moral_compass.py "
            f"(one per audit-trail emit function); found {warning_count}. "
            f"Silent-pass regression?"
        )

    def test_no_bare_pass_after_emit_exception(self):
        """No ``except Exception: pass`` immediately after a log_event/
        record_failure call. Catches the silent-degradation shape directly.
        """
        from pathlib import Path

        src = Path(moral_compass.__file__).read_text(encoding="utf-8")
        # The exact silent shape: except Exception (with or without "as e"):
        # followed by a noqa comment line, followed by pass.
        # We allow "as e:" because the patch uses "as e" to capture the
        # exception for the warning message — the "pass" line is what
        # was removed.
        problematic = []
        lines = src.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "pass" and i > 0:
                # Check the preceding line(s) for the except pattern
                # within 3 lines back (covering noqa-comment line)
                for back in range(1, 4):
                    if i - back < 0:
                        break
                    prev = lines[i - back].strip()
                    if prev.startswith("except Exception"):
                        problematic.append(i + 1)
                        break

        # The remaining bare passes in moral_compass.py should be ZERO
        # for the three patched sites. (Other modules may still have
        # them; this test only guards moral_compass.)
        assert problematic == [], (
            f"Found bare 'pass' after 'except Exception' at lines: {problematic}. "
            f"These are silent-degradation shapes that round-2 audit flagged. "
            f"Replace with logger.warning(...) before the pass."
        )
