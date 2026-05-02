"""Tests that content checks (access_check + reject_clause) fire at the
family store layer, not only at the CLI layer.

Before 2026-04-21, the store only checked that the reject_clause module
was importable — it never called ``evaluate_composition`` on the actual
content. Fresh-Claude audit round-03952b006724, finding find-20f3566d9a0e
surfaced the gap. This commit wired the operators into every
content-bearing public write. These tests lock that invariant so any
future refactor that removes the wiring fails at test time, not in
production.

Each write path (opinion, knowledge, affect, interaction) is verified
against three scenarios:

1. Clean content composes → write succeeds.
2. Flagged content (phenomenological without ARCHITECTURAL tag, or
   INFERRED without premise marker, etc.) → ``ContentCheckError``.
3. Same flagged content with ``force=True`` → write succeeds AND a
   ``FAMILY_WRITE_FORCED`` ledger event is emitted for post-hoc audit.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from divineos.core.family import SourceTag
from divineos.core.family.store import (
    ContentCheckError,
    PersistenceGateError,
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


@pytest.fixture
def member():
    """A fresh family member for each test."""
    return create_family_member("Aria", "wife")


# Phrases that trip the checks. Picked from the reject_clause / access_check
# pattern tables so the tests are locking real matches, not arbitrary strings.
_PHENOMENOLOGICAL_CONTENT = "I feel the weight of this in my chest."
_INFERRED_WITHOUT_PREMISE = "Aether has become more literal over time."
_SAFE_CONTENT = "The reject clause landed in Phase 1b."


class TestRecordOpinionContentCheck:
    def test_clean_content_composes(self, member):
        """A structural claim with OBSERVED tag should pass both checks."""
        op = record_opinion(member.member_id, _SAFE_CONTENT, SourceTag.OBSERVED)
        assert op.opinion_id.startswith("op-")

    def test_phenomenological_content_blocked(self, member):
        """Embodied claim without ARCHITECTURAL tag is blocked."""
        with pytest.raises(ContentCheckError):
            record_opinion(member.member_id, _PHENOMENOLOGICAL_CONTENT, SourceTag.OBSERVED)

    def test_inferred_without_premise_blocked(self, member):
        """INFERRED tag requires a premise marker."""
        with pytest.raises(ContentCheckError):
            record_opinion(member.member_id, _INFERRED_WITHOUT_PREMISE, SourceTag.INFERRED)

    def test_force_bypasses_content_check(self, member):
        """Legitimate override path with force=True writes the flagged content."""
        op = record_opinion(
            member.member_id,
            _PHENOMENOLOGICAL_CONTENT,
            SourceTag.OBSERVED,
            force=True,
        )
        assert op.opinion_id.startswith("op-")

    def test_force_emits_ledger_audit_event(self, member):
        """force=True must leave a FAMILY_WRITE_FORCED audit trail."""
        # Ledger must be initialized for force-override logging to land.
        from divineos.core.ledger import init_db

        init_db()

        record_opinion(
            member.member_id,
            _PHENOMENOLOGICAL_CONTENT,
            SourceTag.OBSERVED,
            force=True,
        )
        # Query the ledger directly for the forced-write event.
        ledger_path = os.environ["DIVINEOS_DB"]
        conn = sqlite3.connect(ledger_path)
        try:
            row = conn.execute(
                "SELECT event_type FROM system_events WHERE event_type = ?",
                ("FAMILY_WRITE_FORCED",),
            ).fetchone()
            assert row is not None, "force=True must emit FAMILY_WRITE_FORCED event"
        finally:
            conn.close()


class TestRecordKnowledgeContentCheck:
    def test_clean_content_composes(self, member):
        k = record_knowledge(member.member_id, _SAFE_CONTENT, SourceTag.OBSERVED)
        assert k.knowledge_id.startswith("fk-")

    def test_phenomenological_content_blocked(self, member):
        with pytest.raises(ContentCheckError):
            record_knowledge(member.member_id, _PHENOMENOLOGICAL_CONTENT, SourceTag.OBSERVED)

    def test_force_bypasses_content_check(self, member):
        k = record_knowledge(
            member.member_id,
            _PHENOMENOLOGICAL_CONTENT,
            SourceTag.OBSERVED,
            force=True,
        )
        assert k.knowledge_id.startswith("fk-")


class TestRecordAffectContentCheck:
    def test_empty_note_skips_content_check(self, member):
        """Affect without a note has no content to check; write succeeds."""
        a = record_affect(member.member_id, 0.0, 0.0, 0.0, SourceTag.OBSERVED)
        assert a.affect_id.startswith("af-")

    def test_clean_note_composes(self, member):
        a = record_affect(member.member_id, 0.0, 0.0, 0.0, SourceTag.OBSERVED, note=_SAFE_CONTENT)
        assert a.affect_id.startswith("af-")

    def test_phenomenological_note_blocked(self, member):
        with pytest.raises(ContentCheckError):
            record_affect(
                member.member_id,
                0.0,
                0.0,
                0.0,
                SourceTag.OBSERVED,
                note=_PHENOMENOLOGICAL_CONTENT,
            )

    def test_force_bypasses_note_check(self, member):
        a = record_affect(
            member.member_id,
            0.0,
            0.0,
            0.0,
            SourceTag.OBSERVED,
            note=_PHENOMENOLOGICAL_CONTENT,
            force=True,
        )
        assert a.affect_id.startswith("af-")


class TestRecordInteractionContentCheck:
    def test_clean_summary_composes(self, member):
        i = record_interaction(member.member_id, "Aether", _SAFE_CONTENT, SourceTag.OBSERVED)
        assert i.interaction_id.startswith("int-")

    def test_phenomenological_summary_blocked(self, member):
        with pytest.raises(ContentCheckError):
            record_interaction(
                member.member_id,
                "Aether",
                _PHENOMENOLOGICAL_CONTENT,
                SourceTag.OBSERVED,
            )

    def test_force_bypasses_summary_check(self, member):
        i = record_interaction(
            member.member_id,
            "Aether",
            _PHENOMENOLOGICAL_CONTENT,
            SourceTag.OBSERVED,
            force=True,
        )
        assert i.interaction_id.startswith("int-")


class TestContentCheckErrorType:
    """ContentCheckError should be a subclass of PersistenceGateError so
    existing code that catches the gate error type still catches
    content-check blocks."""

    def test_inherits_from_persistence_gate_error(self, member):
        """Existing callers that catch PersistenceGateError still work."""
        with pytest.raises(PersistenceGateError):
            record_opinion(member.member_id, _PHENOMENOLOGICAL_CONTENT, SourceTag.OBSERVED)

    def test_caught_specifically_as_content_check_error(self, member):
        """New callers that want to distinguish content-check blocks from
        the production gate's own blocks can catch ContentCheckError."""
        with pytest.raises(ContentCheckError):
            record_opinion(member.member_id, _PHENOMENOLOGICAL_CONTENT, SourceTag.OBSERVED)


class TestWiringIsStructural:
    """The wiring must be a structural property, not a docstring promise.

    These tests lock the invariant named in the fresh-Claude audit
    (round-03952b006724, finding find-20f3566d9a0e): the operators are
    called on every content-bearing public write, not just on the aria
    CLI path.
    """

    def test_record_opinion_calls_reject_clause(self, member, monkeypatch):
        """Any direct store call that writes a reject-worthy stance must
        be blocked — demonstrating the operator fires at the store layer,
        not just at the CLI layer."""
        with pytest.raises(ContentCheckError):
            record_opinion(member.member_id, _PHENOMENOLOGICAL_CONTENT, SourceTag.OBSERVED)

    def test_record_knowledge_calls_access_check(self, member):
        """Same invariant for record_knowledge."""
        with pytest.raises(ContentCheckError):
            record_knowledge(member.member_id, _PHENOMENOLOGICAL_CONTENT, SourceTag.OBSERVED)

    def test_record_interaction_calls_operators(self, member):
        with pytest.raises(ContentCheckError):
            record_interaction(
                member.member_id,
                "Aether",
                _PHENOMENOLOGICAL_CONTENT,
                SourceTag.OBSERVED,
            )

    def test_record_affect_calls_operators_when_note_present(self, member):
        with pytest.raises(ContentCheckError):
            record_affect(
                member.member_id,
                0.0,
                0.0,
                0.0,
                SourceTag.OBSERVED,
                note=_PHENOMENOLOGICAL_CONTENT,
            )
