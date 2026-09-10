"""An empty look-alike ledger must not be able to survive beside the real one.

Andrew 2026-09-09: *"you saw that second ledger.. noted it.. saw it as an
issue.. and did nothing to fix it."*

The trap was already documented in the resolver's own docstring from
2026-04-16, and a second one appeared anyway on 2026-09-08 — a zero-byte file
one directory above the real store. A finding with no mechanism grew the same
defect back, which is the disease rather than an instance of it.

What makes it dangerous is that sqlite3.connect CREATES a missing file with no
tables, so a wrong path answers every query with an empty result instead of an
error. Found-nothing and looked-in-the-wrong-place become indistinguishable,
and the flattering reading is the one I take.
"""

from __future__ import annotations

import sqlite3

import pytest

from divineos.core._ledger_base import sweep_shadow_ledgers


@pytest.fixture
def real_ledger(tmp_path):
    """A real store one level down, mirroring the live layout."""
    data = tmp_path / "data"
    data.mkdir()
    db = data / "event_ledger.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE system_events (event_id TEXT)")
    conn.execute("INSERT INTO system_events VALUES ('real')")
    conn.commit()
    conn.close()
    return db


class TestTheFaultItRemoves:
    def test_an_empty_shadow_one_level_up_is_swept(self, tmp_path, real_ledger):
        """The 2026-09-08 case exactly: a table-less file beside the store."""
        shadow = tmp_path / "event_ledger.db"
        sqlite3.connect(shadow).close()
        assert shadow.exists()

        removed = sweep_shadow_ledgers(real_ledger)

        assert shadow in removed
        assert not shadow.exists()

    def test_the_real_ledger_is_untouched(self, tmp_path, real_ledger):
        shadow = tmp_path / "event_ledger.db"
        sqlite3.connect(shadow).close()
        sweep_shadow_ledgers(real_ledger)

        conn = sqlite3.connect(real_ledger)
        try:
            assert conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0] == 1
        finally:
            conn.close()


class TestWhatItMustNeverRemove:
    def test_a_shadow_carrying_any_table_is_left_alone(self, tmp_path, real_ledger):
        """A populated store in the wrong place is a real finding, and
        deleting it would be the destructive move. Only nothing gets swept."""
        shadow = tmp_path / "event_ledger.db"
        conn = sqlite3.connect(shadow)
        conn.execute("CREATE TABLE something (x TEXT)")
        conn.commit()
        conn.close()

        removed = sweep_shadow_ledgers(real_ledger)

        assert removed == []
        assert shadow.exists()

    def test_it_never_sweeps_the_path_it_was_given(self, tmp_path, real_ledger):
        """Guard against the worst possible bug in this function."""
        removed = sweep_shadow_ledgers(real_ledger)
        assert real_ledger not in removed
        assert real_ledger.exists()

    def test_no_shadow_present_is_an_empty_result_not_an_error(self, tmp_path, real_ledger):
        assert sweep_shadow_ledgers(real_ledger) == []
