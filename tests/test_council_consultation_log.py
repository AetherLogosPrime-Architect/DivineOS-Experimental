"""Tests for council consultation logging + audit promotion.

Commit B of the tiered-audit redesign. Mode 1.5 design: every council
consultation is logged as a ledger event (always-on, non-gating), and
promotion to an audit_round + findings is explicit via --audit flag or
the programmatic promote_to_audit() API.
"""

from __future__ import annotations

import pytest

from divineos.core.council.consultation_log import (
    CONSULTATION_EVENT_TYPE,
    list_recent_consultations,
    log_consultation,
    promote_to_audit,
)
from divineos.core.council.framework import LensAnalysis
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.store import get_round, list_findings
from divineos.core.watchmen.types import Tier


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolate each test on its own DB file."""
    db = tmp_path / "council_log.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    # Ensure both ledger and watchmen tables exist
    from divineos.core.ledger import init_db

    init_db()
    init_watchmen_tables()
    yield db


def _make_analysis(expert_name: str, concerns: list[str]) -> LensAnalysis:
    """Build a minimal LensAnalysis for testing."""
    return LensAnalysis(
        expert_name=expert_name,
        problem="test problem",
        methodology_applied="test-methodology",
        methodology_steps=[],
        core_principle="test principle",
        relevant_insights=[],
        concerns=concerns,
        severity_map={},
        integration_findings=[],
        optimization_target="",
        non_negotiables=[],
        uncertainty_handling="",
        characteristic_questions=[],
        synthesis="test synthesis",
    )


class TestLogConsultation:
    def test_returns_consultation_id(self, tmp_db):
        logged = log_consultation(
            question="test question",
            selected_expert_names=["Kahneman"],
            analyses=[_make_analysis("Kahneman", ["answer came too fast"])],
            synthesis="short synthesis",
        )
        assert logged.consultation_id.startswith("consult-")
        assert logged.event_id  # non-empty
        assert logged.timestamp > 0

    def test_consultation_appears_in_recent_list(self, tmp_db):
        logged = log_consultation(
            question="q",
            selected_expert_names=["Popper"],
            analyses=[_make_analysis("Popper", ["confirmation seeking"])],
            synthesis="s",
        )
        recent = list_recent_consultations(limit=5)
        ids = [c.get("consultation_id") for c in recent]
        assert logged.consultation_id in ids

    def test_multiple_consultations_ordered_newest_first(self, tmp_db):
        c1 = log_consultation("q1", ["K"], [_make_analysis("K", ["a"])], "s")
        c2 = log_consultation("q2", ["P"], [_make_analysis("P", ["b"])], "s")
        c3 = log_consultation("q3", ["D"], [_make_analysis("D", ["c"])], "s")
        recent = list_recent_consultations(limit=10)
        ids = [c.get("consultation_id") for c in recent]
        # newest first, so c3 before c2 before c1
        assert ids.index(c3.consultation_id) < ids.index(c2.consultation_id)
        assert ids.index(c2.consultation_id) < ids.index(c1.consultation_id)


class TestAlwaysOnLoggingIsNonGating:
    """The whole point of Mode 1.5: consultations log but don't bump the gate."""

    def test_logging_does_not_create_audit_round(self, tmp_db):
        from divineos.core.watchmen.store import list_rounds

        rounds_before = len(list_rounds())
        log_consultation("q", ["K"], [_make_analysis("K", ["a"])], "s")
        rounds_after = len(list_rounds())
        assert rounds_after == rounds_before, (
            "consultation logging must not create audit_round rows"
        )

    def test_logging_does_not_create_findings(self, tmp_db):
        findings_before = len(list_findings())
        log_consultation("q", ["K"], [_make_analysis("K", ["a"])], "s")
        findings_after = len(list_findings())
        assert findings_after == findings_before


class TestPromoteToAudit:
    def test_promotion_creates_audit_round(self, tmp_db):
        logged = log_consultation(
            question="what's gameable about the gate?",
            selected_expert_names=["Yudkowsky", "Popper"],
            analyses=[
                _make_analysis("Yudkowsky", ["self-grading without external check"]),
                _make_analysis("Popper", ["confirmation seeking"]),
            ],
            synthesis="s",
        )
        round_id = promote_to_audit(logged.consultation_id)
        r = get_round(round_id)
        assert r is not None
        assert r.actor == "council"

    def test_promoted_round_defaults_to_medium_tier(self, tmp_db):
        logged = log_consultation("q", ["K"], [_make_analysis("K", ["a"])], "s")
        round_id = promote_to_audit(logged.consultation_id)
        r = get_round(round_id)
        assert r.tier == Tier.MEDIUM

    def test_promoted_round_tier_override(self, tmp_db):
        logged = log_consultation("q", ["K"], [_make_analysis("K", ["a"])], "s")
        round_id = promote_to_audit(logged.consultation_id, tier="STRONG")
        r = get_round(round_id)
        assert r.tier == Tier.STRONG

    def test_each_concern_becomes_a_finding(self, tmp_db):
        logged = log_consultation(
            question="q",
            selected_expert_names=["Yudkowsky", "Kahneman"],
            analyses=[
                _make_analysis("Yudkowsky", ["c1", "c2"]),
                _make_analysis("Kahneman", ["c3"]),
            ],
            synthesis="s",
        )
        round_id = promote_to_audit(logged.consultation_id)
        findings = list_findings(round_id=round_id)
        assert len(findings) == 3

    def test_finding_tagged_with_expert(self, tmp_db):
        logged = log_consultation(
            "q",
            ["Yudkowsky"],
            [_make_analysis("Yudkowsky", ["goodhart risk"])],
            "s",
        )
        round_id = promote_to_audit(logged.consultation_id)
        findings = list_findings(round_id=round_id)
        assert len(findings) == 1
        assert "expert:Yudkowsky" in findings[0].tags

    def test_finding_tagged_with_consultation_id(self, tmp_db):
        logged = log_consultation("q", ["K"], [_make_analysis("K", ["concern"])], "s")
        round_id = promote_to_audit(logged.consultation_id)
        findings = list_findings(round_id=round_id)
        assert any(t == f"consultation:{logged.consultation_id}" for t in findings[0].tags)

    def test_missing_consultation_id_raises(self, tmp_db):
        with pytest.raises(ValueError, match="No COUNCIL_CONSULTATION event"):
            promote_to_audit("consult-does-not-exist")

    def test_promotion_is_idempotent_on_id_lookup(self, tmp_db):
        """Promoting the same consultation twice creates two rounds (by design).

        The operator may want to re-promote after cross-validation adds
        context; each promotion is a distinct round. This test documents
        that behavior so it isn't changed accidentally.
        """
        logged = log_consultation("q", ["K"], [_make_analysis("K", ["c"])], "s")
        r1 = promote_to_audit(logged.consultation_id)
        r2 = promote_to_audit(logged.consultation_id)
        assert r1 != r2


class TestConsultationEventTypeName:
    def test_event_type_constant(self):
        assert CONSULTATION_EVENT_TYPE == "COUNCIL_CONSULTATION"


class TestRaiseOnAbsenceOfLedgerWrite:
    """Aletheia + Perplexity cross-audit 2026-07-16 (Perplexity Finding 1).

    Prior behavior silently swallowed ledger-write failures via
    ``except (ImportError, OSError, sqlite3.OperationalError, TypeError,
    ValueError): logger.debug(...)`` — every failure returned a
    LoggedConsultation with an empty event_id, downstream
    ``invocation_tally()`` saw empty state, and the diversity boost that
    is supposed to fight "same 5 experts always win" was silently dead.

    Fix pattern from affect.py F-VAD-1 template: raise-on-absence. If the
    ledger write can't succeed, callers see the failure so they can't
    return-as-if-it-worked. These tests pin that discipline.
    """

    def test_ledger_write_failure_raises(self, tmp_db, monkeypatch):
        """Force the ledger to raise; log_consultation must propagate,
        NOT silently swallow. This is the exact class of failure the
        prior swallow was hiding."""

        def _boom(*_a, **_kw):
            raise OSError("simulated: ledger DB not writable")

        # Patch the ledger.log_event reference the module uses at call time
        # (log_consultation does a local import; patch at the target module).
        monkeypatch.setattr("divineos.core.ledger.log_event", _boom)

        with pytest.raises(OSError, match="ledger DB not writable"):
            log_consultation(
                question="q",
                selected_expert_names=["Kahneman"],
                analyses=[_make_analysis("Kahneman", ["concern"])],
                synthesis="s",
            )

    def test_ledger_write_failure_does_not_return_empty_event_id(self, tmp_db, monkeypatch):
        """The specific silent-fail shape the prior code produced:
        LoggedConsultation with event_id='' when the write failed.
        The fix means this shape is impossible — either the write
        succeeded (event_id truthy) or the function raised."""

        def _boom(*_a, **_kw):
            raise sqlite3.OperationalError("simulated lock timeout")

        import sqlite3

        monkeypatch.setattr("divineos.core.ledger.log_event", _boom)

        try:
            result = log_consultation(
                question="q",
                selected_expert_names=["K"],
                analyses=[_make_analysis("K", ["c"])],
                synthesis="s",
            )
            # If we get here without raise, the silent-swallow has come back.
            # An empty event_id is the specific historical bug shape.
            assert result.event_id, (
                "log_consultation returned LoggedConsultation with empty "
                "event_id — the silent-swallow bug (Perplexity Finding 1) "
                "has regressed. The write failed but the return acted as if "
                "it succeeded. Raise-on-absence is load-bearing here."
            )
        except sqlite3.OperationalError:
            # This is the desired outcome — the failure propagated.
            pass

    def test_successful_write_still_returns_valid_consultation(self, tmp_db):
        """Regression check: the raise-on-absence fix doesn't break the
        happy path. Normal writes still return a LoggedConsultation with
        a real event_id."""
        result = log_consultation(
            question="q",
            selected_expert_names=["Kahneman"],
            analyses=[_make_analysis("Kahneman", ["concern"])],
            synthesis="s",
        )
        assert result.event_id, "successful write must produce a non-empty event_id"
        assert result.consultation_id.startswith("consult-")
        assert result.timestamp > 0

    def test_invocation_tally_sees_successful_writes(self, tmp_db):
        """The whole point of the fix: downstream invocation_tally() must
        be able to see the consultation events that log_consultation
        writes. If tally comes back empty after a successful write, the
        diversity mechanism is still dead."""
        from divineos.core.council.consultation_log import invocation_tally

        # Log a few consultations naming different experts
        log_consultation("q1", ["Kahneman"], [_make_analysis("Kahneman", ["c"])], "s")
        log_consultation("q2", ["Popper"], [_make_analysis("Popper", ["c"])], "s")
        log_consultation("q3", ["Kahneman"], [_make_analysis("Kahneman", ["c"])], "s")

        tally = invocation_tally(last_n=10)
        # Tally must be non-empty and reflect the writes
        assert tally, (
            "invocation_tally returned empty after successful log_consultation "
            "writes — the diversity mechanism cannot boost under-invoked "
            "experts if tally is empty. Perplexity Finding 1 regression."
        )
        assert tally.get("Kahneman", 0) >= 2, tally
        assert tally.get("Popper", 0) >= 1, tally
