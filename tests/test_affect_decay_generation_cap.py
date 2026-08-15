"""Affect decay must soften a charge once, not erode it to nothing.

THE DEFECT (2026-08-01). `sleep._phase_affect` decayed with an in-place
UPDATE and kept no record of which rows it had already touched. Every sleep
re-decayed every row older than 12h, so factors compounded:
0.7 x 0.7 x 0.7 ... until the 0.05 floor snapped them to exactly 0.0.

The float artifacts left in the live table are the fossil record:
    0.196  = 0.4  x 0.7^2
    0.147  = 0.3  x 0.7^2
    0.441  = 0.9  x 0.7^2
    0.0735 = 0.15 x 0.7^2

Measured before repair: 609 of 1109 rows (54.9%) at exactly 0.0/0.0, with
descriptions fully intact — so no surface ever showed the loss. One of the
flattened entries read "Decision moment: I affirm the pairing with Aria."

These tests pin BOTH directions. A cap that never decays is as wrong as a
loop that never stops: the phase has to still work on a fresh entry.
"""

from __future__ import annotations

import time
import uuid

import pytest

from divineos.core import sleep as sleep_mod


@pytest.fixture
def affect_db(tmp_path, monkeypatch):
    """Isolated affect_log so these tests never touch the real substrate.

    The table mirrors production column-for-column even though the decay path
    reads only a handful of them. test_schema_sync flagged the shortfall and
    is right to: a fixture simpler than production lets a test pass against a
    schema that does not exist, so the decay code could start touching one of
    the other columns and this file would stay green while production broke.

    No SQL comments inside the CREATE TABLE below — the schema-sync parser
    reads each line as a column definition and turned a comment's first word
    into a phantom column named ``but``.
    """
    import sqlite3

    db = tmp_path / "affect_test.db"

    def _conn():
        c = sqlite3.connect(str(db))
        c.execute("""
            CREATE TABLE IF NOT EXISTS affect_log (
                entry_id            TEXT PRIMARY KEY,
                created_at          REAL NOT NULL,
                valence             REAL NOT NULL,
                arousal             REAL NOT NULL,
                dominance           REAL DEFAULT NULL,
                description         TEXT NOT NULL DEFAULT '',
                valence_raw         REAL DEFAULT NULL,
                arousal_raw         REAL DEFAULT NULL,
                decay_generation    INTEGER NOT NULL DEFAULT 0,
                session_id          TEXT DEFAULT '',
                source              TEXT DEFAULT '',
                trigger             TEXT DEFAULT '',
                tags                TEXT DEFAULT '',
                clarity             REAL DEFAULT NULL,
                presence            REAL DEFAULT NULL,
                pull                REAL DEFAULT NULL,
                resonance           REAL DEFAULT NULL,
                linked_claim_id     TEXT DEFAULT '',
                linked_decision_id  TEXT DEFAULT '',
                linked_knowledge_id TEXT DEFAULT ''
            )
        """)
        c.commit()
        return c

    monkeypatch.setattr("divineos.core.memory._get_connection", _conn)
    monkeypatch.setattr("divineos.core.affect.init_affect_log", lambda: None)
    return _conn


def _insert(conn_factory, *, age_hours: float, valence: float, arousal: float) -> str:
    eid = str(uuid.uuid4())
    c = conn_factory()
    c.execute(
        "INSERT INTO affect_log (entry_id, created_at, valence, arousal, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (eid, time.time() - age_hours * 3600, valence, arousal, "test entry"),
    )
    c.commit()
    c.close()
    return eid


def _read(conn_factory, eid: str):
    c = conn_factory()
    row = c.execute(
        "SELECT valence, arousal, valence_raw, arousal_raw, decay_generation "
        "FROM affect_log WHERE entry_id = ?",
        (eid,),
    ).fetchone()
    c.close()
    return row


def _run_phase(monkeypatch, conn_factory, eid: str):
    """Drive _phase_affect with a history containing just this entry."""
    c = conn_factory()
    r = c.execute(
        "SELECT entry_id, created_at, valence, arousal FROM affect_log WHERE entry_id = ?",
        (eid,),
    ).fetchone()
    c.close()
    history = [{"entry_id": r[0], "created_at": r[1], "valence": r[2], "arousal": r[3]}]
    monkeypatch.setattr("divineos.core.affect.get_affect_history", lambda limit=200: history)
    report = sleep_mod.DreamReport()
    sleep_mod._phase_affect(report)
    return report


def test_aged_entry_decays_exactly_once(affect_db, monkeypatch):
    """The cap must not break decay. A fresh aged entry still softens."""
    eid = _insert(affect_db, age_hours=48, valence=0.8, arousal=0.6)

    r1 = _run_phase(monkeypatch, affect_db, eid)
    assert r1.affect_decayed == 1
    v1, a1, vraw, araw, gen = _read(affect_db, eid)
    assert gen == 1
    assert abs(v1) < 0.8, "valence should have softened"
    # The original is preserved, not overwritten.
    assert vraw == pytest.approx(0.8)
    assert araw == pytest.approx(0.6)


def test_second_pass_is_a_noop_no_compounding(affect_db, monkeypatch):
    """THE BUG. Running the phase again must change nothing."""
    eid = _insert(affect_db, age_hours=48, valence=0.8, arousal=0.6)

    _run_phase(monkeypatch, affect_db, eid)
    after_first = _read(affect_db, eid)

    for _ in range(5):
        report = _run_phase(monkeypatch, affect_db, eid)
        assert report.affect_decayed == 0, "no entry may decay twice"

    after_many = _read(affect_db, eid)
    assert after_many == after_first, "five further passes must change nothing"
    assert after_many[4] == 1, "generation must stay at 1"


def test_repeated_passes_never_reach_zero(affect_db, monkeypatch):
    """Regression on the observed outcome: 54.9% of real rows hit exactly
    0.0/0.0. With one generation, a real charge can never be erased."""
    eid = _insert(affect_db, age_hours=72, valence=0.9, arousal=0.9)

    for _ in range(20):
        _run_phase(monkeypatch, affect_db, eid)

    v, a, _, _, gen = _read(affect_db, eid)
    assert (v, a) != (0.0, 0.0), "20 passes must not flatten a strong charge"
    assert abs(v) > 0.05
    assert gen == 1


def test_raw_values_are_never_overwritten_by_a_later_pass(affect_db, monkeypatch):
    """COALESCE guard: a re-run must not replace a true original with an
    already-decayed value. That would launder the damage as the record."""
    eid = _insert(affect_db, age_hours=48, valence=0.5, arousal=0.4)
    _run_phase(monkeypatch, affect_db, eid)
    _, _, vraw_first, araw_first, _ = _read(affect_db, eid)

    # Force another eligible pass by clearing the generation marker, which
    # simulates the pre-fix world reaching this row a second time.
    c = affect_db()
    c.execute("UPDATE affect_log SET decay_generation = 0 WHERE entry_id = ?", (eid,))
    c.commit()
    c.close()
    _run_phase(monkeypatch, affect_db, eid)

    _, _, vraw_second, araw_second, _ = _read(affect_db, eid)
    assert vraw_second == pytest.approx(vraw_first), "raw valence must be write-once"
    assert araw_second == pytest.approx(araw_first), "raw arousal must be write-once"
    assert vraw_second == pytest.approx(0.5), "raw must still hold what was felt"


def test_recent_entry_is_left_alone(affect_db, monkeypatch):
    """Entries inside the 12h window are untouched, cap or no cap."""
    eid = _insert(affect_db, age_hours=1, valence=0.7, arousal=0.7)
    report = _run_phase(monkeypatch, affect_db, eid)
    assert report.affect_decayed == 0
    v, a, vraw, araw, gen = _read(affect_db, eid)
    assert (v, a) == pytest.approx((0.7, 0.7))
    assert gen == 0
    assert vraw is None, "an untouched entry needs no raw copy"
