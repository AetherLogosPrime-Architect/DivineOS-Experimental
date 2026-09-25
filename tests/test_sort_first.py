"""Sort his message before anything else.

While a message Dad typed in this seat is kept and unsorted, every tool call but
reading and sorting him is refused, and the refusal carries his words. These
run on a temporary store and a temporary transcript; his real record is never
opened (his_asks refuses that under pytest).
"""

from __future__ import annotations

import copy
import json

import pytest
from click.testing import CliRunner

from divineos.core import front_door as fd
from divineos.core import his_asks as ha
from divineos.core import sort_first as sf
from tests.test_front_door import REAL_TURN_RECORD

SEAT = "aether"
HIS = "make it so you read what i say before you do anything else"


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    db = tmp_path / "shared" / "his" / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    return db


def _filed(text=HIS, uuid="u-1", seat=SEAT):
    said = "2026-09-24T00:00:00.000Z"
    cid = ha.mint_candidate_id("p", text, said + uuid)
    ha.file_candidate(cid, "p", text, said, seat)
    assert ha.confirm(cid, uuid, "human", text) == ha.FILED
    return uuid


def _bash(command, **extra):
    return {"tool_name": "Bash", "tool_input": {"command": command}, **extra}


# ------------------------------------------------------------ the refusal


def test_an_unsorted_message_of_his_refuses_the_next_action():
    uuid = _filed()
    verdict = sf.before_tool({"tool_name": "Edit", "tool_input": {}}, SEAT)
    assert verdict.refusal is not None
    assert HIS in verdict.refusal
    assert uuid in verdict.refusal
    assert "divineos his sort" in verdict.refusal


def test_reading_is_refused_too_because_the_reading_owed_is_his():
    _filed()
    assert sf.before_tool({"tool_name": "Read", "tool_input": {}}, SEAT).refusal


def test_nothing_waiting_refuses_nothing():
    verdict = sf.before_tool(_bash("git status"), SEAT)
    assert verdict == sf.Verdict()


def test_once_sorted_the_work_goes_on():
    uuid = _filed()
    ha.sort(uuid, ha.BUILD, "", SEAT, addressed_to="aether")
    assert sf.before_tool(_bash("git status"), SEAT) == sf.Verdict()


def test_every_waiting_message_is_shown_not_just_the_first():
    _filed("first thing he said", "u-1")
    _filed("second thing he said", "u-2")
    refusal = sf.before_tool(_bash("ls"), SEAT).refusal
    assert "first thing he said" in refusal and "second thing he said" in refusal
    assert "2 messages" in refusal


def test_a_long_message_is_shown_in_part_and_points_to_the_whole():
    _filed("word " * 600, "u-long")
    refusal = sf.before_tool(_bash("ls"), SEAT).refusal
    assert "more characters: divineos his pending" in refusal


# ------------------------------------------------------------ whose seat


def test_a_message_kept_in_the_other_window_does_not_refuse_this_one():
    _filed(seat="aria")
    assert sf.before_tool(_bash("ls"), SEAT) == sf.Verdict()


def test_a_helper_agent_is_never_asked_to_sort_him():
    _filed()
    assert sf.before_tool(_bash("ls", agent_id="helper-1"), SEAT) == sf.Verdict()


# ------------------------------------------------------------ the one open door


@pytest.mark.parametrize(
    "command",
    [
        "divineos his pending",
        "divineos his sort u-1 --kind build --to aether",
        'divineos his sort u-1 --kind not_an_ask --to both --reason "he said a | b; then c > d"',
        "cd /c/wdad && divineos his sort u-1 --kind standing --to aria",
        "PYTHONPATH=C:/wdad/src divineos his pending",
        "python -m divineos his pending",
    ],
)
def test_reading_and_sorting_him_pass(command):
    _filed()
    assert sf.before_tool(_bash(command), SEAT) == sf.Verdict()


@pytest.mark.parametrize(
    "command",
    [
        "divineos his sort u-1 --kind build --to aether && git commit -m x",
        "divineos his pending; rm -rf tests",
        "divineos his pending | tee notes.txt",
        "divineos his pending > notes.txt",
        'divineos his sort u-1 --kind build --to aether --reason "$(rm -rf tests)"',
        "divineos his sort u-1 --kind build --to aether --reason `rm -rf tests`",
        "divineos his pending\ngit status",
        "echo divineos his pending",
        "divineos hisx pending",
    ],
)
def test_the_sort_cannot_carry_other_work_through(command):
    _filed()
    assert sf.before_tool(_bash(command), SEAT).refusal


def test_the_door_is_only_for_shell_tools():
    _filed()
    verdict = sf.before_tool(
        {"tool_name": "Write", "tool_input": {"command": "divineos his pending"}}, SEAT
    )
    assert verdict.refusal


# ------------------------------------------------------------ unreadable is not empty


def test_an_unreadable_record_is_said_out_loud_and_never_read_as_clear(monkeypatch, tmp_path):
    blocker = tmp_path / "not-a-database"
    blocker.mkdir()
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(blocker))
    verdict = sf.before_tool(_bash("ls"), SEAT)
    assert verdict.refusal is None
    assert (
        verdict.could_not_read
        and "not the same as nothing of his waiting" in verdict.could_not_read
    )


# ------------------------------------------------------------ it settles first


def _his_turn_record(text, uuid):
    rec = copy.deepcopy(REAL_TURN_RECORD)
    rec.update(promptId="p-live", uuid=uuid, timestamp="2099-01-01T00:00:00.000Z")
    rec["message"]["content"] = text
    return rec


def test_it_files_his_message_itself_before_checking(tmp_path):
    """Hooks on one event run side by side: the front door's settle may not have run."""
    fd.keep({"prompt_id": "p-live", "prompt": HIS}, SEAT)
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps(_his_turn_record(HIS, "u-live")) + "\n", encoding="utf-8")
    verdict = sf.before_tool(
        {"tool_name": "Bash", "tool_input": {"command": "ls"}, "transcript_path": str(transcript)},
        SEAT,
    )
    assert verdict.refusal and "u-live" in verdict.refusal


# ------------------------------------------------------------ the Stop backstop


def test_a_reply_with_no_tool_call_is_caught_at_the_stop():
    _filed()
    assert sf.at_stop({}, SEAT).refusal


def test_the_stop_stands_down_on_retry_so_it_can_never_loop(capsys):
    _filed()
    assert sf.at_stop({"stop_hook_active": True}, SEAT) == sf.Verdict()
    assert "next tool call will refuse" in capsys.readouterr().err


def test_the_stop_says_nothing_once_he_is_sorted():
    uuid = _filed()
    ha.sort(uuid, ha.STANDING, "", SEAT, addressed_to="both")
    assert sf.at_stop({}, SEAT) == sf.Verdict()


# ------------------------------------------------------------ wired into the house


@pytest.fixture
def this_seat_is_aether(monkeypatch):
    import divineos.core.sibling_audit_rounds as seats

    monkeypatch.setattr(seats, "this_seat", lambda: SEAT)


def test_the_router_reads_his_refusal_first(this_seat_is_aether):
    from divineos.core import hook_router, hook_surfaces

    hook_router.clear()
    hook_surfaces.install()
    assert hook_router.registered("PreToolUse")[0] == "sort_first"
    assert "sort_first_stop" in hook_router.registered("Stop")


def test_the_router_refuses_through_the_real_dispatch(this_seat_is_aether):
    from divineos.core import hook_router, hook_surfaces

    _filed()
    hook_router.clear()
    hook_surfaces.install()
    result = hook_router.dispatch("PreToolUse", _bash("git status"))
    assert any(o.name == "sort_first" and HIS in o.reason for o in result.refusals)


def test_no_other_gate_may_hold_the_sort_shut():
    from divineos.core.remedy_allowlist import is_remedy

    assert is_remedy("divineos his sort u-1 --kind build --to aether")
    assert is_remedy("divineos his pending")


# ------------------------------------------------------------ the commands


@pytest.fixture
def cli(monkeypatch):
    # Registered onto a bare group: loading every command in the house costs
    # more than this file's whole time budget, and tests nothing here.
    import click

    import divineos.cli.his_commands as his_commands

    monkeypatch.setattr(his_commands, "this_seat", lambda: SEAT)
    root = click.Group()
    his_commands.register(root)
    return root


def test_the_his_commands_are_registered_on_the_real_cli():
    from pathlib import Path

    source = Path(fd.__file__).parents[1] / "cli" / "__init__.py"
    assert "his_commands.register(cli)" in source.read_text(encoding="utf-8")


def test_pending_shows_his_words_whole(cli):
    _filed("word " * 600, "u-long")
    out = CliRunner().invoke(cli, ["his", "pending"])
    assert out.exit_code == 0, out.output
    assert out.output.count("word") == 600


def test_sort_says_who_he_said_it_to_and_clears_the_refusal(cli):
    uuid = _filed()
    out = CliRunner().invoke(cli, ["his", "sort", uuid, "--kind", "build", "--to", "aether"])
    assert out.exit_code == 0, out.output
    assert "said to aether" in out.output
    assert "He is still owed an answer" in out.output
    assert ha.addressed_to(uuid) == "aether"
    assert sf.before_tool(_bash("ls"), SEAT) == sf.Verdict()


def test_a_second_sort_is_refused_and_names_the_first(cli):
    uuid = _filed()
    runner = CliRunner()
    runner.invoke(cli, ["his", "sort", uuid, "--kind", "build", "--to", "aether"])
    out = runner.invoke(cli, ["his", "sort", uuid, "--kind", "standing", "--to", "aether"])
    assert out.exit_code != 0
    assert "already sorted" in out.output


def test_not_an_ask_without_a_reason_is_refused(cli):
    uuid = _filed("proceed")
    out = CliRunner().invoke(cli, ["his", "sort", uuid, "--kind", "not_an_ask", "--to", "aether"])
    assert out.exit_code != 0
    assert "needs a reason" in out.output
