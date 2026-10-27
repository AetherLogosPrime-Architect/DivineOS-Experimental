"""The ledger's read side: get_events order, returned fields, and the supersession lookups.

Found 2026-10-20 by forcing faults into ledger.py (scripts/mutate_copy.py): none of these had a
test that could tell the right answer from a wrong one. search_events' ORDER is already pinned by
test_fable_finding_2_3_asc_limit.py (a first reading called it a gap only because that file's name
does not mention the ledger and was not handed to the tool), so it is not repeated here.
"""

import time

import pytest

from divineos.core.ledger import Ledger, get_events, get_ledger, init_db, log_event, search_events
from divineos.core.ledger_verify import verify_event_hash


@pytest.fixture
def three(tmp_path, monkeypatch):
    """Three events, oldest first, with distinct timestamps and distinct everything else."""
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    made = []
    for n, (etype, actor) in enumerate(
        [("NOTE_A", "alice"), ("NOTE_B", "bob"), ("NOTE_C", "cara")]
    ):
        before = time.time()
        eid = log_event(etype, actor, {"tag": "findme", "n": n}, validate=False)
        made.append(
            {
                "id": eid,
                "type": etype,
                "actor": actor,
                "n": n,
                "after": time.time(),
                "before": before,
            }
        )
        time.sleep(0.02)
    return made


def test_get_events_asc_is_oldest_first_and_desc_is_newest_first(three):
    ids = [m["id"] for m in three]
    assert [e["event_id"] for e in get_events(limit=10, order="asc") if e["event_id"] in ids] == ids
    assert [
        e["event_id"] for e in get_events(limit=10, order="desc") if e["event_id"] in ids
    ] == ids[::-1]


@pytest.mark.parametrize(
    "read",
    [
        lambda: get_events(limit=10),
        lambda: search_events("findme", limit=10),
    ],
    ids=["get_events", "search_events"],
)
def test_every_returned_row_carries_its_own_fields_not_a_neighbours(three, read):
    by_id = {e["event_id"]: e for e in read()}
    for m in three:
        row = by_id[m["id"]]
        assert row["event_type"] == m["type"]
        assert row["actor"] == m["actor"]
        assert row["payload"]["n"] == m["n"]
        assert m["before"] <= row["timestamp"] <= m["after"]
        assert verify_event_hash(row["event_id"], row["payload"], row["content_hash"])[0], (
            "the fingerprint returned does not belong to the payload returned"
        )


def test_supersession_lookups_filter_by_both_ids_and_return_the_payloads(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    ledger = Ledger()
    first = {"superseded_fact_id": "old-1", "superseding_fact_id": "new-1"}
    second = {"superseded_fact_id": "old-2", "superseding_fact_id": "new-2"}
    returned_id = ledger.store_event({**first, "event_id": "evt-first"})
    ledger.store_event(second)

    assert returned_id == "evt-first"
    assert len(ledger.query_supersession_events()) == 2
    only_first = ledger.query_supersession_events(superseded_fact_id="old-1")
    assert [p["superseding_fact_id"] for p in only_first] == ["new-1"]
    only_second = ledger.query_supersession_events(superseding_fact_id="new-2")
    assert [p["superseded_fact_id"] for p in only_second] == ["old-2"]
    assert (
        ledger.query_supersession_events(superseded_fact_id="old-1", superseding_fact_id="new-2")
        == []
    )


def test_stored_facts_come_back_filtered_by_type_and_key(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "ledger.db"))
    init_db()
    ledger = Ledger()
    ledger.store_fact({"id": "f1", "fact_type": "color", "fact_key": "sky"})
    ledger.store_fact({"id": "f2", "fact_type": "color", "fact_key": "grass"})
    ledger.store_fact({"id": "f3", "fact_type": "size", "fact_key": "sky"})
    assert {f["id"] for f in ledger.query_facts()} == {"f1", "f2", "f3"}
    assert {f["id"] for f in ledger.query_facts(fact_type="color")} == {"f1", "f2"}
    assert {f["id"] for f in ledger.query_facts(fact_key="sky")} == {"f1", "f3"}
    assert [f["id"] for f in ledger.query_facts(fact_type="color", fact_key="sky")] == ["f1"]


def test_the_shared_ledger_object_is_a_real_ledger_and_is_one_object():
    import divineos.core.ledger as ledger_module

    first = get_ledger()
    # Asked of the module as it is NOW, not of the class imported at the top of this file:
    # test_log_level_config reloads the module, which makes a new Ledger class, and the
    # name imported at collection time then points at the old one (2026-10-27: this test
    # failed two merge checks whenever that file ran first).
    assert isinstance(first, ledger_module.Ledger)  # two Nones would also be "the same object"
    assert get_ledger() is first
