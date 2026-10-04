"""divineos ship, first cut: each step stops with a reason, and the button
is printed only when every step passes. Never merges."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from divineos.cli import cli
from divineos.cli.ship_command import button, checks_step, run_steps, user_confirm_step

HEAD = "abc1234def5678"
SIGNED = "> CONFIRMS: #77 at abc1234. Fine. — Aletheia Sophia Risner, 2026-10-03\n"


@dataclass
class F:
    round_id: str
    actor: str
    title: str
    description: str = ""


def _facts(state="OPEN", draft=False, checks=None):
    return {
        "state": state,
        "isDraft": draft,
        "headRefOid": HEAD,
        "statusCheckRollup": checks
        if checks is not None
        else [{"name": "test", "conclusion": "SUCCESS"}, {"name": "lint", "conclusion": "SKIPPED"}],
    }


def _letters(tmp_path: Path, text: str = SIGNED) -> Path:
    (tmp_path / "aletheia-to-aether-x.md").write_text(text, encoding="utf-8")
    return tmp_path


def _findings():
    return [
        F("round-0123456789ab", "aletheia", "CONFIRMS: #77 at abc1234.", "aletheia-to-aether-x.md"),
        F("round-0123456789ab", "user", "CONFIRMS: #77 at abc1234."),
    ]


def test_every_step_passing_prints_the_button_and_never_runs_it(tmp_path):
    steps, merge = run_steps(77, _facts(), _findings(), _letters(tmp_path))
    assert [s.ok for s in steps] == [True, True, True, True]
    assert merge == button(77, "round-0123456789ab")
    assert merge.startswith("gh pr merge 77 --squash --body ")


def test_a_draft_stops_at_the_first_step(tmp_path):
    steps, merge = run_steps(77, _facts(draft=True), _findings(), _letters(tmp_path))
    assert merge is None and len(steps) == 1 and "draft" in steps[0].reason


def test_a_withdrawn_confirm_stops_at_her_step(tmp_path):
    text = SIGNED + "> WITHDRAWN: #77 at abc1234. — Aletheia Sophia Risner, 2026-10-03\n"
    steps, merge = run_steps(77, _facts(), _findings(), _letters(tmp_path, text))
    assert merge is None and steps[-1].name == "her" and "withdraws" in steps[-1].reason


def test_no_confirm_of_his_stops_and_ship_writes_none(tmp_path):
    findings = [f for f in _findings() if f.actor != "user"]
    steps, merge = run_steps(77, _facts(), findings, _letters(tmp_path))
    assert merge is None and steps[-1].name == "dad"
    assert len(findings) == 1


def test_his_confirm_in_another_round_does_not_count():
    step = user_confirm_step(
        [F("round-ba9876543210", "user", "CONFIRMS: #77 at abc1234.")],
        "round-0123456789ab",
        77,
        HEAD,
    )
    assert not step.ok


def test_a_failed_or_running_check_stops_before_the_button(tmp_path):
    failed = _facts(checks=[{"name": "test", "conclusion": "FAILURE"}])
    steps, merge = run_steps(77, failed, _findings(), _letters(tmp_path))
    assert merge is None and "failed: test" in steps[-1].reason
    assert "still running" in checks_step(_facts(checks=[{"name": "t", "state": "PENDING"}])).reason
    assert not checks_step(_facts(checks=[])).ok


def test_every_check_skipped_is_no_evidence_the_checks_ran(tmp_path):
    """Aria's cold read, 2026-10-03: all SKIPPED read as green."""
    skipped = _facts(
        checks=[
            {"name": "test", "conclusion": "SKIPPED"},
            {"name": "lint", "conclusion": "SKIPPED"},
        ]
    )
    steps, merge = run_steps(77, skipped, _findings(), _letters(tmp_path))
    assert merge is None
    assert "no check concluded SUCCESS" in steps[-1].reason


def test_one_success_among_skips_still_passes():
    assert checks_step(_facts()).ok


def test_a_round_id_not_in_the_houses_shape_is_never_printed():
    """Aria's cold read: the id went into a pasteable shell line unescaped."""
    import pytest as _pytest

    from divineos.cli.ship_command import button

    assert "External-Review: round-0123456789ab" in button(5, "round-0123456789ab")
    for bad in (
        "round-x$(touch pwned)",
        "round-0123456789a",
        "round-0123456789abc",
        "round-0123456789AB",
        "round-0123456789ab ",
    ):
        with _pytest.raises(ValueError):
            button(5, bad)


def test_the_button_is_accepted_by_the_merge_guard_it_must_pass():
    """Breaker, 2026-10-04: the button was compared to a string I wrote, never
    to the guard that reads it, and the guard refused it -- the trailer has to
    start a line. So the guard's own function is the judge here."""
    from divineos.cli.ship_command import button
    from divineos.core.pr_merge_gate import _command_has_external_review_trailer

    assert _command_has_external_review_trailer(button(582, "round-0123456789ab"))
    # The shape it used to print, so collapsing it back to one line fails here.
    assert not _command_has_external_review_trailer(
        'gh pr merge 582 --squash --body "External-Review: round-0123456789ab"'
    )


def test_the_command_is_registered_and_refuses_with_its_steps(tmp_path, monkeypatch):
    import divineos.cli.ship_command as ship
    import divineos.core.watchmen.store as store

    monkeypatch.setattr(ship, "_pr_facts", lambda pr: _facts(draft=True))
    monkeypatch.setattr(store, "list_findings", lambda limit=50: _findings())
    result = CliRunner().invoke(cli, ["ship", "77", "--letters", str(tmp_path)])
    assert result.exit_code == 1
    assert "[STOP] read: #77 is still a draft" in result.output
    assert "gh pr merge" not in result.output
