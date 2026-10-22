"""The note-reading half of verify_chain, tested with crafted rows.

An end-to-end forgery test cannot see this guard: a later check catches the
forgery first, so if this bookkeeping were weakened nothing would show
(Aletheia 2026-10-21). These call the function directly.
"""

import json

from divineos.core.ledger import _removal_notes_from_rows


def _row(event_type, payload, chain_hash="c-own"):
    return ("e", "t", event_type, "a", json.dumps(payload), "h", "p", chain_hash)


def test_a_repair_note_names_the_removed_hash_once():
    rows = [_row("LEDGER_CORRUPTION_REPAIRED", {"deleted_chain_hash": "gone"})]
    assert _removal_notes_from_rows(rows) == {"gone": 1}


def test_a_compaction_note_names_every_hash_in_its_list():
    rows = [_row("LEDGER_COMPACTION", {"gap_tail_chain_hashes": ["g1", "g2"]})]
    assert _removal_notes_from_rows(rows) == {"g1": 1, "g2": 1}


def test_a_name_still_carried_by_a_surviving_row_is_not_a_gap():
    rows = [
        _row("LEDGER_CORRUPTION_REPAIRED", {"deleted_chain_hash": "alive"}),
        _row("OTHER", {}, chain_hash="alive"),
    ]
    assert _removal_notes_from_rows(rows) == {}


def test_two_notes_naming_the_same_hash_count_twice():
    rows = [
        _row("LEDGER_CORRUPTION_REPAIRED", {"deleted_chain_hash": "gone"}, "c1"),
        _row("LEDGER_COMPACTION", {"gap_tail_chain_hashes": ["gone"]}, "c2"),
    ]
    assert _removal_notes_from_rows(rows) == {"gone": 2}


def test_other_event_types_are_never_read_as_notes():
    rows = [_row("USER_INPUT", {"deleted_chain_hash": "gone", "gap_tail_chain_hashes": ["gone"]})]
    assert _removal_notes_from_rows(rows) == {}


def test_a_ledger_lookalike_type_is_not_a_note():
    # Aether 2026-10-21: widening the check to any LEDGER_* type passed every other
    # test here, because the one "other type" row used USER_INPUT.
    rows = [
        _row("LEDGER_SOMETHING_ELSE", {"deleted_chain_hash": "gone"}, "c1"),
        _row("LEDGER_SOMETHING_ELSE", {"gap_tail_chain_hashes": ["gone"]}, "c2"),
    ]
    assert _removal_notes_from_rows(rows) == {}


def test_a_note_with_a_broken_payload_excuses_nothing_and_does_not_crash():
    broken = ("e", "t", "LEDGER_CORRUPTION_REPAIRED", "a", "{not json", "h", "p", "c")
    assert _removal_notes_from_rows([broken]) == {}


def test_a_payload_of_the_wrong_shape_excuses_nothing():
    rows = [
        _row("LEDGER_COMPACTION", {"gap_tail_chain_hashes": 5}, "c1"),
        ("e", "t", "LEDGER_CORRUPTION_REPAIRED", "a", "[1]", "h", "p", "c2"),
    ]
    assert _removal_notes_from_rows(rows) == {}


def test_empty_and_non_string_names_are_ignored():
    rows = [
        _row("LEDGER_COMPACTION", {"gap_tail_chain_hashes": ["", None, 7, "real"]}),
        _row("LEDGER_CORRUPTION_REPAIRED", {"deleted_chain_hash": None}, "c2"),
    ]
    assert _removal_notes_from_rows(rows) == {"real": 1}
