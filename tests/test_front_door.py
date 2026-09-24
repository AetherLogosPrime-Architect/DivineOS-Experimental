"""The front door keeps every message of his, then asks the harness whose it was.

Both record shapes are copied from the live transcript (2026-09-24), every field
as recorded, with only the words, paths and session names replaced. A message
that starts a turn is a ``user`` record with ``origin`` and ``promptId``; a
message sent mid-turn is a ``queued_command`` attachment carrying its stamp in
``attachment.origin`` and no prompt id at all. Everything runs on a temporary
store.
"""

from __future__ import annotations

import copy
import json
import sqlite3

import pytest

from divineos.core import front_door as fd
from divineos.core import his_asks as ha

HIS = "please keep what i ask for, all of it"
LATER = "2099-01-01T00:00:00.000Z"  # after any keeping a test makes

# Copied from a real record, 2026-09-19. Only the words and locations replaced.
REAL_TURN_RECORD = {
    "parentUuid": "68b303cc-e047-419a-82bf-747455b0d6b7",
    "isSidechain": False,
    "promptId": "c701829a-0046-4d7d-9f26-9b87690bfe2a",
    "type": "user",
    "message": {"role": "user", "content": "<HIS WORDS>"},
    "uuid": "a4c6fc08-3bf8-4433-ad58-b04aaa0a7221",
    "timestamp": "2026-09-19T01:07:05.712Z",
    "permissionMode": "auto",
    "origin": {"kind": "human"},
    "promptSource": "sdk",
    "userType": "external",
    "entrypoint": "<entrypoint>",
    "cwd": "<cwd>",
    "sessionId": "<sessionId>",
    "version": "<version>",
    "gitBranch": "<gitBranch>",
}

# Copied from a real queue slip, 2026-09-23. Only the words and locations replaced.
REAL_QUEUE_SLIP = {
    "parentUuid": "319ca775-ce3c-44d9-8ee5-c3e3e782af8e",
    "isSidechain": False,
    "attachment": {
        "type": "queued_command",
        "prompt": "<HIS WORDS>",
        "source_uuid": "e00baa8e-9471-422a-99b9-2808f4eddf55",
        "commandMode": "prompt",
        "origin": {"kind": "human"},
        "timestamp": "2026-09-23T07:46:37.771Z",
        "humanTurn": True,
    },
    "type": "attachment",
    "uuid": "f21fefa1-c19a-477b-bb33-30231c9c93ff",
    "timestamp": "2026-09-23T07:46:37.771Z",
    "rendered": [{"content": "<system-reminder>\n<HIS WORDS>\n</system-reminder>"}],
    "userType": "external",
    "entrypoint": "<entrypoint>",
    "cwd": "<cwd>",
    "sessionId": "<sessionId>",
    "version": "<version>",
    "gitBranch": "<gitBranch>",
    "slug": "<slug>",
}


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    db = tmp_path / "shared" / "his" / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    return db


def _turn(pid, text, kind="human", uuid=None, at=LATER):
    rec = copy.deepcopy(REAL_TURN_RECORD)
    rec.update(promptId=pid, uuid=uuid or f"rec-{pid}", timestamp=at)
    rec["origin"] = {"kind": kind}
    rec["message"]["content"] = text
    return rec


def _slip(text, uuid, kind="human", at=LATER, mode="prompt"):
    rec = copy.deepcopy(REAL_QUEUE_SLIP)
    rec.update(uuid=uuid, timestamp=at)
    rec["attachment"].update(prompt=text, commandMode=mode, timestamp=at)
    if kind is None:
        del rec["attachment"]["origin"]
    else:
        rec["attachment"]["origin"] = {"kind": kind}
    return rec


def _tool_result(pid):
    return {
        "type": "user",
        "uuid": f"tr-{pid}",
        "promptId": pid,
        "timestamp": LATER,
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


def _transcript(tmp_path, *records):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def _could_not_file(db):
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT ref, error FROM could_not_file").fetchall()


def _open():
    return [c.his_text for c in ha.unsettled()]


# ------------------------------------------------------------------ keeping


def test_what_he_typed_is_kept_the_moment_it_arrives():
    assert fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    assert _open() == [HIS]


def test_an_empty_prompt_has_nothing_of_his_to_keep():
    assert fd.keep({"prompt_id": "p1", "prompt": "   "}, "aether") is None
    assert _open() == []


def test_many_messages_under_one_prompt_id_are_each_kept():
    """Measured 2026-09-24: one prompt id sat on ten of his messages."""
    for text in ("first thing", "second thing", "third thing"):
        fd.keep({"prompt_id": "c701829a", "prompt": text}, "aether")
    assert sorted(_open()) == ["first thing", "second thing", "third thing"]


def test_a_missing_prompt_id_does_not_stop_the_keeping():
    """The prompt id is a hint for finding his record, never the key."""
    assert fd.keep({"prompt": HIS}, "aether")
    assert _open() == [HIS]


def test_a_failed_keep_is_recorded_and_never_costs_him_the_prompt(monkeypatch, temp_store):
    def broken(*_a, **_k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(ha, "file_candidate", broken)
    assert fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether") is None
    assert _could_not_file(temp_store) == [("p1", "OperationalError: disk I/O error")]


# ----------------------------------------------------------------- settling


def test_a_message_that_starts_a_turn_is_confirmed_onto_its_record(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _turn("p1", HIS, uuid="u-his"), _tool_result("p1"))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]
    assert [k.uuid for k in ha.pending()] == ["u-his"]


def test_a_message_sent_mid_turn_is_found_in_its_queue_slip(tmp_path):
    """The shape every earlier reader missed: no prompt id, stamp in the attachment."""
    fd.keep({"prompt_id": "running-turn", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _slip(HIS, "u-slip"))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]
    assert [k.uuid for k in ha.pending()] == ["u-slip"]


def test_a_notification_slip_is_withdrawn_by_its_mode_not_its_words(tmp_path):
    words = "<task-notification> a letter arrived </task-notification>"
    fd.keep({"prompt_id": "running-turn", "prompt": words}, "aether")
    path = _transcript(tmp_path, _slip(words, "u-note", kind=None, mode="task-notification"))
    assert list(fd.settle(path, "aether").values()) == [ha.WITHDRAWN]
    assert ha.pending() == []


def test_a_notification_that_starts_a_turn_is_withdrawn_by_its_stamp(tmp_path):
    words = "Monitor event: a letter arrived"
    fd.keep({"prompt_id": "p2", "prompt": words}, "aether")
    path = _transcript(tmp_path, _turn("p2", words, kind="task-notification"))
    assert list(fd.settle(path, "aether").values()) == [ha.WITHDRAWN]


# A real build notice the harness stamped human (slip of 2026-07-17, shortened).
REAL_CI_NOTICE = (
    "<ci-monitor-event>AetherLogosPrime-Architect/DivineOS-Experimental PR #355 has 1 new"
    " review comment:\n- github-actions[bot]: ## Audit-stamp reminder — guardrail-touching"
    " PR\n\nPlease address the feedback and push a fix.</ci-monitor-event>"
)


def test_a_build_notice_stamped_human_is_never_filed_as_his(tmp_path):
    """Aria, 2026-09-24: the harness stamps build notices human. Stamp plus
    containment alone would have filed this as words he typed."""
    fd.keep({"prompt_id": "running-turn", "prompt": REAL_CI_NOTICE}, "aether")
    path = _transcript(tmp_path, _slip(REAL_CI_NOTICE, "u-ci", kind="human"))
    assert list(fd.settle(path, "aether").values()) == [ha.WITHDRAWN]
    assert ha.pending() == []


def test_a_turn_record_that_is_only_a_reminder_is_not_his(tmp_path):
    words = "<system-reminder>\nsomething the machine said\n</system-reminder>"
    fd.keep({"prompt_id": "p1", "prompt": words}, "aether")
    path = _transcript(tmp_path, _turn("p1", words))
    assert list(fd.settle(path, "aether").values()) == [ha.WITHDRAWN]


def test_his_words_beside_an_envelope_are_still_his(tmp_path):
    words = f"<system-reminder>\nnoise\n</system-reminder>\n{HIS}"
    fd.keep({"prompt_id": "p1", "prompt": words}, "aether")
    path = _transcript(tmp_path, _turn("p1", words))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]


def test_an_unstamped_prompt_slip_is_left_visible_not_guessed(tmp_path):
    fd.keep({"prompt_id": "running-turn", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _slip(HIS, "u-bare", kind=None, mode="prompt"))
    assert fd.settle(path, "aether") == {}
    assert _open() == [HIS]


def test_two_identical_short_messages_land_on_two_records_in_order(tmp_path):
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    path = _transcript(
        tmp_path,
        _slip("proceed", "u-first", at="2099-01-01T00:00:00.000Z"),
        _slip("proceed", "u-second", at="2099-01-01T00:05:00.000Z"),
    )
    assert list(fd.settle(path, "aether").values()) == [ha.FILED, ha.FILED]
    assert sorted(k.uuid for k in ha.pending()) == ["u-first", "u-second"]


def test_a_new_message_is_never_settled_onto_an_old_record_of_the_same_words(tmp_path):
    """His record cannot be older than his keeping."""
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    path = _transcript(tmp_path, _slip("proceed", "u-old", at="2020-01-01T00:00:00.000Z"))
    assert fd.settle(path, "aether") == {}
    assert _open() == ["proceed"]


def test_the_second_of_two_messages_waits_for_its_own_record(tmp_path):
    """Only one record exists yet, so only one of the two is settled."""
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    path = _transcript(tmp_path, _slip("proceed", "u-first"))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]
    assert _open() == ["proceed"]


def _kept_at(monkeypatch, moment):
    monkeypatch.setattr(fd, "_now_iso", lambda: moment)


def test_a_slip_written_before_the_door_saw_it_is_still_his(monkeypatch, tmp_path):
    """Found by dogfooding on 2026-09-24, not by a test: his slip was written
    thirteen seconds before the door saw the message, and the first door read
    that as too old to be his."""
    _kept_at(monkeypatch, "2026-09-24T22:23:36.959+00:00")
    fd.keep({"prompt_id": "running-turn", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _slip(HIS, "u-slip", at="2026-09-24T22:23:23.709Z"))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]


def test_a_slip_older_than_any_step_could_hold_it_is_some_other_days_words(monkeypatch, tmp_path):
    _kept_at(monkeypatch, "2026-09-24T22:23:36.959+00:00")
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    path = _transcript(tmp_path, _slip("proceed", "u-old", at="2026-09-24T21:00:00.000Z"))
    assert fd.settle(path, "aether") == {}


def test_a_record_already_holding_his_message_is_never_offered_again(monkeypatch, tmp_path):
    """Inside the waiting window, the store's own memory is the guard."""
    _kept_at(monkeypatch, "2026-09-24T22:20:00.000+00:00")
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    path = _transcript(tmp_path, _slip("proceed", "u-first", at="2026-09-24T22:19:58.000Z"))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]

    _kept_at(monkeypatch, "2026-09-24T22:25:00.000+00:00")
    fd.keep({"prompt_id": "running-turn", "prompt": "proceed"}, "aether")
    assert fd.settle(path, "aether") == {}
    assert _open() == ["proceed"]
    assert [k.uuid for k in ha.pending()] == ["u-first"]


def test_a_slip_pushed_past_the_first_read_by_a_long_step_is_still_found(monkeypatch, tmp_path):
    """Found by dogfooding: a slip sat just past the fixed tail the first door read."""
    monkeypatch.setattr(fd, "_TAIL_BYTES", 2048)
    _kept_at(monkeypatch, "2026-09-24T22:23:36.959+00:00")
    fd.keep({"prompt_id": "running-turn", "prompt": HIS}, "aether")
    filler = [_tool_result(f"noise-{n}") for n in range(200)]
    for rec in filler:
        rec["timestamp"] = "2026-09-24T22:30:00.000Z"
    path = _transcript(tmp_path, _slip(HIS, "u-slip", at="2026-09-24T22:23:23.709Z"), *filler)
    assert path.stat().st_size > 8 * 2048
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]


def test_not_knowing_which_records_are_his_settles_nothing(monkeypatch, tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    monkeypatch.setattr(ha, "already_kept", lambda _uuids: None)
    assert fd.settle(_transcript(tmp_path, _turn("p1", HIS)), "aether") is None
    assert _open() == [HIS]


def test_a_tool_result_sharing_his_prompt_id_never_settles_it(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    assert fd.settle(_transcript(tmp_path, _tool_result("p1")), "aether") == {}
    assert _open() == [HIS]


def test_a_tool_result_carrying_its_own_nested_origin_never_settles_it(tmp_path):
    """Found by jamming the lock: the text prefilter is not the guard."""
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    rec = _tool_result("p1")
    rec["toolUseResult"] = {"origin": {"kind": "human"}, "stdout": HIS}
    rec["message"]["content"] = [{"type": "text", "text": HIS}]
    assert fd.settle(_transcript(tmp_path, rec), "aether") == {}


def test_a_record_with_a_different_prompt_id_is_not_his_record(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    assert fd.settle(_transcript(tmp_path, _turn("p-other", HIS)), "aether") == {}


def test_a_record_that_does_not_hold_his_words_is_never_his(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    assert fd.settle(_transcript(tmp_path, _turn("p1", "something he never typed")), "aether") == {}
    assert _open() == [HIS]


def test_a_subagents_record_is_not_his(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    rec = _turn("p1", HIS)
    rec["isSidechain"] = True
    assert fd.settle(_transcript(tmp_path, rec), "aether") == {}


def test_the_other_seats_candidate_is_left_for_that_seat(tmp_path):
    fd.keep({"prompt_id": "aria-p", "prompt": "said to aria"}, "aria")
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _turn("p1", HIS))
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]
    assert _open() == ["said to aria"]


def test_a_resumed_copy_of_his_record_is_kept_once(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    fd.keep({"prompt_id": "p1-resumed", "prompt": HIS}, "aether")
    path = _transcript(
        tmp_path, _turn("p1", HIS, uuid="u-his"), _turn("p1-resumed", HIS, uuid="u-his")
    )
    assert list(fd.settle(path, "aether").values()) == [ha.FILED]
    assert len(ha.pending()) == 1
    assert _open() == [HIS]  # the copy stays visible, never bound a second time


def test_settling_twice_changes_nothing(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _turn("p1", HIS))
    fd.settle(path, "aether")
    assert fd.settle(path, "aether") == {}


def test_his_words_inside_list_content_are_read(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    rec = _turn("p1", "")
    rec["message"]["content"] = [{"type": "text", "text": HIS}]
    assert list(fd.settle(_transcript(tmp_path, rec), "aether").values()) == [ha.FILED]


def test_a_missing_transcript_settles_nothing_and_loses_nothing(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    assert fd.settle(tmp_path / "gone.jsonl", "aether") == {}
    assert _open() == [HIS]


def _bash():
    """Git Bash, never the WSL relay bare "bash" resolves to here (see
    test_advisory_hooks_stay_advisory: that relay exits 1 without running the
    hook, which is could-not-look, not a result)."""
    import shutil
    from pathlib import Path

    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


needs_bash = pytest.mark.skipif(
    _bash() is None, reason="no POSIX bash here -- could-not-look, which is not a pass"
)


@needs_bash
def test_the_real_hook_keeps_then_settles_through_the_shell(tmp_path, temp_store):
    """End to end through .claude/hooks/front-door.sh, the path the house runs."""
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DIVINEOS_HIS_ASKS_DB": str(temp_store)}

    def hook(action, payload):
        return subprocess.run(
            [_bash(), ".claude/hooks/front-door.sh", action],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=root,
            env=env,
            timeout=60,
        )

    kept = hook("keep", {"prompt_id": "p-e2e", "prompt": HIS})
    assert kept.returncode == 0, kept.stderr
    assert _open() == [HIS], kept.stderr
    path = _transcript(tmp_path, _turn("p-e2e", HIS, uuid="u-e2e"))
    settled = hook("settle", {"transcript_path": str(path)})
    assert settled.returncode == 0, settled.stderr
    assert [k.uuid for k in ha.pending()] == ["u-e2e"], settled.stderr


@needs_bash
def test_a_broken_door_never_blocks_the_prompt(tmp_path):
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    done = subprocess.run(
        [_bash(), ".claude/hooks/front-door.sh", "keep"],
        input="this is not json",
        capture_output=True,
        text=True,
        cwd=root,
        timeout=60,
    )
    assert done.returncode == 0
    assert "front-door" in done.stderr


def test_an_unreadable_store_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(ha, "unsettled", lambda: None)
    assert fd.settle(tmp_path / "t.jsonl", "aether") is None
