"""Delivery in full must silence the re-ask, not just the current demand.

MEASURED, NOT SUSPECTED. On 2026-09-03 this gate demanded the same 40-line
letter four separate times in one session, and its clears log already held 22
records for that one path. It was clearing correctly every single time.

Both halves existed and neither knew about the other:

    delivery-in-full   cleared the pending requirement, wrote CLEAR_LOG
    re-arm suppressor  read SEEN_READS, which only recorded Read TOOL CALLS

So a file the gate handed over in full satisfied the moment and left no memory.
The surface re-registered it on the next prompt. The loop ran until the session
ended, and from inside it looked exactly like the clearing being broken -- which
is how it survived a previous fix aimed at the wrong half.

That is this session's own subject arriving inside the instrument that had been
reporting it: two correct mechanisms writing to different ledgers, with the gap
invisible from inside either one.

These tests reproduce the LOOP rather than the symptom. A test that only checks
"the requirement cleared" passed throughout the entire defect.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import read_gate


@pytest.fixture
def gate_state(tmp_path, monkeypatch):
    """Point every state seam at a scratch dir, including the undocumented ones."""
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(read_gate, "STATE_FILE", tmp_path / "read_gate.json", raising=False)
    monkeypatch.setattr(read_gate, "SEEN_READS", tmp_path / "seen.json", raising=False)
    monkeypatch.setattr(read_gate, "CLEAR_LOG", tmp_path / "clears.jsonl", raising=False)
    monkeypatch.setattr(read_gate, "REARM_LOG", tmp_path / "rearm.jsonl", raising=False)
    return tmp_path


def _seen(state) -> dict:
    path = state / "seen.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def test_delivery_is_recorded_where_the_suppressor_looks(gate_state):
    """The whole defect in one assertion.

    Before the fix this file had no INLINE_DELIVERY entry after a full
    delivery, so the suppressor found nothing and the surface re-armed.
    """
    (gate_state / "seen.json").write_text(
        json.dumps({"transcript": "/session/one.jsonl", "reads": []}), encoding="utf-8"
    )

    read_gate._record_inline_delivery("exploration/letters/a_letter.md")

    entries = _seen(gate_state).get("reads", [])
    delivered = [e for e in entries if e[0] == "INLINE_DELIVERY"]
    assert delivered, (
        "a full inline delivery left no trace in the ledger the re-arm "
        "suppressor reads; the surface will re-register this path forever"
    )
    assert "a_letter.md" in delivered[0][1]


def test_the_record_says_delivery_rather_than_read(gate_state):
    """Neither event may wear the other's name.

    The clears log carries an extent precisely so that "the gate handed it
    over" and "I went and opened it" stay distinguishable. Recording a delivery
    as a Read would erase that distinction in the other ledger.
    """
    (gate_state / "seen.json").write_text(
        json.dumps({"transcript": "/session/one.jsonl", "reads": []}), encoding="utf-8"
    )
    read_gate._record_inline_delivery("exploration/x.md")
    names = {e[0] for e in _seen(gate_state).get("reads", [])}
    assert "Read" not in names, "a delivery was recorded as though it were a Read tool call"
    assert names == {"INLINE_DELIVERY"}


def test_no_transcript_means_no_record_rather_than_an_invented_one(gate_state):
    """Silence beats inventing a session key.

    A delivery filed under a made-up transcript would let one session's inline
    silence a requirement in the NEXT session -- the opposite failure, and the
    worse one, because it makes the gate quieter than anyone asked for.
    """
    (gate_state / "seen.json").write_text(json.dumps({"reads": []}), encoding="utf-8")
    read_gate._record_inline_delivery("exploration/x.md")
    assert not _seen(gate_state).get("reads"), (
        "a delivery was recorded with no transcript to scope it to; that would leak across sessions"
    )


def test_an_absent_ledger_leaves_the_gate_exactly_as_strict(gate_state):
    """Fails toward the old behaviour, never toward a quieter gate."""
    read_gate._record_inline_delivery("exploration/x.md")
    assert not (gate_state / "seen.json").is_file(), (
        "the suppressor created state where none existed; a mechanism that "
        "cannot read must not write"
    )


def test_clearing_a_requirement_actually_records_the_delivery(gate_state):
    """THE WIRE, not the mechanism -- and the first version of this file missed it.

    Every other test here calls ``_record_inline_delivery`` directly. All five
    passed with the fix mutated out of ``_mark_satisfied``, because none of them
    asked whether anything CALLS it.

    That is the register's defect rebuilt inside the test written for its
    cousin, one hour later: a mechanism that exists and nothing invokes. Caught
    by removing the call and watching the suite stay green, which is the only
    reason it is here.
    """
    read_gate.require_read("surface", "docs/AUTOMATION_REGISTER.md", "why")
    (gate_state / "seen.json").write_text(
        json.dumps({"transcript": "/session/one.jsonl", "reads": []}), encoding="utf-8"
    )

    read_gate._mark_satisfied("docs/AUTOMATION_REGISTER.md", "inlined in full")

    entries = {tuple(e) for e in _seen(gate_state).get("reads", [])}
    assert any(name == "INLINE_DELIVERY" for name, _ in entries), (
        "clearing a requirement by delivery did not record it where the re-arm "
        "suppressor looks -- the wire is missing and the loop is still open"
    )


def test_existing_reads_survive_a_delivery(gate_state):
    """The delivery is added, not substituted for what was already known."""
    (gate_state / "seen.json").write_text(
        json.dumps({"transcript": "/session/one.jsonl", "reads": [["Read", "docs/other.md"]]}),
        encoding="utf-8",
    )
    read_gate._record_inline_delivery("exploration/x.md")
    entries = {tuple(e) for e in _seen(gate_state).get("reads", [])}
    assert ("Read", "docs/other.md") in entries, "an earlier read was dropped"
    assert ("INLINE_DELIVERY", "exploration/x.md") in entries
