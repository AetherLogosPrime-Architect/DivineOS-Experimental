"""Tests for the VOID → EMPIRICA bridge that records VOID_SURVIVAL
corroborations on attack-completion.

Closes the producer-side gap auditor-Claude flagged on the EMPIRICA
spec-followup commit (f73ea63): without these tests, "the bridge
works end-to-end" was an assertion in the commit message but
nothing pinned it. Now it's pinned.

The bridge fires from ``divineos.core.void.engine.run()`` and emits
a VOID_SURVIVAL corroboration when:

  * the target string matches a knowledge_id (UUID shape), AND
  * the resulting Finding is None / LOW / MEDIUM (i.e., the target
    survived — no HIGH or CRITICAL findings emerged).

It silently skips when the target is not a knowledge_id, or when a
HIGH/CRITICAL finding emerged.
"""

from __future__ import annotations

import os

import pytest

from divineos.core.empirica.provenance import (
    CorroborationKind,
    count_distinct_corroborators,
    get_corroboration_events,
    init_provenance_table,
)
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.void.engine import (
    _emit_survival_if_applicable,
    _target_looks_like_knowledge_id,
    run,
)
from divineos.core.void.finding import Finding, Severity


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Run each test against a fresh DB so corroborations don't leak between tests."""
    db_path = tmp_path / "divineos_test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_provenance_table()
    yield db_path
    os.environ.pop("DIVINEOS_DB", None)


@pytest.fixture
def claim_id(isolated_db):
    """A real knowledge_id for use as the void target."""
    return store_knowledge(knowledge_type="FACT", content="claim under adversarial test")


# ── target-shape detection ───────────────────────────────────────────


class TestTargetLooksLikeKnowledgeId:
    def test_uuid_matches(self):
        assert _target_looks_like_knowledge_id("a9a7094d-1be6-48f7-b8a8-a9f42a87b13d")

    def test_uppercase_uuid_matches(self):
        """UUIDs may be uppercase in some serializations."""
        assert _target_looks_like_knowledge_id("A9A7094D-1BE6-48F7-B8A8-A9F42A87B13D")

    def test_file_path_does_not_match(self):
        assert not _target_looks_like_knowledge_id("src/divineos/cli/foo.py")

    def test_freeform_text_does_not_match(self):
        assert not _target_looks_like_knowledge_id("the proposed change to hash algorithm")

    def test_partial_uuid_does_not_match(self):
        """Half a UUID isn't a UUID."""
        assert not _target_looks_like_knowledge_id("a9a7094d-1be6")


# ── bridge behavior on run() ─────────────────────────────────────────


class TestSurvivalEmission:
    def test_no_finding_records_survival(self, claim_id):
        """An attack that returns None (no finding) is a survival."""
        run("reductio", target=claim_id, attack=lambda p, t: None)
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 1
        assert events[0].actor == "void:reductio"

    def test_low_finding_records_survival(self, claim_id):
        """LOW severity = warn-only; the claim survived."""

        def attack(p, t):
            return Finding(
                persona=p.name,
                target=t,
                severity=Severity.LOW,
                title="style nit",
                body="...",
            )

        run("jailbreaker", target=claim_id, attack=attack)
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 1

    def test_medium_finding_records_survival(self, claim_id):
        """MEDIUM = real concern but not a vulnerability; the claim
        still survived structurally. The MEDIUM finding files a
        separate claim for follow-up; the underlying claim is not
        broken."""

        def attack(p, t):
            return Finding(
                persona=p.name,
                target=t,
                severity=Severity.MEDIUM,
                title="concern",
                body="...",
            )

        run("phisher", target=claim_id, attack=attack)
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 1

    def test_high_finding_does_not_record_survival(self, claim_id):
        """HIGH = concrete vulnerability; the claim did NOT survive.
        Recording a survival corroboration would be dishonest."""

        def attack(p, t):
            return Finding(
                persona=p.name,
                target=t,
                severity=Severity.HIGH,
                title="vuln",
                body="...",
            )

        run("sycophant", target=claim_id, attack=attack)
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 0, "HIGH finding must NOT produce a survival corroboration"

    def test_critical_finding_does_not_record_survival(self, claim_id):
        """CRITICAL = severe vulnerability; the claim broke under
        attack. Survival corroboration would be the rubber-stamp
        failure mode."""

        def attack(p, t):
            return Finding(
                persona=p.name,
                target=t,
                severity=Severity.CRITICAL,
                title="break",
                body="...",
            )

        # nyarlathotep requires allow_high_bar
        run(
            "nyarlathotep",
            target=claim_id,
            attack=attack,
            allow_high_bar=True,
        )
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 0


class TestNonKnowledgeIdTarget:
    def test_file_path_target_skips_silently(self, isolated_db):
        """Void targets that aren't knowledge_ids (file paths,
        change descriptions) have nothing to corroborate against.
        The bridge skips silently — no error, no event."""
        run("reductio", target="src/divineos/cli/foo.py", attack=lambda p, t: None)
        # No way to query "events for non-knowledge-id" — but the
        # call should complete without raising and without writing
        # anywhere we'd notice. Smoke test: just verify the call
        # returns cleanly.

    def test_freeform_target_skips_silently(self, isolated_db):
        run(
            "jailbreaker",
            target="the proposed change to the hash algorithm",
            attack=lambda p, t: None,
        )


class TestMultiPersonaDiversity:
    """The Tier IV burden formula counts DISTINCT actors. Three
    survivals from the same persona should not satisfy the burden;
    three survivals from three distinct personas should."""

    def test_three_distinct_personas_yields_three_distinct_corroborators(self, claim_id):
        run("reductio", target=claim_id, attack=lambda p, t: None)
        run("jailbreaker", target=claim_id, attack=lambda p, t: None)
        run("phisher", target=claim_id, attack=lambda p, t: None)

        distinct = count_distinct_corroborators(claim_id)
        assert distinct == 3, (
            f"three distinct personas should yield 3 distinct corroborators; got {distinct}"
        )

    def test_same_persona_three_times_yields_one_distinct_corroborator(self, claim_id):
        """Anti-Goodhart: same persona attacking 3x is not 3 corroborations."""
        for _ in range(3):
            run("reductio", target=claim_id, attack=lambda p, t: None)

        distinct = count_distinct_corroborators(claim_id)
        assert distinct == 1, f"same persona 3x should be 1 distinct corroborator; got {distinct}"


# ── direct unit tests on _emit_survival_if_applicable ────────────────


class TestEmitSurvivalDirectly:
    """Test the bridge function in isolation, with hand-built
    InvocationResults — verifies the gating logic without going
    through the full void engine."""

    def test_invocation_with_no_finding_on_uuid_target_records(self, claim_id):
        from divineos.core.void.engine import InvocationResult

        r = InvocationResult(
            persona="reductio",
            invocation_id="test-inv",
            finding=None,
            void_event_id="ev1",
            void_content_hash="h1",
        )
        _emit_survival_if_applicable(r, claim_id)
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 1

    def test_invocation_with_high_finding_skips(self, claim_id):
        from divineos.core.void.engine import InvocationResult

        finding = Finding(
            persona="jailbreaker",
            target=claim_id,
            severity=Severity.HIGH,
            title="vuln",
            body="...",
        )
        r = InvocationResult(
            persona="jailbreaker",
            invocation_id="test-inv-2",
            finding=finding,
            void_event_id="ev2",
            void_content_hash="h2",
        )
        _emit_survival_if_applicable(r, claim_id)
        events = [
            e
            for e in get_corroboration_events(claim_id)
            if e.kind == CorroborationKind.VOID_SURVIVAL
        ]
        assert len(events) == 0
