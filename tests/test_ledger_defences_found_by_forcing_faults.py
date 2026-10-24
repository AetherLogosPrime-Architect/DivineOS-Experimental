"""Ledger defences that no test exercised, found by forcing faults (scripts/mutate_copy.py, 2026-10-20).

Each test below names the fault that left every earlier test green. All four sit on the
integrity path.
"""

import pytest

from divineos.core import ledger
from divineos.core._ledger_base import get_connection
from divineos.core.ledger import append_on, init_db, log_event, verify_chain
from divineos.core.ledger_verify import get_verified_events


@pytest.fixture
def three_events(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    return [log_event("NOTE", "system", {"n": n}, validate=False) for n in range(3)]


def _insert_unchained(event_id: str, timestamp: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO system_events "
            "(event_id, timestamp, event_type, actor, payload, content_hash, prior_hash, chain_hash) "
            "VALUES (?, ?, 'NOTE', 'system', '{}', 'forged', NULL, NULL)",
            (event_id, timestamp),
        )
        conn.commit()
    finally:
        conn.close()


def test_a_row_with_no_chain_written_after_chained_rows_is_a_forgery_not_legacy(three_events):
    """Fault: `seen_a_chained_row = True` -> False. Every unchained row would then count as
    pre-chain legacy, and a forged row with NULL chain columns would verify clean."""
    _insert_unchained("forged-after-the-chain", timestamp=9e9)
    result = verify_chain()
    assert result["ok"] is False
    assert result["unchained_after_chain_began"] == ["forged-after-the-chain"]
    assert "AFTER chaining began" in result["broken_reason"]


def test_a_payload_with_non_ascii_text_still_verifies_when_written_by_append_on(three_events):
    """Faults: ensure_ascii False -> True, and sort_keys True -> False, in append_on's content
    hash. ASCII payloads hash the same with either ensure_ascii, and a one-key payload hashes the
    same sorted or not, so only non-ASCII text with keys out of order shows them."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        # keys deliberately out of alphabetical order: the hash must sort them, as the verifier does
        event_id = append_on(conn, "NOTE", "system", {"zeta": 1, "text": "café — ✓ 日本"})
        conn.commit()
    finally:
        conn.close()
    verified, corrupted = get_verified_events(limit=50)
    assert corrupted == []
    assert event_id in {e["event_id"] for e in verified}


def test_opening_a_database_with_unchained_rows_fills_in_their_chain_automatically(
    tmp_path, monkeypatch
):
    """Fault: `if needs_backfill:` negated. The migration seam (Grok audit 2026-05-02): rows
    without a chain hash must be chained when the database is opened, not only when someone
    remembers to call the backfill by hand."""
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    _insert_unchained("older-row", timestamp=1.0)
    init_db()
    conn = get_connection()
    try:
        chain = conn.execute(
            "SELECT chain_hash FROM system_events WHERE event_id = 'older-row'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert chain, "the row opened without a chain hash was left without one"


def test_the_first_event_in_a_fresh_ledger_points_at_the_genesis_value(tmp_path, monkeypatch):
    """Fault: the genesis constant's length 64 -> 65. Within one run it stays self-consistent,
    so nothing noticed, but every ledger already on disk starts from 64 zeros and would stop
    verifying."""
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    first = log_event("NOTE", "system", {"n": 0}, validate=False)
    assert ledger._CHAIN_GENESIS == "0" * 64
    conn = get_connection()
    try:
        prior = conn.execute(
            "SELECT prior_hash FROM system_events WHERE event_id = ?", (first,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert prior == "0" * 64
