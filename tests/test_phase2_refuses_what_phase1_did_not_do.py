"""Phase 2 believes a finished phase 1 only when phase 1 says, step by step, that it ran.

Draft: docs/drafts/phase_2_takes_the_rebuilt_module_from_551_draft_2026-11-09.md
Walk: walk-c1e91a70c961.

Every case here is a marker some reader ran against the real module on 2026-11-09,
written as a test so a later copy of the module cannot bring the flaw back unnoticed
(Dawkins): the July build accepted main's dry run as a completed phase 1, read a null
cycle id as the text "None", raised on infinity and took `true` for a number. #551's
rebuilt module refuses the first two; infinity and booleans were wrong in both.

These tests go by behaviour (what a marker on disk makes the public reader and the
commands do), not by private names, so they hold for whichever module is underneath.
"""

import json

import click
import pytest
from click.testing import CliRunner

from divineos.core import auto_cycle
from divineos.core import auto_cycle_phase2 as p2

GOOD_STEPS = {
    "commit": {"ran": True, "succeeded": True},
    "extract": {"ran": True, "succeeded": True},
    "sleep": {"ran": True, "succeeded": True},
}
DRY_STEPS = {name: {"ran": False, "succeeded": True} for name in GOOD_STEPS}


@pytest.fixture(autouse=True)
def _own_home(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    yield


def _marker(body: str) -> None:
    path = auto_cycle.marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _marker_for(**fields) -> None:
    base = {"cycle_id": "c1", "trigger_context_pct": 88.0, "steps": GOOD_STEPS}
    base.update(fields)
    _marker(json.dumps(base))


def test_a_good_marker_reads_as_a_completed_phase_one():
    """The control: without it, every refusal below could be a broken reader."""
    _marker_for(phase1_tokens_used=10)
    result = p2.read_handshake()
    assert result is not None
    assert result.cycle_id == "c1"


def test_mains_dry_run_is_not_a_completed_phase_one():
    """Every step ran=False, succeeded=True: nothing happened, so no rest menu."""
    _marker_for(steps=DRY_STEPS)
    assert p2.read_handshake() is None


def test_a_null_cycle_id_is_refused_not_turned_into_the_text_none():
    _marker_for(cycle_id=None)
    assert p2.read_handshake() is None


@pytest.mark.parametrize("field", ["phase1_tokens_used", "budget_remaining_est"])
@pytest.mark.parametrize("raw", ["1e999", "-1e999"])
def test_infinity_in_a_count_returns_none_and_does_not_raise(field, raw):
    body = json.dumps({"cycle_id": "c1", "trigger_context_pct": 88.0, "steps": GOOD_STEPS})
    _marker(body[:-1] + f', "{field}": {raw}' + "}")
    assert p2.read_handshake() is None


@pytest.mark.parametrize(
    "field", ["trigger_context_pct", "phase1_tokens_used", "budget_remaining_est"]
)
def test_true_is_not_a_number(field):
    _marker_for(**{field: True})
    assert p2.read_handshake() is None


# Behaviours of the July build (#753) that the rebuilt module (#551) did not carry, kept
# because the walk (Hinton) said to weigh what was learned by being attacked: which
# checkout a cycle ran in, the folder the refusal names, and one home for all three files.


def test_repo_root_is_carried_into_the_audit_summary():
    _marker_for(repo_root="C:/some/checkout")
    result = p2.read_handshake()
    assert result is not None
    assert result.repo_root == "C:/some/checkout"
    assert p2._handshake_summary(result)["repo_root"] == "C:/some/checkout"


def test_an_older_marker_without_repo_root_still_reads():
    _marker_for()
    result = p2.read_handshake()
    assert result is not None
    assert result.repo_root == ""


@pytest.mark.parametrize("body", ["[]", "[1, 2]", '"just a string"', "null", ""])
def test_a_marker_that_is_not_an_object_fires_nothing(body):
    _marker(body)
    assert p2.read_handshake() is None


def test_the_refusal_names_the_folder_this_house_really_reads(tmp_path):
    why = p2.inspect_handshake()
    assert isinstance(why, p2.NoHandshake)
    assert str(auto_cycle.marker_path()) in p2.refusal_text(why)


def test_the_handshake_the_pending_offering_and_the_audit_live_in_one_home(tmp_path):
    _marker_for()
    record, _ = p2.offer_cycle()
    assert record is not None
    p2.close_cycle("no-pull-honest")
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert any("audit" in p.name for p in written), [p.name for p in written]
    assert all(tmp_path in p.parents for p in written)


def _menu(steps: dict) -> str:
    _marker_for(steps=steps)
    result = p2.read_handshake()
    assert result is not None
    return p2.render_menu(result, {})


def test_a_step_that_ran_and_failed_is_named_as_failed_in_the_menu():
    text = _menu(
        {
            "commit": {"ran": True, "succeeded": True},
            "extract": {"ran": True, "succeeded": False, "error_class": "OSError"},
        }
    )
    assert "extract" in text and "fail" in text.lower()


def test_a_clean_cycle_prints_no_caution_line_in_the_menu():
    assert "[~]" not in _menu({"commit": {"ran": True, "succeeded": True}})


@pytest.fixture
def phase2_group():
    from divineos.cli.auto_cycle_commands import auto_cycle_group
    from divineos.cli.auto_cycle_phase2_commands import register

    register(click.Group())
    return auto_cycle_group


def test_the_offer_command_refuses_a_dry_run_and_writes_no_pending_offering(phase2_group, tmp_path):
    """Through the command, the one place that belongs to neither module's own tests (Schneier)."""
    _marker_for(steps=DRY_STEPS)
    before = {p.name for p in tmp_path.rglob("*") if p.is_file()}
    result = CliRunner().invoke(phase2_group, ["offer"])
    after = {p.name for p in tmp_path.rglob("*") if p.is_file()}
    assert result.exit_code == 0, result.output
    assert (
        "Rest menu" not in result.output and "menu" not in result.output.lower().split("refus")[0]
    )
    assert not [n for n in after - before if "pending" in n], "a pending offering was written"


def test_a_dry_run_of_fire_prints_dry_not_ok(phase2_group):
    """The display half of the same fault: the reader refuses a dry run, so fire must not call it OK."""
    result = CliRunner().invoke(phase2_group, ["fire", "--dry-run", "--force"])
    assert result.exit_code == 0, result.output
    assert "[DRY]" in result.output
    assert "[OK " not in result.output


def test_phase_two_registers_offer_close_and_audit_once_and_phase_one_does_not(phase2_group):
    import inspect

    from divineos.cli import auto_cycle_commands

    assert {"offer", "close", "audit"} <= set(phase2_group.commands)
    source = inspect.getsource(auto_cycle_commands)
    for name in ("offer", "close", "audit"):
        assert f'.command("{name}")' not in source, f"phase 1's file also registers {name}"
