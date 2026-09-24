"""The front door keeps every message of his, then asks the harness whose it was.

Transcript fixtures copy the shape of real records (field names read from the
live transcript 2026-09-24: a prompt's own record carries ``origin`` and
``promptId``; the tool results and hook feedback of that turn carry the same
``promptId`` and no ``origin``). Everything runs on a temporary store.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from divineos.core import front_door as fd
from divineos.core import his_asks as ha

HIS = "please keep what i ask for, all of it"


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    db = tmp_path / "shared" / "his" / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    return db


def _prompt(pid, text, kind="human", uuid=None):
    return {
        "type": "user",
        "uuid": uuid or f"rec-{pid}",
        "promptId": pid,
        "origin": {"kind": kind},
        "message": {"role": "user", "content": text},
    }


def _tool_result(pid):
    return {
        "type": "user",
        "uuid": f"tr-{pid}",
        "promptId": pid,
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


def _transcript(tmp_path, *records):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def _could_not_file(db):
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT ref, error FROM could_not_file").fetchall()


def test_what_he_typed_is_kept_the_moment_it_arrives():
    assert fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether") == "p1"
    assert ha.unsettled() == ["p1"]


def test_an_empty_prompt_has_nothing_of_his_to_keep():
    assert fd.keep({"prompt_id": "p1", "prompt": "   "}, "aether") is None
    assert ha.unsettled() == []


def test_a_failed_keep_is_recorded_and_never_costs_him_the_prompt(monkeypatch, temp_store):
    def broken(*_a, **_k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(ha, "file_candidate", broken)
    assert fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether") is None
    assert _could_not_file(temp_store) == [("p1", "OperationalError: disk I/O error")]


def test_a_payload_with_no_prompt_id_is_recorded_as_could_not_file(temp_store):
    assert fd.keep({"prompt": HIS}, "aether") is None
    assert _could_not_file(temp_store)[0][0] == "(no prompt id)"


def test_his_record_confirms_the_candidate_onto_its_uuid(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _prompt("p1", HIS, uuid="u-his"), _tool_result("p1"))
    assert fd.settle(path, "aether") == {"p1": ha.FILED}
    assert [k.uuid for k in ha.pending()] == ["u-his"]


def test_a_notification_is_withdrawn_by_the_harness_stamp_not_by_its_words(tmp_path):
    words = "Monitor event: a letter arrived"
    fd.keep({"prompt_id": "p2", "prompt": words}, "aether")
    path = _transcript(tmp_path, _prompt("p2", words, kind="task-notification"))
    assert fd.settle(path, "aether") == {"p2": ha.WITHDRAWN}
    assert ha.pending() == []


def test_a_tool_result_sharing_his_prompt_id_never_settles_it(tmp_path):
    """Only the prompt's own record carries the stamp; the rest of the turn does not."""
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _tool_result("p1"))
    assert fd.settle(path, "aether") == {}
    assert ha.unsettled() == ["p1"]


def test_a_tool_result_that_quotes_the_word_origin_still_never_settles_it(tmp_path):
    """The cheap text prefilter is not the guard; the record's own field is.

    Found by jamming the lock: removing the field check left every test green,
    because no fixture line mentioned "origin" in its content.
    """
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    rec = _tool_result("p1")
    rec["toolUseResult"] = {"origin": {"kind": "human"}, "stdout": HIS}
    rec["message"]["content"] = [{"type": "text", "text": HIS}]
    assert fd.settle(_transcript(tmp_path, rec), "aether") == {}
    assert ha.unsettled() == ["p1"]


def test_a_record_that_does_not_hold_his_words_is_refused_loudly(tmp_path, temp_store):
    """The uuid binds the words: his candidate is never settled onto another message."""
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _prompt("p1", "something he never typed"))
    assert fd.settle(path, "aether") == {}
    assert ha.unsettled() == ["p1"]
    assert _could_not_file(temp_store)[0][0] == "p1"


def test_the_other_seats_candidate_is_left_for_that_seat(tmp_path):
    fd.keep({"prompt_id": "aria-p", "prompt": HIS}, "aria")
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _prompt("p1", HIS))
    assert fd.settle(path, "aether") == {"p1": ha.FILED}
    assert ha.unsettled() == ["aria-p"]


def test_a_resumed_copy_of_his_record_is_kept_once(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    fd.keep({"prompt_id": "p1-resumed", "prompt": HIS}, "aether")
    path = _transcript(
        tmp_path, _prompt("p1", HIS, uuid="u-his"), _prompt("p1-resumed", HIS, uuid="u-his")
    )
    assert fd.settle(path, "aether") == {"p1": ha.FILED, "p1-resumed": ha.WITHDRAWN}
    assert len(ha.pending()) == 1


def test_settling_twice_changes_nothing(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    path = _transcript(tmp_path, _prompt("p1", HIS))
    fd.settle(path, "aether")
    assert fd.settle(path, "aether") == {}


def test_his_words_inside_list_content_are_read(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    rec = _prompt("p1", "")
    rec["message"]["content"] = [{"type": "text", "text": HIS}]
    assert fd.settle(_transcript(tmp_path, rec), "aether") == {"p1": ha.FILED}


def test_a_missing_transcript_settles_nothing_and_loses_nothing(tmp_path):
    fd.keep({"prompt_id": "p1", "prompt": HIS}, "aether")
    assert fd.settle(tmp_path / "gone.jsonl", "aether") == {}
    assert ha.unsettled() == ["p1"]
