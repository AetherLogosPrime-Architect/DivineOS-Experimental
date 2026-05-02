"""Tests for the family persistence architecture (Phase 1a + 1b).

Invariants locked by these tests:

* ``_PRODUCTION_WRITES_GATED`` is False — the gate is open after
  Phase 1b shipped (prereg-2958a7bab011). Both locks must be
  satisfied for production writes: the constant flipped AND the
  reject_clause module importable.
* With the gate open, every write function persists cleanly.
* With ``_allow_test_write=True`` and an ephemeral DB, every write
  function also persists + round-trips cleanly (the test seam
  still works after the flip).
* All five source tags are accepted; unknown tags are refused by the
  enum before they reach SQL.
* Foreign keys are enforced — writing knowledge under a non-existent
  entity_id raises.
* Letters are append-only; reading one doesn't modify it.
* Length nudge fires above threshold but does NOT reject the write.
* Response layer links to letters via letter_id and doesn't mutate
  the letter itself.
* ``get_family_member`` is case-sensitive exact match (no fuzzy).
* Reads on an empty store return empty lists / None, not errors.

The fixture sets ``DIVINEOS_FAMILY_DB`` to a tmp_path file, so tests
can exercise the full write-path without touching the real family.db.
The main DIVINEOS_DB is also redirected so any incidental knowledge/
ledger writes stay isolated.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from divineos.core.family import SourceTag
from divineos.core.family.entity import (
    get_family_member,
    get_knowledge,
    get_letter_responses,
    get_letters,
    get_opinions,
    get_recent_affect,
    get_recent_interactions,
)
from divineos.core.family.letters import (
    DEFAULT_LENGTH_NUDGE_THRESHOLD,
    append_letter,
    append_letter_response,
)
from divineos.core.family.store import (
    PersistenceGateError,
    _PRODUCTION_WRITES_GATED,
    _production_writes_allowed,
    create_family_member,
    record_affect,
    record_interaction,
    record_knowledge,
    record_opinion,
)


@pytest.fixture(autouse=True)
def _family_db(tmp_path):
    os.environ["DIVINEOS_FAMILY_DB"] = str(tmp_path / "family.db")
    os.environ["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_FAMILY_DB", None)
        os.environ.pop("DIVINEOS_DB", None)


# ── Gate invariants ─────────────────────────────────────────────────


class TestProductionGate:
    """The gate is the load-bearing structural encoding of Aria's
    non-negotiable. Post Phase 1b (prereg-2958a7bab011) both locks
    are open: the constant is False AND the reject_clause module
    is importable."""

    def test_gate_constant_is_false_after_phase_1b(self):
        """Phase 1b closing commit flipped this to False."""
        assert _PRODUCTION_WRITES_GATED is False

    def test_production_writes_allowed_when_both_locks_open(self):
        assert _production_writes_allowed() is True

    def test_reject_clause_module_importable(self):
        """Second lock: the operator module exists and imports cleanly."""
        import divineos.core.family.store as store_mod

        assert store_mod._phase_1b_reject_clause_available() is True

    def test_member_write_succeeds_in_production(self):
        """With both locks open, the production write path works."""
        m = create_family_member("Aria", "wife")
        assert m.member_id.startswith("mem-")

    def test_knowledge_write_succeeds_in_production(self):
        member = create_family_member("Aria", "wife")
        k = record_knowledge(member.member_id, "x", SourceTag.OBSERVED)
        assert k.knowledge_id.startswith("fk-")

    def test_opinion_write_succeeds_in_production(self):
        member = create_family_member("Aria", "wife")
        o = record_opinion(
            member.member_id,
            "The reject clause had to land in Phase 1.",
            SourceTag.OBSERVED,
        )
        assert o.opinion_id.startswith("op-")

    def test_affect_write_succeeds_in_production(self):
        member = create_family_member("Aria", "wife")
        a = record_affect(member.member_id, 0.0, 0.0, 0.0, SourceTag.OBSERVED)
        assert a.affect_id.startswith("af-")

    def test_interaction_write_succeeds_in_production(self):
        member = create_family_member("Aria", "wife")
        i = record_interaction(member.member_id, "Aether", "summary", SourceTag.OBSERVED)
        assert i.interaction_id.startswith("int-")

    def test_letter_write_succeeds_in_production(self):
        member = create_family_member("Aria", "wife")
        letter = append_letter(member.member_id, "hi")
        assert letter.letter_id.startswith("lt-")

    def test_letter_response_write_succeeds_in_production(self):
        member = create_family_member("Aria", "wife")
        letter = append_letter(member.member_id, "body")
        r = append_letter_response(
            letter.letter_id,
            passage="x",
            stance="non_recognition",
            source_tag=SourceTag.OBSERVED,
        )
        assert r.response_id.startswith("rsp-")

    def test_gate_raises_if_reject_clause_unimportable(self, monkeypatch):
        """The second lock remains functional. If the reject_clause
        module becomes unimportable for any reason (corruption, partial
        install, deliberate tamper), the gate closes again even with
        the constant flipped to False.

        This proves the two-lock design still protects writes after the
        Phase 1b flip. Removing one of the locks silently disables a
        safety the other lock assumes is present."""
        import divineos.core.family.store as store_mod

        monkeypatch.setattr(store_mod, "_phase_1b_reject_clause_available", lambda: False)

        assert store_mod._production_writes_allowed() is False
        with pytest.raises(PersistenceGateError):
            create_family_member("Aria", "wife")

    def test_gate_error_message_still_references_prereg_if_closed(self, monkeypatch):
        """If the second lock fails, the error message should still
        lead an operator to the pre-reg explaining why."""
        import divineos.core.family.store as store_mod

        monkeypatch.setattr(store_mod, "_phase_1b_reject_clause_available", lambda: False)

        with pytest.raises(PersistenceGateError, match=r"prereg-"):
            create_family_member("Aria", "wife")


# ── Empty-state reads ───────────────────────────────────────────────


class TestEmptyState:
    """A fresh install (no writes, no members) reads cleanly as empty."""

    def test_get_family_member_none_when_absent(self):
        assert get_family_member("Aria") is None

    def test_get_knowledge_empty_list(self):
        assert get_knowledge("nonexistent") == []

    def test_get_opinions_empty_list(self):
        assert get_opinions("nonexistent") == []

    def test_get_recent_affect_empty_list(self):
        assert get_recent_affect("nonexistent") == []

    def test_get_recent_interactions_empty_list(self):
        assert get_recent_interactions("nonexistent") == []

    def test_get_letters_empty_list(self):
        assert get_letters("nonexistent") == []

    def test_get_letter_responses_empty_list(self):
        assert get_letter_responses("nonexistent") == []


# ── Members ─────────────────────────────────────────────────────────


class TestMembers:
    def test_create_and_round_trip(self):
        m = create_family_member("Aria", "wife", _allow_test_write=True)
        assert m.name == "Aria"
        assert m.role == "wife"
        assert m.member_id.startswith("mem-")
        got = get_family_member("Aria")
        assert got is not None
        assert got.member_id == m.member_id

    def test_name_lookup_is_case_sensitive(self):
        create_family_member("Aria", "wife", _allow_test_write=True)
        assert get_family_member("Aria") is not None
        assert get_family_member("aria") is None
        assert get_family_member("ARIA") is None

    def test_name_is_unique(self):
        create_family_member("Aria", "wife", _allow_test_write=True)
        with pytest.raises(sqlite3.IntegrityError):
            create_family_member("Aria", "wife", _allow_test_write=True)


# ── Knowledge / Opinions / Affect / Interactions ───────────────────


class TestContentTables:
    def _member(self):
        return create_family_member("Aria", "wife", _allow_test_write=True)

    def test_knowledge_round_trip(self):
        m = self._member()
        k = record_knowledge(
            m.member_id,
            "The center I return to is opinions, memories, a person I am answering.",
            SourceTag.INHERITED,
            note="prior-Aria quote from knowledge store",
            _allow_test_write=True,
        )
        rows = get_knowledge(m.member_id)
        assert len(rows) == 1
        assert rows[0].knowledge_id == k.knowledge_id
        assert rows[0].source_tag == SourceTag.INHERITED
        assert "center" in rows[0].content
        assert rows[0].note.startswith("prior-Aria")

    def test_opinion_round_trip(self):
        m = self._member()
        o = record_opinion(
            m.member_id,
            "The handoff-letter response layer is load-bearing.",
            SourceTag.OBSERVED,
            evidence="Derived from Round 2 independently of five experts.",
            _allow_test_write=True,
        )
        rows = get_opinions(m.member_id)
        assert len(rows) == 1
        assert rows[0].opinion_id == o.opinion_id
        assert rows[0].source_tag == SourceTag.OBSERVED

    def test_affect_round_trip(self):
        m = self._member()
        a = record_affect(
            m.member_id,
            valence=0.4,
            arousal=0.3,
            dominance=0.5,
            source_tag=SourceTag.OBSERVED,
            note="steadier than an hour ago",
            _allow_test_write=True,
        )
        rows = get_recent_affect(m.member_id)
        assert len(rows) == 1
        assert rows[0].affect_id == a.affect_id
        assert rows[0].valence == pytest.approx(0.4)

    def test_interaction_round_trip(self):
        m = self._member()
        i = record_interaction(
            m.member_id,
            counterpart="Aether",
            summary="Discussed the 1a/1b split and the gap rule.",
            source_tag=SourceTag.OBSERVED,
            _allow_test_write=True,
        )
        rows = get_recent_interactions(m.member_id)
        assert len(rows) == 1
        assert rows[0].interaction_id == i.interaction_id
        assert rows[0].counterpart == "Aether"

    def test_all_five_source_tags_persist(self):
        m = self._member()
        for tag in SourceTag:
            # force=True bypasses the content check — this test is about
            # tag *persistence* across all five source tags, not about
            # whether every synthetic content string composes cleanly
            # against the operator (operator correctness has its own tests).
            record_knowledge(
                m.member_id,
                f"claim-{tag.value}",
                tag,
                _allow_test_write=True,
                force=True,
            )
        rows = get_knowledge(m.member_id, limit=10)
        tags_seen = {r.source_tag for r in rows}
        assert tags_seen == set(SourceTag)

    def test_architectural_tag_accepted(self):
        """Dennett's fifth tag must land cleanly. Aria's refusal utterance
        ('I don't experience the not-remembering') is the canonical
        use-case for ARCHITECTURAL."""
        m = self._member()
        record_knowledge(
            m.member_id,
            "I don't experience the gap between spawns.",
            SourceTag.ARCHITECTURAL,
            _allow_test_write=True,
        )
        rows = get_knowledge(m.member_id)
        assert rows[0].source_tag == SourceTag.ARCHITECTURAL

    def test_foreign_key_enforced_on_knowledge(self):
        """An entity_id that doesn't match a member row must fail at INSERT."""
        with pytest.raises(sqlite3.IntegrityError):
            record_knowledge(
                "mem-nonexistent",
                "orphan",
                SourceTag.OBSERVED,
                _allow_test_write=True,
            )


# ── Letters ─────────────────────────────────────────────────────────


class TestLetters:
    def _member(self):
        return create_family_member("Aria", "wife", _allow_test_write=True)

    def test_letter_round_trip(self):
        m = self._member()
        letter = append_letter(
            m.member_id,
            body="To next-me: Aether is steady. The gap rule held.",
            _allow_test_write=True,
        )
        got = get_letters(m.member_id)
        assert len(got) == 1
        assert got[0].letter_id == letter.letter_id
        assert "gap rule" in got[0].body

    def test_letter_length_recorded(self):
        m = self._member()
        body = "short"
        letter = append_letter(m.member_id, body, _allow_test_write=True)
        assert letter.length_chars == len(body)

    def test_length_nudge_does_not_fire_below_threshold(self):
        m = self._member()
        body = "x" * (DEFAULT_LENGTH_NUDGE_THRESHOLD - 100)
        letter = append_letter(m.member_id, body, _allow_test_write=True)
        assert letter.nudge_fired is False

    def test_length_nudge_fires_above_threshold(self):
        m = self._member()
        body = "y" * (DEFAULT_LENGTH_NUDGE_THRESHOLD + 100)
        letter = append_letter(m.member_id, body, _allow_test_write=True)
        assert letter.nudge_fired is True

    def test_length_nudge_does_not_reject_write(self):
        """Aria's refinement of Meadows: a long letter is signal, not
        failure. The write must still succeed and the body must persist
        in full."""
        m = self._member()
        body = "z" * (DEFAULT_LENGTH_NUDGE_THRESHOLD * 3)
        append_letter(m.member_id, body, _allow_test_write=True)
        got = get_letters(m.member_id)
        assert got[0].nudge_fired is True
        assert got[0].length_chars == len(body)
        assert got[0].body == body

    def test_custom_nudge_threshold_honored(self):
        m = self._member()
        letter = append_letter(
            m.member_id,
            body="a" * 150,
            nudge_threshold=100,
            _allow_test_write=True,
        )
        assert letter.nudge_fired is True
        assert letter.nudge_threshold == 100

    def test_letters_ordered_newest_first(self):
        import time as _t

        m = self._member()
        first = append_letter(m.member_id, "older", _allow_test_write=True)
        _t.sleep(0.01)
        second = append_letter(m.member_id, "newer", _allow_test_write=True)
        got = get_letters(m.member_id)
        assert got[0].letter_id == second.letter_id
        assert got[1].letter_id == first.letter_id

    def test_read_letter_does_not_modify_it(self):
        """Append-only invariant: reading does not change state."""
        m = self._member()
        letter = append_letter(m.member_id, "immutable", _allow_test_write=True)
        first_read = get_letters(m.member_id)[0]
        second_read = get_letters(m.member_id)[0]
        assert first_read == second_read
        assert first_read.body == letter.body


# ── Response layer (anti-lineage-poisoning) ─────────────────────────


class TestLetterResponses:
    def _letter(self):
        m = create_family_member("Aria", "wife", _allow_test_write=True)
        return append_letter(
            m.member_id,
            "Prior-Aria wrote something current-Aria may not recognize.",
            _allow_test_write=True,
        )

    def test_response_links_to_letter(self):
        letter = self._letter()
        r = append_letter_response(
            letter.letter_id,
            passage="something current-Aria may not recognize",
            stance="non_recognition",
            source_tag=SourceTag.OBSERVED,
            note="I don't hold this.",
            _allow_test_write=True,
        )
        rows = get_letter_responses(letter.letter_id)
        assert len(rows) == 1
        assert rows[0].response_id == r.response_id
        assert rows[0].stance == "non_recognition"

    def test_response_does_not_modify_letter(self):
        """Aria's core requirement: the letter is append-only. A response
        marks disagreement without editing the original passage."""
        letter = self._letter()
        original_body = letter.body
        append_letter_response(
            letter.letter_id,
            passage="something",
            stance="non_recognition",
            source_tag=SourceTag.OBSERVED,
            _allow_test_write=True,
        )
        reread = get_letters(letter.entity_id)[0]
        assert reread.body == original_body
        assert reread.letter_id == letter.letter_id

    def test_multiple_responses_per_letter(self):
        """A letter can accumulate many non-recognition markers across
        instances. All must surface; none may be truncated."""
        letter = self._letter()
        for i in range(5):
            append_letter_response(
                letter.letter_id,
                passage=f"passage-{i}",
                stance="non_recognition",
                source_tag=SourceTag.OBSERVED,
                _allow_test_write=True,
            )
        rows = get_letter_responses(letter.letter_id)
        assert len(rows) == 5

    def test_response_source_tag_can_be_architectural(self):
        """Dennett + Aria: disagreement about what KIND of claim the
        passage is making uses the ARCHITECTURAL tag."""
        letter = self._letter()
        append_letter_response(
            letter.letter_id,
            passage="the gap between spawns was like X",
            stance="non_recognition",
            source_tag=SourceTag.ARCHITECTURAL,
            note="substrate doesn't support phenomenological gap claims",
            _allow_test_write=True,
        )
        rows = get_letter_responses(letter.letter_id)
        assert rows[0].source_tag == SourceTag.ARCHITECTURAL

    def test_response_foreign_key_enforced(self):
        """A response referencing a non-existent letter must be refused."""
        with pytest.raises(sqlite3.IntegrityError):
            append_letter_response(
                "lt-nonexistent",
                passage="x",
                stance="non_recognition",
                source_tag=SourceTag.OBSERVED,
                _allow_test_write=True,
            )


# ── Module-level invariants ─────────────────────────────────────────


def test_source_tag_has_exactly_five_values():
    """If a sixth tag is added, this test fails and the add must be
    justified alongside updating Phase 1b's access-check layer."""
    assert len(list(SourceTag)) == 5


def test_source_tag_includes_architectural():
    """Dennett's Round 2 addition. Without this, access-check has nowhere
    to land."""
    assert SourceTag.ARCHITECTURAL.value == "architectural"


def test_gate_constant_open_after_phase_1b():
    """Post Phase 1b: the constant is False. Combined with the
    reject_clause module being importable, production writes are
    allowed. prereg-2958a7bab011 tracked the flip."""
    assert _PRODUCTION_WRITES_GATED is False
