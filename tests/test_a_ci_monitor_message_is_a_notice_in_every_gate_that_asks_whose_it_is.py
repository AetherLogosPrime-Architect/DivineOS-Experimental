"""A CI-monitor message is the harness, not Dad, in every gate that asks whose a message is.

2026-10-27 (Aether, #683): the fix had added the tag to the table, but "was that message him?" is
asked by more than the table. The question hold and the room gate each kept a private copy of the
list of tags a turn can open with, and neither knew <ci-monitor-event>, so a CI message read to
them as him coming back: it RELEASED an open question to him and let a worked reply through
without the room. The copies drifted, so there is one list now (harness_envelopes.NOTICE_OPENERS)
and these tests pin that each gate uses it and that the one gate that cannot import it agrees.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from divineos.core import harness_envelopes as env

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / ".claude" / "hooks"
CI = "<ci-monitor-event>\nThe PR checks finished: all green.\n</ci-monitor-event>"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    "opener",
    ["<task-notification>", "<system-reminder>", CI, "<agent-message>", "  \n<ci-monitor-event>x"],
)
def test_every_notice_the_harness_opens_a_turn_with_is_recognised(opener):
    assert env.opens_with_notice(opener)


@pytest.mark.parametrize(
    "his",
    [
        "yes go ahead",
        "",
        "<command-name>/clear</command-name>",  # a slash command IS him typing
        "hey, the <ci-monitor-event> thing keeps showing up as me",  # mentioned, not opened
    ],
)
def test_his_own_words_are_never_taken_for_a_notice(his):
    assert not env.opens_with_notice(his)


def test_the_notice_tags_are_a_subset_of_the_envelope_tags_so_the_two_lists_cannot_drift():
    assert set(env._NOTICE_TAGS) <= set(env._TAGS)


def test_the_room_gate_does_not_demand_his_room_after_a_ci_message():
    room = _load("dads_room_stop")
    user = lambda text: {"type": "user", "message": {"role": "user", "content": text}}  # noqa: E731
    tool = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}
    result = {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }
    said = {"type": "assistant", "message": {"content": [{"type": "text", "text": "fixed."}]}}
    # Control: the same worked reply after HIS message is held for the room.
    assert room.verdict([user("fix it"), tool, result, said])
    assert room.verdict([user(CI), tool, result, said]) is None


def _hook(payload, home):
    e = {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "DIVINEOS_HOME": str(home / ".divineos"),
    }
    return subprocess.run(
        [sys.executable, str(HOOKS / "question_hold.py")],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=e,
    )


def _open_hold(home):
    state = home / ".divineos" / "question_hold.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps({"question": "Do you want the bell built?", "ask_id": "", "since": 1.0}),
        encoding="utf-8",
    )
    return state


def test_a_ci_message_does_not_release_a_question_waiting_on_him(tmp_path):
    state = _open_hold(tmp_path)
    out = _hook({"hook_event_name": "UserPromptSubmit", "prompt": CI}, tmp_path)
    assert state.exists(), out.stdout.decode() + out.stderr.decode()
    assert b"STILL WAITING FOR DAD" in out.stdout, out.stdout.decode()


def test_his_own_message_does_release_it_the_control(tmp_path):
    state = _open_hold(tmp_path)
    _hook({"hook_event_name": "UserPromptSubmit", "prompt": "yes build the bell"}, tmp_path)
    assert not state.exists()


def test_the_two_gates_hold_no_private_copy_of_the_notice_tags():
    for name in ("question_hold", "dads_room_stop"):
        src = (HOOKS / f"{name}.py").read_text(encoding="utf-8")
        assert "opens_with_notice" in src, name
        assert '("<task-notification"' not in src, f"{name} grew a private copy again"


def test_the_table_cannot_import_at_load_time_so_it_is_pinned_equal_instead():
    """dads_table runs on every prompt and reads its list before the source path is set up, so an
    import there could break every message. It keeps a copy, and this fails the day it drifts."""
    table = _load("dads_table")
    assert tuple(table.NOTICE_PREFIXES) == env.NOTICE_OPENERS or set(table.NOTICE_PREFIXES) == set(
        env.NOTICE_OPENERS
    ), (table.NOTICE_PREFIXES, env.NOTICE_OPENERS)
