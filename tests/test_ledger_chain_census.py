"""The census sees every crossed hook, not only the first, and tells them from altered rows."""

import importlib.util
from pathlib import Path

from divineos.core._ledger_base import get_connection
from divineos.core.ledger import init_db, log_event

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("census", ROOT / "scripts" / "ledger_chain_census.py")
census_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census_mod)


def test_every_break_is_counted_and_an_altered_row_is_named(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    ids = [log_event("NOTE", "system", {"n": n}, validate=False) for n in range(6)]
    conn = get_connection()
    try:
        conn.execute("UPDATE system_events SET prior_hash = 'x' WHERE event_id = ?", (ids[2],))
        conn.execute("UPDATE system_events SET prior_hash = 'y' WHERE event_id = ?", (ids[4],))
        conn.commit()
    finally:
        conn.close()
    result = census_mod.census()
    # Each edited row's own backward link breaks; the row after it still hooks
    # onto the edited row's stored chain, so two edits are two breaks.
    assert [b["event_id"] for b in result["link_breaks"]] == [ids[2], ids[4]]
    assert {r["event_id"] for r in result["altered_rows"]} == {ids[2], ids[4]}
