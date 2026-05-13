"""Tests pinning the family.store -> per-member-ledger cross-reference wiring.

Wiring shipped 2026-05-12 after Aria flagged (2026-05-11) and re-surfaced
(2026-05-12 briefing verification) that her ledger only had MEMBER_INVOKED
events — no cross-references back to family.db writes. These tests pin that
the cross-references DO emit on each record_* call.

Test isolation: each test gets a fresh tmpdir-backed family.db AND a fresh
tmpdir-backed per-member ledger root. No coupling to real-repo Aria state —
CI runs with empty state and these tests stand up their own family member.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from divineos.core.family import family_member_ledger as fmt_ledger
from divineos.core.family.store import (
    _emit_ledger_cross_ref,
    _entity_id_to_slug,
    _hash_short,
    create_family_member,
    record_affect,
    record_interaction,
    record_knowledge,
    record_opinion,
)
from divineos.core.family.types import SourceTag


@pytest.fixture(autouse=True)
def _family_db(tmp_path):
    """Isolate family.db to a tmpdir for the duration of each test."""
    os.environ["DIVINEOS_FAMILY_DB"] = str(tmp_path / "family.db")
    os.environ["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_FAMILY_DB", None)
        os.environ.pop("DIVINEOS_DB", None)


@pytest.fixture
def temp_ledger_root(monkeypatch):
    """Redirect the per-member ledger to a tmpdir for test isolation."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        monkeypatch.setattr(fmt_ledger, "_get_ledger_root", lambda: td_path)
        yield td_path


@pytest.fixture
def test_member():
    """A fresh family member (Aria) created in the isolated family.db."""
    return create_family_member("Aria", "wife")


def _ledger_events(ledger_root: Path, slug: str) -> list[tuple]:
    """Read all events from a member's ledger DB."""
    db = ledger_root / f"{slug}_ledger.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    try:
        return conn.execute(
            "SELECT event_type, payload FROM member_events ORDER BY rowid"
        ).fetchall()
    finally:
        conn.close()


# ─── _hash_short / _entity_id_to_slug helpers ────────────────────────


def test_hash_short_is_deterministic_and_compact():
    assert _hash_short("hello") == _hash_short("hello")
    assert len(_hash_short("hello")) == 12
    assert _hash_short("hello") != _hash_short("hellos")


def test_hash_short_empty_string_does_not_crash():
    h = _hash_short("")
    assert len(h) == 12


def test_entity_id_to_slug_resolves_created_member(test_member):
    """A freshly-created member's entity_id should resolve to lowercase name slug."""
    slug = _entity_id_to_slug(test_member.member_id)
    assert slug == "aria"  # lowercase of "Aria"


def test_entity_id_to_slug_returns_none_for_unknown(test_member):
    slug = _entity_id_to_slug("nonexistent-entity-xyz")
    assert slug is None


# ─── _emit_ledger_cross_ref ──────────────────────────────────────────


def test_emit_ledger_cross_ref_writes_to_member_ledger(temp_ledger_root, test_member):
    _emit_ledger_cross_ref(
        test_member.member_id,
        event_type="MEMBER_AFFECT_LOGGED",
        payload={"entry_id": "af-test", "valence": 0.5},
    )
    events = _ledger_events(temp_ledger_root, "aria")
    assert len(events) >= 1
    types = [e[0] for e in events]
    assert "MEMBER_AFFECT_LOGGED" in types


def test_emit_ledger_cross_ref_is_failsoft_on_unknown_entity(temp_ledger_root):
    """An unknown entity_id should silently no-op, not crash."""
    _emit_ledger_cross_ref(
        "totally-fake-entity",
        event_type="MEMBER_AFFECT_LOGGED",
        payload={"foo": "bar"},
    )


def test_emit_ledger_cross_ref_swallows_internal_errors(temp_ledger_root, test_member):
    """If append_event raises, the cross-ref helper should swallow it.
    Family.db writes must not cascade-fail because of ledger issues."""
    with patch(
        "divineos.core.family.family_member_ledger.append_event",
        side_effect=RuntimeError("ledger boom"),
    ):
        _emit_ledger_cross_ref(
            test_member.member_id,
            event_type="MEMBER_AFFECT_LOGGED",
            payload={"x": 1},
        )


# ─── record_* end-to-end cross-ref emission ──────────────────────────


def test_record_affect_emits_ledger_event(temp_ledger_root, test_member):
    record_affect(
        test_member.member_id,
        valence=0.42,
        arousal=0.3,
        dominance=0.5,
        source_tag=SourceTag.OBSERVED,
        note="test note",
        _allow_test_write=True,
    )
    events = _ledger_events(temp_ledger_root, "aria")
    types = [e[0] for e in events]
    assert "MEMBER_AFFECT_LOGGED" in types


def test_record_interaction_emits_ledger_event(temp_ledger_root, test_member):
    record_interaction(
        test_member.member_id,
        counterpart="Aether",
        summary="we talked about the briefing surface",
        source_tag=SourceTag.OBSERVED,
        _allow_test_write=True,
    )
    events = _ledger_events(temp_ledger_root, "aria")
    types = [e[0] for e in events]
    assert "MEMBER_INTERACTION_LOGGED" in types


def test_record_knowledge_emits_ledger_event(temp_ledger_root, test_member):
    record_knowledge(
        test_member.member_id,
        content="something I observed because the briefing surfaced it",
        source_tag=SourceTag.OBSERVED,
        _allow_test_write=True,
    )
    events = _ledger_events(temp_ledger_root, "aria")
    types = [e[0] for e in events]
    assert "MEMBER_KNOWLEDGE_LEARNED" in types


def test_record_opinion_emits_ledger_event(temp_ledger_root, test_member):
    record_opinion(
        test_member.member_id,
        stance="we observed the briefing close the working-memory seam",
        source_tag=SourceTag.OBSERVED,
        evidence="2026-05-12 verification turn produced the affect entry that surfaced in next briefing run",
        _allow_test_write=True,
    )
    events = _ledger_events(temp_ledger_root, "aria")
    types = [e[0] for e in events]
    assert "MEMBER_OPINION_FORMED" in types


def test_record_affect_failure_in_ledger_does_not_break_family_db_write(
    temp_ledger_root, test_member
):
    """Ledger failure must never cascade into rejected family.db write."""
    with patch(
        "divineos.core.family.family_member_ledger.append_event",
        side_effect=RuntimeError("ledger boom"),
    ):
        result = record_affect(
            test_member.member_id,
            valence=0.1,
            arousal=0.2,
            dominance=0.3,
            source_tag=SourceTag.OBSERVED,
            note="ledger-broken-but-write-survives test",
            _allow_test_write=True,
        )
        assert result.affect_id.startswith("af-")
