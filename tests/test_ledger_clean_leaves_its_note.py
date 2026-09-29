"""The ledger cleaner leaves a note for every page it removes, and the diary still reads true.

Anvil and Muse (Structured Chaos review, SC #10 and #11, reproduced live on a
throwaway copy 2026-09-28): clean_corrupted_events deleted on one connection
and wrote each LEDGER_CORRUPTION_REPAIRED record through a second one, which
waited on the first one's lock, failed, and was swallowed -- 1 deleted, 0
records, while the message said every deletion was logged. It also left the
chain pointing at the removed row, so the next verify called the ledger
tampered. This is their scenario, and it must fail on that code.
"""

import json

import pytest

from divineos.core import ledger
from divineos.core._ledger_base import get_connection
from divineos.core.ledger import init_db, log_event, verify_chain
from divineos.core.ledger_verify import clean_corrupted_events


@pytest.fixture
def three_events(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    ids = [log_event("NOTE", "system", {"n": n}, validate=False) for n in range(3)]
    return ids


def _break_payload(event_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE system_events SET payload = ? WHERE event_id = ?",
            (json.dumps({"n": "edited"}), event_id),
        )
        conn.commit()
    finally:
        conn.close()


def _repair_records() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT payload FROM system_events WHERE event_type = 'LEDGER_CORRUPTION_REPAIRED'"
        ).fetchall()
    finally:
        conn.close()
    return [json.loads(r[0]) for r in rows]


def test_every_removed_event_leaves_its_note(three_events):
    broken = three_events[1]
    _break_payload(broken)
    result = clean_corrupted_events()
    notes = _repair_records()
    assert result["deleted_count"] == 1
    assert [n["deleted_event_id"] for n in notes] == [broken]
    assert result["logged_count"] == 1


def _prior_of(event_id: str) -> str:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT prior_hash FROM system_events WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def test_the_gap_stands_and_is_explained_by_its_note(three_events):
    """No surviving row is rewritten; verify accepts the gap only because a note
    names the removed row (council walk and Aria, 2026-09-28)."""
    before = _prior_of(three_events[2])
    _break_payload(three_events[1])
    clean_corrupted_events()
    assert _prior_of(three_events[2]) == before, "a surviving row was rewritten"
    chain = verify_chain()
    assert chain["ok"], chain


def test_without_its_note_the_gap_is_a_break(three_events):
    _break_payload(three_events[1])
    clean_corrupted_events()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM system_events WHERE event_type = 'LEDGER_CORRUPTION_REPAIRED'")
        conn.commit()
    finally:
        conn.close()
    assert not verify_chain()["ok"]


def test_one_note_excuses_one_link_and_a_second_claim_is_a_fork(three_events):
    _break_payload(three_events[1])
    clean_corrupted_events()
    removed_chain = _prior_of(three_events[2])
    forged = log_event("NOTE", "system", {"n": "forged"}, validate=False)
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE system_events SET prior_hash = ? WHERE event_id = ?", (removed_chain, forged)
        )
        conn.commit()
    finally:
        conn.close()
    assert not verify_chain()["ok"]


def test_nothing_is_removed_when_the_note_cannot_be_written(three_events, monkeypatch):
    """The removal and its note land together or not at all."""
    _break_payload(three_events[1])

    def refuse(*_a, **_k):
        raise RuntimeError("note could not be written")

    monkeypatch.setattr("divineos.core.ledger_verify._append_on", refuse)
    with pytest.raises(RuntimeError):
        clean_corrupted_events()
    conn = get_connection()
    try:
        still_there = conn.execute(
            "SELECT 1 FROM system_events WHERE event_id = ?", (three_events[1],)
        ).fetchone()
    finally:
        conn.close()
    assert still_there


def test_a_listed_break_excuses_the_link_never_the_row(three_events, tmp_path, monkeypatch):
    """Aria 2026-09-28: the exemption covers the prior link, not the row's own hash."""
    target = three_events[2]
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE system_events SET prior_hash = 'x', chain_hash = 'forged' WHERE event_id = ?",
            (target,),
        )
        conn.commit()
    finally:
        conn.close()
    known = tmp_path / "known_chain_breaks.md"
    known.write_text(f"- `{target}` -- a real concurrent-append race, see the note\n", "utf-8")
    monkeypatch.setattr(ledger, "KNOWN_CHAIN_BREAKS_FILE", known)
    chain = verify_chain()
    assert not chain["ok"]
    assert "chain_hash mismatch" in (chain["broken_reason"] or "")


def test_a_bare_id_with_no_evidence_is_not_an_exemption(three_events, tmp_path, monkeypatch):
    target = three_events[2]
    conn = get_connection()
    try:
        conn.execute("UPDATE system_events SET prior_hash = 'x' WHERE event_id = ?", (target,))
        conn.commit()
    finally:
        conn.close()
    known = tmp_path / "known_chain_breaks.md"
    known.write_text(f"- `{target}`\n", "utf-8")
    monkeypatch.setattr(ledger, "KNOWN_CHAIN_BREAKS_FILE", known)
    assert not verify_chain()["ok"]
