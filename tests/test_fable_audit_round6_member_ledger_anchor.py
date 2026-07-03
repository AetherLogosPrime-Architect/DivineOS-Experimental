"""Fable audit round 6 finding #2 (2026-07-02) — member ledger tail truncation.

Reproduces Fable's exact case: append 8 events, delete the 3 newest
directly, call verify_chain. Before the fix: returns (True, 'chain
valid: 5 events verified'). After the fix: returns (False, ...) naming
the tail-truncation via the head anchor mismatch.

Same-class fix as round 1 on the main ledger — grep siblings and
propagate the protection, per Aria's addendum meta-observation and the
audit's own thread-to-rounds-1-through-5.
"""

from __future__ import annotations

from divineos.core.family import family_member_ledger as fml


def _get_conn(member_slug):
    return fml._get_connection(member_slug)


def _append_n(member_slug, n):
    """Append n events, return their event_ids in order."""
    ids = []
    for i in range(n):
        result = fml.append_event(
            member_slug,
            event_type="TEST_EVENT",
            actor="test",
            payload={"i": i},
        )
        ids.append(result["event_id"])
    return ids


def _tail_delete(member_slug, ids_to_delete):
    """Delete specified event_ids from the ledger table WITHOUT updating
    the anchor. This is the attacker's move: tail-truncate quietly."""
    conn = _get_conn(member_slug)
    try:
        for eid in ids_to_delete:
            conn.execute("DELETE FROM member_events WHERE event_id = ?", (eid,))
        conn.commit()
    finally:
        conn.close()


def test_verify_chain_catches_tail_truncation_the_fable_reproduction(tmp_path, monkeypatch):
    """Fable's exact reproduction: 8 events, delete 3 newest, verify_chain
    must return False (was returning True before the anchor fix)."""
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))
    ids = _append_n("aether", 8)

    ok, msg = fml.verify_chain("aether")
    assert ok, f"pristine ledger should verify clean, got: {msg}"
    assert "8 events verified" in msg

    # Delete the 3 newest directly from the events table (skipping the
    # anchor update). This is the attacker's move.
    _tail_delete("aether", ids[-3:])

    ok, msg = fml.verify_chain("aether")
    assert not ok, (
        "verify_chain must catch tail truncation via the head anchor — "
        "Fable round 6 finding #2 regression. Returned CLEAN on a "
        f"truncated ledger. Message: {msg}"
    )
    assert "tail truncation" in msg or "Fable round 6" in msg, (
        f"diagnostic should name the failure class, got: {msg}"
    )


def test_verify_chain_still_passes_untampered_ledger(tmp_path, monkeypatch):
    """Regression: clean chains still verify true."""
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))

    _append_n("aether", 5)
    ok, msg = fml.verify_chain("aether")
    assert ok, f"clean ledger should verify true, got: {msg}"
    assert "5 events verified" in msg


def test_verify_chain_catches_middle_deletion_still(tmp_path, monkeypatch):
    """Regression: middle-deletion was already caught before the anchor
    fix. Confirm the new anchor logic didn't break that.
    """
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))

    ids = _append_n("aether", 6)
    _tail_delete("aether", [ids[2]])  # delete a middle event
    ok, msg = fml.verify_chain("aether")
    assert not ok, "middle deletion must still be caught"


def test_verify_chain_catches_anchor_only_tampering(tmp_path, monkeypatch):
    """Adversary tampers with the anchor row directly to hide truncation.

    Even if the attacker rewrites the anchor to match a truncated tail,
    the fix's per-event content_hash chain still catches the mismatch —
    OR the anchor is the only thing lying and the chain walk agrees with
    the tail. This test covers the case where the attacker deletes tail
    events AND updates the anchor to point at the new tail: the anchor
    now matches the truncated tail, but the event_count in the anchor
    still contradicts the row count if the attacker forgets to update it.
    """
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))

    ids = _append_n("aether", 8)

    # Sophisticated attack: delete 3 events AND rewrite the anchor to
    # point at the new tail. But leave event_count stale (attacker missed
    # a field). The count mismatch alone should catch this.
    conn = _get_conn("aether")
    try:
        for eid in ids[-3:]:
            conn.execute("DELETE FROM member_events WHERE event_id = ?", (eid,))
        # Rewrite anchor to match new tail (event index 4, which is ids[4])
        new_tail = conn.execute(
            "SELECT content_hash, event_id FROM member_events "
            "ORDER BY timestamp ASC, rowid ASC LIMIT 1 OFFSET 4"
        ).fetchone()
        # Attacker sets event_count to old value (8) — the mismatch.
        conn.execute(
            "UPDATE member_head_anchor SET content_hash = ?, latest_event_id = ? WHERE row_id = 1",
            (new_tail["content_hash"], new_tail["event_id"]),
        )
        conn.commit()
    finally:
        conn.close()

    ok, msg = fml.verify_chain("aether")
    assert not ok, (
        "attacker rewrote anchor but left event_count stale — count "
        "mismatch must be caught. Message: %s" % msg
    )


def test_empty_ledger_verifies_clean(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))

    fml.init_ledger("aether")
    ok, msg = fml.verify_chain("aether")
    assert ok
    assert "empty ledger" in msg


def test_empty_ledger_with_lying_anchor_caught(tmp_path, monkeypatch):
    """If the ledger is empty but the anchor claims events existed, that
    IS tail-truncation evidence — an attacker wiped everything but forgot
    the anchor."""
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))

    _append_n("aether", 3)
    # Wipe the events but leave the anchor
    conn = _get_conn("aether")
    try:
        conn.execute("DELETE FROM member_events")
        conn.commit()
    finally:
        conn.close()
    ok, msg = fml.verify_chain("aether")
    assert not ok, f"anchor-says-N events but empty ledger must fail: {msg}"
    assert "tail truncation" in msg
