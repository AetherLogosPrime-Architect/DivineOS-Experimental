"""More ledger defences that no test exercised, found by the full fault run on ledger.py (2026-10-20).

The run planted all 213 faults it could and 75 slipped past the fourteen ledger test files. The
ones here are the ones that matter: a wiped ledger, the main write path's fingerprint, the file
that excuses recorded chain breaks, and the defaults and wrappers the rest of the house leans on.
Readout and sorting: docs/drafts/the_full_ledger_fault_run_draft_2026-10-20.md.

Integrity tests: the wiped ledger, the fingerprint, the known-breaks file.
Contract tests (other code leans on them; they say nothing about trust): defaults and wrappers.
"""

import re
import sqlite3

import pytest

from divineos.core import ledger
from divineos.core._ledger_base import _get_db_path, get_connection
from divineos.core.ledger import (
    Ledger,
    get_events,
    get_recent_context,
    init_db,
    log_event,
    search_events,
    verify_chain,
)
from divineos.core.ledger_verify import get_verified_events


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()


def _sql(statement: str, params: tuple = ()) -> None:
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.execute(statement, params)
        conn.commit()
    finally:
        conn.close()


# --- a wiped ledger (integrity) ---------------------------------------------------------------


@pytest.mark.parametrize("how_many", [1, 3])
def test_a_ledger_emptied_while_its_anchor_remembers_events_is_reported(fresh, how_many):
    """The worst thing that can happen to a record is all of it going, and nothing tried it:
    faults on the "anchor remembers more than zero" test and on the result built under it all
    left every earlier test green. One event is the boundary: a ledger that held exactly one
    event and lost it is still a wipe."""
    for n in range(how_many):
        log_event("NOTE", "system", {"n": n}, validate=False)
    _sql("DELETE FROM system_events")
    result = verify_chain()
    assert result["ok"] is False
    assert result["total"] == 0
    assert result["broken_at"] is None
    assert f"anchor says {how_many} events but ledger is empty" in result["broken_reason"]


def test_an_empty_ledger_whose_anchor_says_zero_is_not_truncation(fresh):
    """Pins a boundary, not a story: this state (an anchor that says zero over an empty ledger) may
    not arise in normal use, but a fresh install must never be told it was wiped."""
    log_event("NOTE", "system", {"n": 0}, validate=False)
    _sql("DELETE FROM system_events")
    _sql("UPDATE ledger_head_anchor SET event_count = 0 WHERE row_id = 1")
    assert verify_chain()["ok"] is True


# --- the main write path's fingerprint (integrity) --------------------------------------------


def test_log_event_stores_unicode_unescaped_and_keys_sorted_and_still_verifies(fresh):
    """The verifier hashes with unescaped unicode and sorted keys, so a different choice on the
    write path only shows when the payload has non-ASCII text or keys out of alphabetical order.
    Same class as the append_on fault fixed earlier tonight."""
    event_id = log_event("NOTE", "system", {"zeta": 1, "text": "café ✓"}, validate=False)
    conn = get_connection()
    try:
        stored = conn.execute(
            "SELECT payload FROM system_events WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert "café ✓" in stored and "\\u00e9" not in stored
    assert stored.index('"text"') < stored.index('"zeta"')
    verified, corrupted = get_verified_events(limit=20)
    assert corrupted == [] and event_id in {e["event_id"] for e in verified}
    assert verify_chain()["ok"] is True


def test_events_are_validated_by_default(fresh):
    """A USER_INPUT with no content must be refused unless the caller opts out."""
    with pytest.raises(ValueError, match="Invalid event payload"):
        log_event("USER_INPUT", "user", {})
    log_event("USER_INPUT", "user", {}, validate=False)  # the opt-out still works


# --- the file that excuses recorded chain breaks (integrity) ----------------------------------


def test_the_known_chain_breaks_file_is_found_and_read():
    """A wrong path to this file would read as "no recorded breaks" with no error, and every
    investigated break would be reported as tampering again."""
    path = ledger.KNOWN_CHAIN_BREAKS_FILE
    assert path.is_file(), f"known chain breaks file not found at {path}"
    assert path.name == "known_chain_breaks.md" and path.parent.name == "docs"
    text = path.read_text(encoding="utf-8")
    assert ledger._known_chain_breaks() == set(
        re.findall(r"^-\s+`([0-9a-f-]{8,})`\s*\S.{7,}", text, re.MULTILINE)
    )
    assert ledger._known_chain_breaks(), "the one recorded entry is no longer read"


# --- reading back: defaults, filters, wrappers (contract) -------------------------------------


def test_get_events_defaults_return_a_hundred_from_the_start(fresh):
    ids = [log_event("NOTE", "system", {"n": n}, validate=False) for n in range(105)]
    got = [e["event_id"] for e in get_events()]
    assert got == ids[:100]
    assert [e["event_id"] for e in Ledger().get_events()] == ids[:100]


def test_search_events_defaults_return_fifty(fresh):
    for n in range(55):
        log_event("NOTE", "system", {"tag": "needle", "n": n}, validate=False)
    assert len(search_events("needle")) == 50


def test_a_list_of_event_types_filters_to_those_types(fresh):
    for etype in ("NOTE_A", "NOTE_B", "NOTE_C"):
        log_event(etype, "system", {}, validate=False)
    got = {e["event_type"] for e in get_events(event_type=["NOTE_A", "NOTE_C"])}
    assert got == {"NOTE_A", "NOTE_C"}


def test_the_ledger_object_passes_its_arguments_through_and_returns_the_results(fresh):
    led = Ledger()
    first = led.log_event("NOTE_A", "alice", {"n": 0}, validate=False)
    led.log_event("NOTE_A", "bob", {"n": 1}, validate=False)
    third = led.log_event("NOTE_A", "alice", {"n": 2}, validate=False)
    assert isinstance(first, str) and first, "log_event through the object returned no id"
    got = led.get_events(limit=5, offset=1, event_type="NOTE_A", actor="alice")
    assert [e["event_id"] for e in got] == [third], "arguments were not passed through"
    with pytest.raises(ValueError):
        led.log_event("USER_INPUT", "user", {})  # validation is on by default here too
    assert led.store_fact({"id": "fact-9"}) == "fact-9"


def test_recent_context_skips_bookkeeping_by_default_and_keeps_chronological_order(fresh):
    kept = [log_event("NOTE", "system", {"n": n}, validate=False) for n in range(3)]
    noise = log_event("TOOL_CALL", "system", {"tool": "x"}, validate=False)
    newest = log_event("NOTE", "system", {"n": 3}, validate=False)
    default = get_recent_context(n=10)
    assert [e["event_id"] for e in default] == kept + [newest]
    everything = get_recent_context(n=10, meaningful_only=False)
    assert [e["event_id"] for e in everything] == kept + [noise, newest]
    assert [e["event_id"] for e in get_recent_context(n=2)] == [kept[2], newest]
    row = default[0]
    assert row["actor"] == "system" and row["event_type"] == "NOTE" and row["payload"]["n"] == 0
    assert isinstance(row["timestamp"], float)


def test_recent_context_returns_twenty_by_default(fresh):
    for n in range(25):
        log_event("NOTE", "system", {"n": n}, validate=False)
    assert len(get_recent_context()) == 20
