"""Each of verify_chain's three head-anchor checks must fire on its own.

Found 2026-10-20 by forcing faults into ledger.py (scripts/mutate_copy.py): flipping
`ok=False` to `ok=True` in the third check (the anchor's latest_event_id differs
from the ledger's) left every test green. The existing tail-truncation test chops
real events, which trips the FIRST check (chain_hash) and returns before the other
two are reached, so those two were never exercised by anything.

Here the stored anchor is altered one field at a time, leaving the events alone, so
only one check can be the one that fires. Each test also asserts WHICH reason came
back: any failing result would otherwise satisfy `ok is False` and a check could be
swapped for another unnoticed.
"""

from __future__ import annotations

import sqlite3

from divineos.core._ledger_base import _get_db_path
from divineos.core.ledger import log_event, verify_chain


def _seed(n: int = 4) -> None:
    for i in range(n):
        log_event("TEST_EVENT", "test", {"seq": i})


def _anchor() -> tuple:
    conn = sqlite3.connect(_get_db_path())
    try:
        return conn.execute(
            "SELECT chain_hash, event_count, latest_event_id FROM ledger_head_anchor WHERE row_id = 1"
        ).fetchone()
    finally:
        conn.close()


def _set_anchor(column: str, value: object) -> None:
    assert column in {"chain_hash", "event_count", "latest_event_id"}
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.execute(f"UPDATE ledger_head_anchor SET {column} = ? WHERE row_id = 1", (value,))
        conn.commit()
    finally:
        conn.close()


def test_an_untouched_ledger_and_its_anchor_agree():
    _seed()
    assert _anchor() is not None
    assert verify_chain()["ok"] is True


def test_a_wrong_anchor_chain_hash_alone_is_caught_with_its_own_reason():
    _seed()
    _set_anchor("chain_hash", "f" * 64)
    result = verify_chain()
    assert result["ok"] is False
    assert "chain_hash mismatch" in result["broken_reason"]


def test_a_wrong_anchor_event_count_alone_is_caught_with_its_own_reason():
    _seed()
    _set_anchor("event_count", _anchor()[1] + 1)
    result = verify_chain()
    assert result["ok"] is False
    assert "event_count mismatch" in result["broken_reason"]


def test_a_wrong_anchor_latest_event_id_alone_is_caught_with_its_own_reason():
    _seed()
    _set_anchor("latest_event_id", "not-the-real-tip")
    result = verify_chain()
    assert result["ok"] is False
    assert "latest_event_id mismatch" in result["broken_reason"]
