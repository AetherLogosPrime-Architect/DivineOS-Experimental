"""The emergency-completion lane must be reachable from the command line.

WHY THESE TESTS EXIST. ``core/emergency_completion.py`` shipped complete and
command-less. Its own docstring prescribed
``divineos emergency-completion resolve --diagnosis "..."``, which did not
exist. That mattered because ``arm()`` refuses while a debt is outstanding
and ``resolve_debt()`` is the only thing that clears one — so the first use
of the lane would have left a permanent debt and closed the lane forever,
discoverable only during the emergency it was built for.

So the load-bearing test here is REACHABILITY, same as the m3 doorman's:
prove the discharge path can actually be walked, not merely that the refusal
works. A mechanism whose failure you can demonstrate but whose recovery you
cannot is a trap with a manual.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core import emergency_completion as ec


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Point the lane's marker/debt/history files at a temp home so no test
    touches the real install."""
    monkeypatch.setattr(ec, "divineos_home", lambda: tmp_path)
    monkeypatch.setattr(ec, "_log_ledger", lambda *a, **k: None)
    yield


# --------------------------------------------------------------------------
# REACHABILITY — the tests that would have caught the missing command
# --------------------------------------------------------------------------


def test_the_resolve_command_is_registered():
    """THE regression. The core docstring prescribed this exact invocation
    while nothing in the CLI answered to it."""
    result = CliRunner().invoke(cli, ["emergency-completion", "resolve", "--help"])
    assert result.exit_code == 0
    assert "--diagnosis" in result.output


def test_arm_then_consume_then_resolve_can_be_walked_end_to_end():
    """The full lifecycle, which was unreachable at its last step. If this
    cannot complete, one emergency completion bricks the lane permanently."""
    runner = CliRunner()

    armed = runner.invoke(
        cli,
        [
            "emergency-completion",
            "arm",
            "--reason",
            "In-flight critical repair of the ledger hash chain; the gate "
            "false-positived on a read-only verification step.",
            "--for",
            "claim-probe-1",
            "--risk",
            "If this is wrong the verification is skipped and a corrupt event "
            "survives into the chain unnoticed.",
        ],
    )
    assert armed.exit_code == 0, armed.output
    assert ec.is_armed() is True

    assert ec.consume_if_armed(consumed_by="probe-gate") is not None
    assert ec.has_outstanding_debt() is True

    resolved = runner.invoke(
        cli,
        [
            "emergency-completion",
            "resolve",
            "--diagnosis",
            "(a) The gate should have distinguished read-only verification "
            "from substrate mutation. (b) The emergency classification was "
            "correct in hindsight. (c) Splitting the gate's tool matcher so "
            "read-only paths never reach it prevents the false positive.",
        ],
    )
    assert resolved.exit_code == 0, resolved.output
    assert ec.has_outstanding_debt() is False, "debt survived its own discharge command"


def test_the_lane_reopens_after_a_discharge():
    """The consequence that makes the missing command load-bearing rather
    than cosmetic: arm must succeed again once the debt is cleared."""
    reason = "Second in-flight repair after the first debt was discharged cleanly."
    risk = "If wrong, the second repair proceeds without its gate check."

    ec.arm(reason=reason, for_ref="claim-probe-2", risk=risk)
    ec.consume_if_armed(consumed_by="probe-gate")
    ec.resolve_debt(
        diagnosis=(
            "(a) Same class as the first: read-only vs mutation. (b) Correct "
            "in hindsight. (c) The matcher split lands in the same change and "
            "removes this class of false positive entirely."
        )
    )

    armed = ec.arm(reason=reason, for_ref="claim-probe-3", risk=risk)
    assert armed.for_ref == "claim-probe-3"


# --------------------------------------------------------------------------
# The refusing direction still has to work
# --------------------------------------------------------------------------


def test_resolve_refuses_a_short_diagnosis():
    """The >=100 char floor is the discipline. A command that accepts "fixed"
    would make the debt a formality."""
    result = CliRunner().invoke(cli, ["emergency-completion", "resolve", "--diagnosis", "fixed"])
    assert result.exit_code == 1
    assert "Refused" in result.output


def test_resolve_refuses_when_there_is_no_debt():
    result = CliRunner().invoke(
        cli,
        [
            "emergency-completion",
            "resolve",
            "--diagnosis",
            "(a) nothing to distinguish here (b) not applicable in hindsight "
            "(c) no structural change is called for because no debt exists.",
        ],
    )
    assert result.exit_code == 1


def test_status_reports_a_clean_lane():
    result = CliRunner().invoke(cli, ["emergency-completion", "status"])
    assert result.exit_code == 0
    assert "none outstanding" in result.output
