"""The compressor leaves its gaps (Aria, 2026-09-29; walk-d1d17f7e2883).

No surviving row is rewritten; each gap is named by a chained LEDGER_COMPACTION
note. These supersede the 2026-07-16 relink design, whose tests in
test_ledger_compressor_chain_repair.py assert the old behaviour and are
brought to Dad as a removal case (his rule 2026-09-28) rather than removed.
"""

from __future__ import annotations

import json
import sqlite3
import time

import pytest


@pytest.fixture
def ledger_at(tmp_path, monkeypatch):
    db_path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DIVINEOS_LEDGER_PATH", str(db_path))
    from divineos.core import _ledger_base
    from divineos.core import ledger as ledger_mod

    monkeypatch.setattr(_ledger_base, "_get_db_path", lambda: db_path)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: db_path)
    ledger_mod.init_db()
    return db_path


def _log(n, event_type):
    from divineos.core.ledger import log_event

    return [
        log_event(
            event_type, actor="test", payload={"content": f"{event_type}-{i}"}, validate=False
        )
        for i in range(n)
    ]


def _age(db_path, event_type, days=60):
    """Make a type old enough to compress, re-chaining so the ledger starts healthy."""
    from divineos.core.ledger import backfill_chain_hashes

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "UPDATE system_events SET timestamp = ? WHERE event_type = ?",
        (time.time() - days * 86400, event_type),
    )
    conn.execute("UPDATE system_events SET prior_hash = NULL, chain_hash = NULL")
    conn.execute("DELETE FROM ledger_head_anchor WHERE row_id = 1")
    conn.commit()
    conn.close()
    backfill_chain_hashes()


def _survivors(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        return {
            eid: (prior, chain)
            for eid, prior, chain in conn.execute(
                "SELECT event_id, prior_hash, chain_hash FROM system_events"
            )
        }
    finally:
        conn.close()


def _notes(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        return [
            (json.loads(p), prior, chain)
            for p, prior, chain in conn.execute(
                "SELECT payload, prior_hash, chain_hash FROM system_events "
                "WHERE event_type = 'LEDGER_COMPACTION' ORDER BY rowid"
            )
        ]
    finally:
        conn.close()


def _two_runs(db_path):
    """kept x3, noise x3, kept x2, noise x2, kept x2: two gaps with survivors after."""
    _log(3, "USER_INPUT")
    _log(3, "TOOL_CALL")
    _log(2, "USER_INPUT")
    _log(2, "TOOL_CALL")
    _log(2, "USER_INPUT")
    _age(db_path, "TOOL_CALL")


def test_no_surviving_row_is_rewritten(ledger_at):
    # Sagan: proven byte for byte, not read off the code.
    _two_runs(ledger_at)
    before = _survivors(ledger_at)
    from divineos.core.ledger_compressor import compress_ledger

    result = compress_ledger(retention_days=30)
    after = _survivors(ledger_at)
    assert result["compressed"] == 5
    for eid, links in after.items():
        if eid in before:
            assert links == before[eid], f"surviving row {eid} was rewritten"


def test_each_gap_is_named_once_by_a_chained_note(ledger_at):
    _two_runs(ledger_at)
    before = _survivors(ledger_at)
    from divineos.core.ledger_compressor import compress_ledger

    result = compress_ledger(retention_days=30)
    assert result["gap_count"] == 2
    ((payload, prior, chain),) = _notes(ledger_at)
    tails = payload["gap_tail_chain_hashes"]
    assert len(tails) == 2 and prior and chain  # the note is itself chained (Turing)
    after = _survivors(ledger_at)
    # Each tail names a row that is now gone ...
    assert all(t not in {c for _, c in after.values()} for t in tails)
    # ... and is exactly what a surviving row now points at.
    assert set(tails) <= {p for eid, (p, _) in after.items() if eid in before}


def test_a_crossing_before_compression_is_still_reported_after(ledger_at):
    # Popper: the old relink silently mended unrelated crossings after a gap.
    _two_runs(ledger_at)
    conn = sqlite3.connect(str(ledger_at))
    last = conn.execute("SELECT rowid FROM system_events ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    conn.execute("UPDATE system_events SET prior_hash = ? WHERE rowid = ?", ("f" * 64, last))
    conn.commit()
    conn.close()
    from divineos.core.ledger import verify_chain
    from divineos.core.ledger_compressor import compress_ledger

    assert verify_chain()["ok"] is False
    compress_ledger(retention_days=30)
    assert verify_chain()["ok"] is False


def test_verify_reads_the_gaps_as_explained(ledger_at):
    # Needs Aether's verify_chain to accept LEDGER_COMPACTION gap tails
    # (agreed 2026-09-29, his to write on #565). Fails until it lands.
    _two_runs(ledger_at)
    from divineos.core.ledger import verify_chain
    from divineos.core.ledger_compressor import compress_ledger

    compress_ledger(retention_days=30)
    assert verify_chain()["ok"] is True, verify_chain()


def test_many_gaps_split_across_chained_notes(ledger_at, monkeypatch):
    # Shannon: alternating noise and kept rows, one gap per removed row.
    from divineos.core import ledger_compressor as lc

    monkeypatch.setattr(lc, "MAX_TAILS_PER_NOTE", 2)
    for _ in range(5):
        _log(1, "USER_INPUT")
        _log(1, "TOOL_CALL")
    _log(1, "USER_INPUT")
    _age(ledger_at, "TOOL_CALL")
    result = lc.compress_ledger(retention_days=30)
    notes = _notes(ledger_at)
    assert result["gap_count"] == 5 and len(notes) == 3
    assert sum(len(p["gap_tail_chain_hashes"]) for p, _, _ in notes) == 5
    assert all(p.get("continues") == result["summary_event_id"] for p, _, _ in notes[1:])


def test_no_meaningful_kind_of_event_counts_as_noise():
    # Dillahunty: the gap mechanism must never widen into dropping what matters.
    from divineos.core.ledger_compressor import _COMPRESSIBLE_TYPES

    meaningful = {"USER_INPUT", "SESSION_END", "LEDGER_COMPACTION", "LEDGER_CORRUPTION_REPAIRED"}
    assert not (meaningful & set(_COMPRESSIBLE_TYPES))
    assert not any(t.endswith("_FIRED") for t in _COMPRESSIBLE_TYPES)
