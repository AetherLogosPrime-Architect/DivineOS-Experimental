"""Tests for watchmen tier + review-chain support.

Added 2026-04-21 as Commit A of the tiered-audit redesign (claim 44087186).
See knowledge 9dddbd9f for the anti-god-authority principle that motivates
tier defaults.
"""

from __future__ import annotations

import sqlite3

import pytest

from divineos.core.watchmen._schema import (
    _column_exists,
    _migrate_tier_columns,
    init_watchmen_tables,
)
from divineos.core.watchmen.store import (
    chain_tier_for_finding,
    get_finding,
    get_round,
    list_reviews_of,
    submit_finding,
    submit_round,
)
from divineos.core.watchmen.types import (
    DEFAULT_TIER_BY_ACTOR,
    ReviewStance,
    Tier,
    tier_for_actor,
)


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolate each test on its own DB file."""
    db = tmp_path / "watchmen.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    init_watchmen_tables()
    yield db


class TestTierEnum:
    def test_tier_values(self):
        assert Tier.WEAK.value == "WEAK"
        assert Tier.MEDIUM.value == "MEDIUM"
        assert Tier.STRONG.value == "STRONG"

    def test_tier_for_actor_user_is_weak(self):
        assert tier_for_actor("user") == Tier.WEAK

    def test_tier_for_actor_council_is_medium(self):
        assert tier_for_actor("council") == Tier.MEDIUM

    def test_tier_for_actor_grok_is_strong(self):
        assert tier_for_actor("grok") == Tier.STRONG

    def test_tier_for_actor_gemini_is_strong(self):
        assert tier_for_actor("gemini") == Tier.STRONG

    def test_tier_for_actor_claude_auditor_is_strong(self):
        """Disambiguated claude-* actors are STRONG."""
        assert tier_for_actor("claude-opus-auditor") == Tier.STRONG
        assert tier_for_actor("claude-sonnet-external") == Tier.STRONG

    def test_tier_for_actor_unknown_defaults_to_weak(self):
        assert tier_for_actor("some-new-actor") == Tier.WEAK

    def test_default_mapping_has_expected_keys(self):
        assert "user" in DEFAULT_TIER_BY_ACTOR
        assert "council" in DEFAULT_TIER_BY_ACTOR
        assert "grok" in DEFAULT_TIER_BY_ACTOR


class TestSchemaMigration:
    def test_new_table_has_tier_column(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        try:
            assert _column_exists(conn, "audit_rounds", "tier")
            assert _column_exists(conn, "audit_findings", "tier")
            assert _column_exists(conn, "audit_findings", "reviewed_finding_id")
            assert _column_exists(conn, "audit_findings", "review_stance")
        finally:
            conn.close()

    def test_migration_is_idempotent(self, tmp_db):
        """Running init twice must not error."""
        init_watchmen_tables()
        init_watchmen_tables()  # should be a no-op

    def test_migration_adds_columns_to_legacy_table(self, tmp_path, monkeypatch):
        """Simulate a legacy DB without tier columns, then migrate."""
        db = tmp_path / "legacy.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db))

        # Build legacy schema manually (no tier columns)
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE audit_rounds (
                round_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                actor TEXT NOT NULL,
                focus TEXT NOT NULL,
                expert_count INTEGER NOT NULL DEFAULT 0,
                finding_count INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE audit_findings (
                finding_id TEXT PRIMARY KEY,
                round_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                actor TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                recommendation TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'OPEN',
                resolution_notes TEXT NOT NULL DEFAULT '',
                routed_to TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.commit()
        assert not _column_exists(conn, "audit_rounds", "tier")
        _migrate_tier_columns(conn)
        conn.commit()
        assert _column_exists(conn, "audit_rounds", "tier")
        assert _column_exists(conn, "audit_findings", "tier")
        assert _column_exists(conn, "audit_findings", "reviewed_finding_id")
        assert _column_exists(conn, "audit_findings", "review_stance")
        conn.close()


class TestSubmitRoundWithTier:
    def test_user_round_defaults_to_weak(self, tmp_db):
        round_id = submit_round(actor="user", focus="test focus")
        r = get_round(round_id)
        assert r.tier == Tier.WEAK

    def test_council_round_defaults_to_medium(self, tmp_db):
        round_id = submit_round(actor="council", focus="council test")
        r = get_round(round_id)
        assert r.tier == Tier.MEDIUM

    def test_grok_round_defaults_to_strong(self, tmp_db):
        round_id = submit_round(actor="grok", focus="external test")
        r = get_round(round_id)
        assert r.tier == Tier.STRONG

    def test_claude_auditor_round_defaults_to_strong(self, tmp_db):
        round_id = submit_round(actor="claude-opus-auditor", focus="external")
        r = get_round(round_id)
        assert r.tier == Tier.STRONG

    def test_explicit_tier_override(self, tmp_db):
        """A user-filed round can be promoted explicitly if cross-validated."""
        round_id = submit_round(actor="user", focus="cross-validated", tier=Tier.MEDIUM)
        r = get_round(round_id)
        assert r.tier == Tier.MEDIUM

    def test_explicit_tier_as_string(self, tmp_db):
        round_id = submit_round(actor="user", focus="test", tier="STRONG")
        r = get_round(round_id)
        assert r.tier == Tier.STRONG

    def test_invalid_tier_string_raises(self, tmp_db):
        with pytest.raises(ValueError, match="Invalid tier"):
            submit_round(actor="user", focus="test", tier="BANANA")

    def test_tier_override_emits_loud_ledger_event(self, tmp_db):
        """Fresh-Claude audit 2026-04-21: silent tier override was a
        Goodhart loophole. Every override now emits a TIER_OVERRIDE
        ledger event so the override is auditable.
        """
        # Initialize ledger so the override event can land.
        from divineos.core.ledger import init_db

        init_db()

        # user-default is WEAK; explicit MEDIUM is an override.
        submit_round(actor="user", focus="override test", tier="MEDIUM")

        # Query the ledger for TIER_OVERRIDE events.
        import os
        import sqlite3 as _sq

        ledger_path = os.environ["DIVINEOS_DB"]
        conn = _sq.connect(str(ledger_path))
        try:
            row = conn.execute(
                "SELECT event_type FROM system_events WHERE event_type = ?",
                ("TIER_OVERRIDE",),
            ).fetchone()
            assert row is not None, "tier override must emit TIER_OVERRIDE event"
        finally:
            conn.close()

    def test_actor_default_tier_does_not_emit_override(self, tmp_db):
        """When the resolved tier matches the actor's default, no
        TIER_OVERRIDE event is emitted — only actual overrides are loud.
        """
        from divineos.core.ledger import init_db

        init_db()

        # council default IS MEDIUM; explicit MEDIUM is NOT an override.
        submit_round(actor="council", focus="default match", tier="MEDIUM")

        import os
        import sqlite3 as _sq

        ledger_path = os.environ["DIVINEOS_DB"]
        conn = _sq.connect(str(ledger_path))
        try:
            row = conn.execute(
                "SELECT event_type FROM system_events WHERE event_type = ?",
                ("TIER_OVERRIDE",),
            ).fetchone()
            assert row is None, "tier matching actor-default must NOT emit TIER_OVERRIDE"
        finally:
            conn.close()


class TestSubmitFindingWithTier:
    def test_user_finding_defaults_to_weak(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        fid = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        f = get_finding(fid)
        assert f.tier == Tier.WEAK

    def test_council_finding_defaults_to_medium(self, tmp_db):
        round_id = submit_round(actor="council", focus="f")
        fid = submit_finding(
            round_id=round_id,
            actor="council",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        f = get_finding(fid)
        assert f.tier == Tier.MEDIUM

    def test_standalone_finding_has_no_review_link(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        fid = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        f = get_finding(fid)
        assert f.reviewed_finding_id == ""
        assert f.review_stance is None


class TestReviewChainValidation:
    def test_stance_without_reviewed_id_raises(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        with pytest.raises(ValueError, match="reviewed_finding_id is required"):
            submit_finding(
                round_id=round_id,
                actor="user",
                severity="LOW",
                category="BEHAVIOR",
                title="t",
                description="d",
                review_stance=ReviewStance.CONFIRMS,
            )

    def test_reviewed_id_without_stance_raises(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        fid_1 = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="orig",
            description="d",
        )
        with pytest.raises(ValueError, match="review_stance is required"):
            submit_finding(
                round_id=round_id,
                actor="user",
                severity="LOW",
                category="BEHAVIOR",
                title="rev",
                description="d",
                reviewed_finding_id=fid_1,
            )

    def test_nonexistent_reviewed_id_raises(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        with pytest.raises(ValueError, match="does not exist"):
            submit_finding(
                round_id=round_id,
                actor="user",
                severity="LOW",
                category="BEHAVIOR",
                title="t",
                description="d",
                reviewed_finding_id="find-DEADBEEF",
                review_stance=ReviewStance.CONFIRMS,
            )

    def test_review_links_to_parent(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="parent",
            description="d",
        )
        child = submit_finding(
            round_id=round_id,
            actor="grok",
            severity="LOW",
            category="BEHAVIOR",
            title="review",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.CONFIRMS,
        )
        f = get_finding(child)
        assert f.reviewed_finding_id == parent
        assert f.review_stance == ReviewStance.CONFIRMS

    def test_list_reviews_returns_children(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="parent",
            description="d",
        )
        r1 = submit_finding(
            round_id=round_id,
            actor="grok",
            severity="LOW",
            category="BEHAVIOR",
            title="r1",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.CONFIRMS,
        )
        r2 = submit_finding(
            round_id=round_id,
            actor="gemini",
            severity="LOW",
            category="BEHAVIOR",
            title="r2",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.REFINES,
        )
        reviews = list_reviews_of(parent)
        assert len(reviews) == 2
        assert {r.finding_id for r in reviews} == {r1, r2}


class TestChainTierComputation:
    def test_standalone_finding_returns_own_tier(self, tmp_db):
        round_id = submit_round(actor="council", focus="f")
        fid = submit_finding(
            round_id=round_id,
            actor="council",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        assert chain_tier_for_finding(fid) == Tier.MEDIUM

    def test_weak_finding_confirmed_by_medium_escalates(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        assert chain_tier_for_finding(parent) == Tier.WEAK

        submit_finding(
            round_id=round_id,
            actor="council",
            severity="LOW",
            category="BEHAVIOR",
            title="rev",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.CONFIRMS,
        )
        assert chain_tier_for_finding(parent) == Tier.MEDIUM

    def test_weak_finding_confirmed_by_strong_escalates_to_strong(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        submit_finding(
            round_id=round_id,
            actor="grok",
            severity="LOW",
            category="BEHAVIOR",
            title="rev",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.CONFIRMS,
        )
        assert chain_tier_for_finding(parent) == Tier.STRONG

    def test_disputes_does_not_escalate(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        submit_finding(
            round_id=round_id,
            actor="grok",
            severity="LOW",
            category="BEHAVIOR",
            title="rev",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.DISPUTES,
        )
        # STRONG reviewer but DISPUTES — chain stays WEAK
        assert chain_tier_for_finding(parent) == Tier.WEAK

    def test_refines_caps_at_medium_even_from_strong(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        submit_finding(
            round_id=round_id,
            actor="grok",
            severity="LOW",
            category="BEHAVIOR",
            title="rev",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.REFINES,
        )
        # STRONG reviewer but REFINES — chain capped at MEDIUM
        assert chain_tier_for_finding(parent) == Tier.MEDIUM

    def test_max_of_multiple_reviews(self, tmp_db):
        round_id = submit_round(actor="user", focus="f")
        parent = submit_finding(
            round_id=round_id,
            actor="user",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        # Two reviews: one REFINES (caps MEDIUM), one CONFIRMS from STRONG
        submit_finding(
            round_id=round_id,
            actor="council",
            severity="LOW",
            category="BEHAVIOR",
            title="r1",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.REFINES,
        )
        submit_finding(
            round_id=round_id,
            actor="grok",
            severity="LOW",
            category="BEHAVIOR",
            title="r2",
            description="d",
            reviewed_finding_id=parent,
            review_stance=ReviewStance.CONFIRMS,
        )
        assert chain_tier_for_finding(parent) == Tier.STRONG

    def test_missing_finding_returns_weak(self, tmp_db):
        assert chain_tier_for_finding("find-does-not-exist") == Tier.WEAK
