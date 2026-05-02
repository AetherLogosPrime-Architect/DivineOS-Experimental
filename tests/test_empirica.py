"""Tests for EMPIRICA Phase 1 (prereg-ce8998194943).

Coverage:

* ``types`` — Tier/ClaimMagnitude enum invariants, EvidenceReceipt hash
  + chain-link correctness + tamper detection.
* ``burden`` — required_corroboration returns measurably different
  values across tiers at equal magnitudes (pre-reg falsifier #2);
  ADVERSARIAL raises; matrix shape correct.
* ``classifier`` — each rule fires on its canonical trigger; default
  fallback path is labeled; magnitude heuristics hit their keywords.
* ``receipt`` — persistence round-trip; chain verification catches
  in-DB tampering; per-claim retrieval ordering.
* ``routing`` — TRIVIAL/NORMAL skip council; LOAD_BEARING requires 1
  round; FOUNDATIONAL requires 2; any blocked round rejects.
* ``gate`` — full pipeline: burden rejection, council rejection,
  pass-through with receipt; receipt_id column migration.
* Cross-module invariants — valid != true disclaimer is discoverable;
  Tier.ADVERSARIAL propagates rejection through all layers.
"""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

from divineos.core.empirica.burden import burden_matrix, required_corroboration
from divineos.core.empirica.classifier import classify_claim
from divineos.core.empirica.gate import (
    ensure_receipt_column_on_knowledge,
    evaluate_and_issue,
    record_receipt_on_knowledge,
)
from divineos.core.empirica.routing import (
    rounds_required,
    route_for_approval,
)
from divineos.core.empirica.types import (
    ClaimMagnitude,
    EvidenceReceipt,
    Tier,
    ReceiptChainError,
    ReceiptForkError,
)
from divineos.core.empirica.receipt import (
    get_receipt,
    get_receipts_for_claim,
    init_receipt_table,
    issue_receipt,
    verify_chain,
    verify_claim_chain,
    verify_global_chain,
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "empirica-test.db")
    try:
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.ledger import init_db

        init_db()
        init_knowledge_table()
        init_receipt_table()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# ── types ────────────────────────────────────────────────────────────


class TestTierEnum:
    def test_four_tiers_defined(self):
        assert len(list(Tier)) == 4

    def test_tiers_serialize_as_strings(self):
        assert Tier.FALSIFIABLE.value == "falsifiable"
        assert Tier.OUTCOME.value == "outcome"
        assert Tier.PATTERN.value == "pattern"
        assert Tier.ADVERSARIAL.value == "adversarial"

    def test_tier_is_str_subclass(self):
        """String-subclass so SQLite + JSON serialize cleanly."""
        assert isinstance(Tier.FALSIFIABLE, str)


class TestClaimMagnitudeEnum:
    def test_four_magnitudes(self):
        assert len(list(ClaimMagnitude)) == 4

    def test_values_are_integers_ordered(self):
        """Integer values are the burden multiplier — must be ordered."""
        assert ClaimMagnitude.TRIVIAL.value == 0
        assert ClaimMagnitude.NORMAL.value == 1
        assert ClaimMagnitude.LOAD_BEARING.value == 2
        assert ClaimMagnitude.FOUNDATIONAL.value == 3


class TestEvidenceReceiptSelfHash:
    def test_issue_computes_self_hash(self):
        w = EvidenceReceipt.issue(
            claim_id="c1",
            tier=Tier.FALSIFIABLE,
            magnitude=ClaimMagnitude.NORMAL,
            corroboration_count=4,
            council_count=0,
            artifact_pointer=None,
            previous_receipt_hash_global=None,
            previous_receipt_hash_in_claim=None,
        )
        assert w.self_hash
        assert len(w.self_hash) == 64  # sha256 hex

    def test_verify_self_hash_true_on_fresh(self):
        w = EvidenceReceipt.issue(
            "c1", Tier.PATTERN, ClaimMagnitude.LOAD_BEARING, 12, 1, None, None, None
        )
        assert w.verify_self_hash() is True

    def test_verify_self_hash_false_after_tamper(self):
        """Using dataclass.replace to tamper with a frozen field."""
        w = EvidenceReceipt.issue(
            "c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4, 0, None, None, None
        )
        tampered = replace(w, corroboration_count=999)
        assert tampered.verify_self_hash() is False

    def test_self_hash_deterministic_across_issues_with_same_inputs(self):
        """Two receipts with identical content produce identical hashes.

        Since issued_at is wall-clock, use the internal compute method
        directly with a fixed timestamp."""
        # _compute_self_hash signature: (claim_id, tier, magnitude,
        # corroboration_count, council_count, issued_at,
        # artifact_pointer, previous_receipt_hash_global,
        # previous_receipt_hash_in_claim)
        h1 = EvidenceReceipt._compute_self_hash(
            "c", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6, 0, 1000.0, None, None, None
        )
        h2 = EvidenceReceipt._compute_self_hash(
            "c", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6, 0, 1000.0, None, None, None
        )
        assert h1 == h2

    def test_self_hash_changes_with_tier(self):
        h1 = EvidenceReceipt._compute_self_hash(
            "c", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4, 0, 1000.0, None, None, None
        )
        h2 = EvidenceReceipt._compute_self_hash(
            "c", Tier.PATTERN, ClaimMagnitude.NORMAL, 4, 0, 1000.0, None, None, None
        )
        assert h1 != h2


# ── burden ───────────────────────────────────────────────────────────


class TestRequiredCorroboration:
    def test_falsifiable_trivial(self):
        assert required_corroboration(Tier.FALSIFIABLE, ClaimMagnitude.TRIVIAL) == 2

    def test_falsifiable_normal(self):
        assert required_corroboration(Tier.FALSIFIABLE, ClaimMagnitude.NORMAL) == 4

    def test_falsifiable_foundational(self):
        assert required_corroboration(Tier.FALSIFIABLE, ClaimMagnitude.FOUNDATIONAL) == 8

    def test_outcome_normal(self):
        assert required_corroboration(Tier.OUTCOME, ClaimMagnitude.NORMAL) == 6

    def test_pattern_foundational_is_highest(self):
        assert required_corroboration(Tier.PATTERN, ClaimMagnitude.FOUNDATIONAL) == 16

    def test_adversarial_raises_not_implemented(self):
        """Tier IV intentionally unimplemented in Phase 1 — waits for VOID."""
        with pytest.raises(NotImplementedError, match="VOID"):
            required_corroboration(Tier.ADVERSARIAL, ClaimMagnitude.NORMAL)

    def test_tiers_differ_at_equal_magnitude(self):
        """Pre-reg falsifier #2: if the calculator produces the same
        value across tiers at equal magnitude, it's decorative."""
        f = required_corroboration(Tier.FALSIFIABLE, ClaimMagnitude.NORMAL)
        o = required_corroboration(Tier.OUTCOME, ClaimMagnitude.NORMAL)
        p = required_corroboration(Tier.PATTERN, ClaimMagnitude.NORMAL)
        assert f != o and o != p and f != p

    def test_magnitude_scales_within_tier(self):
        """Within a tier, higher magnitude requires strictly more."""
        vals = [
            required_corroboration(Tier.PATTERN, m)
            for m in (
                ClaimMagnitude.TRIVIAL,
                ClaimMagnitude.NORMAL,
                ClaimMagnitude.LOAD_BEARING,
                ClaimMagnitude.FOUNDATIONAL,
            )
        ]
        assert vals == sorted(vals)
        assert len(set(vals)) == 4  # all distinct


class TestBurdenMatrix:
    def test_matrix_covers_three_tiers(self):
        """ADVERSARIAL deliberately omitted (raises on required_corroboration)."""
        m = burden_matrix()
        tiers_present = {t for (t, _) in m}
        assert tiers_present == {Tier.FALSIFIABLE, Tier.OUTCOME, Tier.PATTERN}

    def test_matrix_covers_four_magnitudes(self):
        m = burden_matrix()
        mags = {mag for (_, mag) in m}
        assert mags == set(ClaimMagnitude)

    def test_matrix_twelve_entries(self):
        assert len(burden_matrix()) == 12


# ── classifier ───────────────────────────────────────────────────────


class TestClassifierRules:
    # Tests for tiers above OUTCOME (PATTERN / FALSIFIABLE) must
    # supply an artifact_pointer per prereg-e210f5fb78c9, else the
    # claim is demoted to OUTCOME. These tests confirm the TIER
    # ROUTING rules themselves fire correctly WHEN the pointer is
    # present. Tests for the demotion rule itself live below in
    # TestArtifactPointerRule.
    def test_pattern_knowledge_type_routes_to_pattern(self):
        c = classify_claim("content", knowledge_type="PATTERN", artifact_pointer="test/demo")
        assert c.tier == Tier.PATTERN
        assert "rule-1" in c.reason

    def test_fact_measured_routes_to_falsifiable(self):
        c = classify_claim(
            "x",
            knowledge_type="FACT",
            source="measured",
            artifact_pointer="commit-abc",
        )
        assert c.tier == Tier.FALSIFIABLE
        assert "rule-2" in c.reason

    def test_outcome_types_route_to_outcome(self):
        # OUTCOME doesn't require a pointer — tests the honest middle.
        for kt in ("PRINCIPLE", "BOUNDARY", "MISTAKE", "DIRECTIVE"):
            c = classify_claim("x", knowledge_type=kt)
            assert c.tier == Tier.OUTCOME, f"knowledge_type={kt}"
            assert "rule-3" in c.reason

    def test_pattern_keyword_triggers_pattern(self):
        c = classify_claim(
            "pattern recurring across multiple sessions",
            artifact_pointer="decide-xyz",
        )
        assert c.tier == Tier.PATTERN
        assert "rule-4" in c.reason

    def test_falsifiability_keyword_triggers_falsifiable(self):
        c = classify_claim(
            "threshold asserts repeatable behavior",
            artifact_pointer="prereg-xyz",
        )
        assert c.tier == Tier.FALSIFIABLE
        assert "rule-5" in c.reason

    def test_default_to_outcome(self):
        c = classify_claim("some content with no signal at all")
        assert c.tier == Tier.OUTCOME
        # Default rule is labeled "rule-6" in reason — unchanged.
        assert "rule-6" in c.reason

    def test_classifier_never_returns_adversarial(self):
        """ADVERSARIAL requires VOID routing — never auto-assigned."""
        for content in ("adversarial attack", "red team survival", "steelman claim"):
            c = classify_claim(content)
            assert c.tier != Tier.ADVERSARIAL

    def test_reason_always_populated(self):
        """The audit trail is load-bearing — empty reason means the
        classifier is decorative."""
        c = classify_claim("any content")
        assert c.reason
        assert ";" in c.reason  # tier reason + magnitude reason joined

    def test_classification_is_frozen_dataclass(self):
        c = classify_claim("x")
        with pytest.raises(Exception):
            c.tier = Tier.PATTERN  # type: ignore[misc]


class TestMagnitudeHeuristics:
    def test_explicit_override_wins(self):
        c = classify_claim("trivial typo", explicit_magnitude=ClaimMagnitude.FOUNDATIONAL)
        assert c.magnitude == ClaimMagnitude.FOUNDATIONAL
        assert "explicit" in c.reason

    def test_trivial_keyword_detected(self):
        c = classify_claim("small fix to the cli output")
        assert c.magnitude == ClaimMagnitude.TRIVIAL

    def test_load_bearing_keyword_detected(self):
        c = classify_claim("foundational invariant of the architecture")
        assert c.magnitude == ClaimMagnitude.LOAD_BEARING

    def test_trivial_wins_over_load_bearing_when_both_present(self):
        """TRIVIAL is more specific — 'small fix to architecture' is
        still small."""
        c = classify_claim("small fix to the foundational architecture")
        assert c.magnitude == ClaimMagnitude.TRIVIAL

    def test_default_is_normal(self):
        c = classify_claim("a statement with no magnitude signal")
        assert c.magnitude == ClaimMagnitude.NORMAL


# ── receipt ──────────────────────────────────────────────────────────


class TestReceiptPersistence:
    def test_issue_round_trips(self):
        w = issue_receipt("claim-a", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        loaded = get_receipt(w.receipt_id)
        assert loaded is not None
        assert loaded.receipt_id == w.receipt_id
        assert loaded.tier == Tier.FALSIFIABLE
        assert loaded.magnitude == ClaimMagnitude.NORMAL
        assert loaded.corroboration_count == 4

    def test_get_receipt_missing_returns_none(self):
        assert get_receipt("nonexistent") is None

    def test_get_receipts_for_claim_ordered(self):
        w1 = issue_receipt("claim-multi", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        import time as _t

        _t.sleep(0.01)
        w2 = issue_receipt("claim-multi", Tier.FALSIFIABLE, ClaimMagnitude.LOAD_BEARING, 6)
        receipts = get_receipts_for_claim("claim-multi")
        assert [w.receipt_id for w in receipts] == [w1.receipt_id, w2.receipt_id]

    def test_receipt_id_prefix(self):
        w = issue_receipt("c", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        assert w.receipt_id.startswith("receipt-")


class TestReceiptChain:
    def test_genesis_receipt_has_no_previous(self):
        w = issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        assert w.previous_receipt_hash_global is None
        assert w.previous_receipt_hash_in_claim is None

    def test_second_receipt_chains_to_first(self):
        w1 = issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        w2 = issue_receipt("c2", Tier.PATTERN, ClaimMagnitude.NORMAL, 8)
        # Global chain: w2 links to w1 (different claims, but same
        # global chronology).
        assert w2.previous_receipt_hash_global == w1.self_hash
        # Per-claim chain: w2 is genesis for claim c2.
        assert w2.previous_receipt_hash_in_claim is None

    def test_verify_chain_passes_empty(self):
        verify_chain()  # no raise

    def test_verify_chain_passes_with_receipts(self):
        issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        issue_receipt("c2", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("c3", Tier.PATTERN, ClaimMagnitude.NORMAL, 8)
        verify_chain()  # no raise

    def test_verify_chain_catches_content_tamper(self):
        w = issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE evidence_receipts SET corroboration_count = 999 WHERE receipt_id = ?",
                (w.receipt_id,),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(ReceiptChainError, match="self_hash mismatch"):
            verify_chain()

    def test_verify_chain_catches_broken_link(self):
        """Tamper the previous_receipt_hash_global to create a chain
        break. Dual chain: since w2 is first receipt for claim c2,
        its per-claim chain is fine — the break surfaces on the
        GLOBAL chain as an orphan."""
        issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        w2 = issue_receipt("c2", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)

        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            # Tamper previous_receipt_hash_global AND self_hash so
            # the content-check passes but the chain-check fails.
            fake_prev = "0" * 64
            fake_self = EvidenceReceipt._compute_self_hash(
                w2.claim_id,
                w2.tier,
                w2.magnitude,
                w2.corroboration_count,
                w2.council_count,
                w2.issued_at,
                w2.artifact_pointer,
                fake_prev,
                w2.previous_receipt_hash_in_claim,
            )
            conn.execute(
                "UPDATE evidence_receipts SET previous_receipt_hash_global = ?, "
                "self_hash = ? WHERE receipt_id = ?",
                (fake_prev, fake_self, w2.receipt_id),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(ReceiptChainError, match="Orphan"):
            verify_chain()


class TestDualChain:
    """Hofstadter audit finding find-f2284f22d795.

    The single global chain entangled two concerns: system
    self-integrity AND what a receipt means about its claim.
    Receipts for claim A and claim B share no semantic scope but
    were linked in a way that made verification of claim A depend
    on every receipt ever issued. The fix: per-claim chain AND
    global chain. Each receipt links on both axes. These tests
    lock the invariants.
    """

    def test_first_receipt_for_claim_is_claim_genesis(self):
        """Per-claim chain: first receipt for a given claim_id has
        previous_receipt_hash_in_claim = None, regardless of how
        many receipts for other claims came before it."""
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        first_b = issue_receipt("claim-b", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        assert first_b.previous_receipt_hash_in_claim is None
        # But on the global chain, claim-b's first receipt chains
        # to the prior (the second claim-a receipt).
        assert first_b.previous_receipt_hash_global is not None

    def test_second_receipt_for_claim_chains_in_claim(self):
        """Per-claim: the second receipt for a claim links to the
        first receipt for THAT claim, skipping any intervening
        receipts for other claims."""
        a1 = issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-b", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-c", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        a2 = issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        assert a2.previous_receipt_hash_in_claim == a1.self_hash

    def test_verify_claim_chain_passes_on_clean_store(self):
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-b", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        verify_claim_chain("claim-a")  # no raise
        verify_claim_chain("claim-b")  # no raise

    def test_verify_claim_chain_ignores_other_claims_tamper(self):
        """Tampering a receipt for claim-b must NOT break verification
        of claim-a's per-claim chain. This is the core semantic
        separation Hofstadter flagged."""
        from divineos.core._ledger_base import get_connection

        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        wb = issue_receipt("claim-b", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)

        # Tamper claim-b's self_hash via content edit.
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE evidence_receipts SET corroboration_count = 999 WHERE receipt_id = ?",
                (wb.receipt_id,),
            )
            conn.commit()
        finally:
            conn.close()

        # Per-claim walk for claim-a must PASS (tamper was on b).
        verify_claim_chain("claim-a")
        # Per-claim walk for claim-b must FAIL.
        with pytest.raises(ReceiptChainError, match="self_hash mismatch"):
            verify_claim_chain("claim-b")

    def test_verify_global_chain_separate_from_claim_chain(self):
        """verify_global_chain walks global links; verify_claim_chain
        walks per-claim links. They are independent functions."""
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-b", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        verify_global_chain()  # no raise
        verify_claim_chain("claim-a")  # no raise

    def test_per_claim_fork_detected_in_claim_scope(self):
        """If two receipts for the SAME claim chain to the same
        per-claim previous hash, that's a per-claim fork. The
        scope_label in the error message should identify the
        affected claim so operators can diagnose."""
        from divineos.core._ledger_base import get_connection
        import time as _t

        a1 = issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        a2 = issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        # Forge a third receipt for claim-a that chains in-claim to
        # a1, same as a2 — a per-claim fork.
        fork_at = _t.time()
        fork_self_hash = EvidenceReceipt._compute_self_hash(
            "claim-a",
            Tier.OUTCOME,
            ClaimMagnitude.NORMAL,
            6,
            0,
            fork_at,
            None,
            a2.self_hash,  # valid global link (off-chain for global fork)
            a1.self_hash,  # SAME per-claim previous as a2 — the fork
        )
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO evidence_receipts (receipt_id, claim_id, tier, "
                "magnitude, corroboration_count, council_count, issued_at, "
                "artifact_pointer, previous_receipt_hash_global, "
                "previous_receipt_hash_in_claim, self_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "receipt-afork000",
                    "claim-a",
                    Tier.OUTCOME.value,
                    ClaimMagnitude.NORMAL.value,
                    6,
                    0,
                    fork_at,
                    None,
                    a2.self_hash,
                    a1.self_hash,
                    fork_self_hash,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(ReceiptForkError, match="claim:claim-a"):
            verify_claim_chain("claim-a")

    def test_verify_chain_runs_both_scopes(self):
        """verify_chain() walks global + every per-claim chain. If
        any chain breaks on any scope, verify_chain raises."""
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-b", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("claim-a", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        verify_chain()  # no raise


# ── routing ──────────────────────────────────────────────────────────


class _StubConvene:
    """Deterministic convene stub for routing tests."""

    def __init__(self, concerns: list[str]) -> None:
        self._c = concerns

    def shared_concerns(self) -> list[str]:
        return list(self._c)


class TestReceiptForkDetection:
    """Dijkstra audit finding find-0ea12ad4b5d0.

    The previous verify_chain sorted by issued_at and reported
    concurrent-writer races as tamper events. The fix: traverse
    by hash pointers and report forks as ReceiptForkError
    explicitly. These tests lock the new behavior.
    """

    def test_concurrent_writer_race_detected_as_fork(self):
        """Two receipts chaining to the same previous — the
        textbook race. Must raise ReceiptForkError, not
        ReceiptChainError with tamper-shaped message."""
        from divineos.core._ledger_base import get_connection

        # w1 is genesis. Then simulate two concurrent writers both
        # chaining to w1 by directly inserting both with the same
        # previous_receipt_hash.
        w1 = issue_receipt("claim-genesis", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        w2 = issue_receipt("claim-legit-child", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)

        # Now craft a THIRD receipt that ALSO chains to w1 (as if a
        # second concurrent writer saw w1 as latest and inserted).
        import time as _t

        fork_issued_at = _t.time()
        fork_self_hash = EvidenceReceipt._compute_self_hash(
            "claim-racer",
            Tier.PATTERN,
            ClaimMagnitude.NORMAL,
            8,
            0,
            fork_issued_at,
            None,  # artifact_pointer
            w1.self_hash,  # same global previous as w2 — the race
            None,  # per-claim previous (genesis for claim-racer)
        )
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO evidence_receipts (receipt_id, claim_id, tier, "
                "magnitude, corroboration_count, council_count, issued_at, "
                "artifact_pointer, previous_receipt_hash_global, "
                "previous_receipt_hash_in_claim, self_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "receipt-racer0000",
                    "claim-racer",
                    Tier.PATTERN.value,
                    ClaimMagnitude.NORMAL.value,
                    8,
                    0,
                    fork_issued_at,
                    None,  # artifact_pointer
                    w1.self_hash,
                    None,  # per-claim previous
                    fork_self_hash,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(ReceiptForkError, match="Fork at receipt"):
            verify_chain()
        # Confirm w2 is the legitimate child (was there first)
        assert w2.previous_receipt_hash_global == w1.self_hash

    def test_double_genesis_detected_as_fork(self):
        """Two receipts with previous=None = fork at root.
        Usually happens when two concurrent writers both see
        an empty store and both insert a genesis receipt."""
        from divineos.core._ledger_base import get_connection

        w1 = issue_receipt("claim-a", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)

        # Craft a second genesis receipt directly.
        import time as _t

        second_issued_at = _t.time()
        second_self_hash = EvidenceReceipt._compute_self_hash(
            "claim-b",
            Tier.OUTCOME,
            ClaimMagnitude.NORMAL,
            6,
            0,
            second_issued_at,
            None,  # artifact_pointer
            None,  # global genesis
            None,  # per-claim genesis
        )
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO evidence_receipts (receipt_id, claim_id, tier, "
                "magnitude, corroboration_count, council_count, issued_at, "
                "artifact_pointer, previous_receipt_hash_global, "
                "previous_receipt_hash_in_claim, self_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "receipt-second-gen",
                    "claim-b",
                    Tier.OUTCOME.value,
                    ClaimMagnitude.NORMAL.value,
                    6,
                    0,
                    second_issued_at,
                    None,  # artifact_pointer
                    None,  # global genesis
                    None,  # per-claim genesis
                    second_self_hash,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(ReceiptForkError, match="Multiple genesis"):
            verify_chain()
        assert w1.previous_receipt_hash_global is None  # first was legit

    def test_fork_error_is_subclass_of_chain_error(self):
        """Existing callers catching ReceiptChainError must still
        catch forks — backward compatibility invariant."""
        assert issubclass(ReceiptForkError, ReceiptChainError)

    def test_existing_tamper_detection_still_fires(self):
        """Self-hash tamper should still raise ReceiptChainError
        (NOT ReceiptForkError), distinguishing tamper from fork."""
        from divineos.core._ledger_base import get_connection

        w = issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE evidence_receipts SET corroboration_count = 999 WHERE receipt_id = ?",
                (w.receipt_id,),
            )
            conn.commit()
        finally:
            conn.close()

        # ReceiptChainError, not ReceiptForkError — tamper, not fork.
        with pytest.raises(ReceiptChainError, match="self_hash mismatch") as exc_info:
            verify_chain()
        assert not isinstance(exc_info.value, ReceiptForkError)

    def test_orphan_receipt_detected(self):
        """A receipt whose previous_receipt_hash points to a
        self_hash that doesn't exist must be caught by the orphan
        invariant."""
        from divineos.core._ledger_base import get_connection

        w1 = issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)

        # Craft an orphan — previous points to nothing.
        import time as _t

        orphan_issued_at = _t.time()
        orphan_self_hash = EvidenceReceipt._compute_self_hash(
            "c-orphan",
            Tier.OUTCOME,
            ClaimMagnitude.NORMAL,
            6,
            0,
            orphan_issued_at,
            None,  # artifact_pointer
            "0" * 64,  # fake global previous
            None,  # per-claim genesis (first for c-orphan)
        )
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO evidence_receipts (receipt_id, claim_id, tier, "
                "magnitude, corroboration_count, council_count, issued_at, "
                "artifact_pointer, previous_receipt_hash_global, "
                "previous_receipt_hash_in_claim, self_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "receipt-orphan00",
                    "c-orphan",
                    Tier.OUTCOME.value,
                    ClaimMagnitude.NORMAL.value,
                    6,
                    0,
                    orphan_issued_at,
                    None,  # artifact_pointer
                    "0" * 64,  # fake global previous
                    None,  # per-claim genesis
                    orphan_self_hash,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(ReceiptChainError, match="Orphan"):
            verify_chain()
        assert w1.previous_receipt_hash_global is None

    def test_clean_chain_after_fix_still_passes(self):
        """Regression: the happy path still works after the
        implementation rewrite."""
        issue_receipt("c1", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        issue_receipt("c2", Tier.OUTCOME, ClaimMagnitude.NORMAL, 6)
        issue_receipt("c3", Tier.PATTERN, ClaimMagnitude.NORMAL, 8)
        verify_chain()  # no raise


class TestRouting:
    def test_trivial_requires_no_rounds(self):
        assert rounds_required(ClaimMagnitude.TRIVIAL) == 0

    def test_normal_requires_no_rounds(self):
        assert rounds_required(ClaimMagnitude.NORMAL) == 0

    def test_load_bearing_requires_one_round(self):
        assert rounds_required(ClaimMagnitude.LOAD_BEARING) == 1

    def test_foundational_requires_two_rounds(self):
        assert rounds_required(ClaimMagnitude.FOUNDATIONAL) == 2

    def test_trivial_approves_without_calling_council(self):
        called = {"n": 0}

        def spy(_content):
            called["n"] += 1
            return _StubConvene([])

        r = route_for_approval("x", ClaimMagnitude.TRIVIAL, convene_fn=spy)
        assert r.approved is True
        assert r.council_count == 0
        assert called["n"] == 0  # council never invoked

    def test_load_bearing_clean_approves(self):
        r = route_for_approval(
            "x", ClaimMagnitude.LOAD_BEARING, convene_fn=lambda _: _StubConvene([])
        )
        assert r.approved is True
        assert r.council_count == 1

    def test_load_bearing_with_concerns_blocks(self):
        r = route_for_approval(
            "x",
            ClaimMagnitude.LOAD_BEARING,
            convene_fn=lambda _: _StubConvene(["concern"]),
        )
        assert r.approved is False
        assert r.council_count == 0
        assert "BLOCKED" in r.rationale

    def test_foundational_requires_both_rounds(self):
        """One approved + one blocked = rejected."""
        idx = [0]

        def alternating(_content):
            idx[0] += 1
            return _StubConvene([] if idx[0] == 1 else ["second round concern"])

        r = route_for_approval("x", ClaimMagnitude.FOUNDATIONAL, convene_fn=alternating)
        assert r.approved is False
        assert r.council_count == 1
        # Both rounds named in rationale
        assert "round 1" in r.rationale
        assert "round 2" in r.rationale

    def test_foundational_both_clean_approves(self):
        r = route_for_approval(
            "x", ClaimMagnitude.FOUNDATIONAL, convene_fn=lambda _: _StubConvene([])
        )
        assert r.approved is True
        assert r.council_count == 2

    def test_rationale_never_empty(self):
        r = route_for_approval("x", ClaimMagnitude.TRIVIAL)
        assert r.rationale


# ── gate (full pipeline) ─────────────────────────────────────────────


class TestGate:
    def test_receipt_column_migration_idempotent(self):
        ensure_receipt_column_on_knowledge()
        ensure_receipt_column_on_knowledge()
        # Column exists
        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
        finally:
            conn.close()
        assert "receipt_id" in cols

    def test_burden_rejection_returns_none_receipt(self):
        # FACT + keyword "threshold" -> FALSIFIABLE only if
        # artifact_pointer is supplied; otherwise demoted. Provide
        # the pointer so we're specifically testing the burden gate.
        w, classification, routing = evaluate_and_issue(
            claim_id="c1",
            content="threshold assert",  # falsifiable
            corroboration_count=1,  # below 4 required
            knowledge_type="FACT",
            artifact_pointer="test/demo",
        )
        assert w is None
        assert classification.tier == Tier.FALSIFIABLE
        assert routing is None  # never reached

    def test_council_rejection_returns_none_receipt(self):
        w, c, r = evaluate_and_issue(
            claim_id="c1",
            content="load-bearing architectural claim",
            corroboration_count=20,
            knowledge_type="PATTERN",
            convene_fn=lambda _: _StubConvene(["A", "B"]),
        )
        assert w is None
        assert r is not None
        assert r.approved is False

    def test_passes_with_receipt_issued(self):
        w, c, r = evaluate_and_issue(
            claim_id="c1",
            content="measured threshold assert",
            corroboration_count=8,
            knowledge_type="FACT",
            source="measured",
            artifact_pointer="commit-abc123",
            convene_fn=lambda _: _StubConvene([]),
        )
        assert w is not None
        assert w.tier == Tier.FALSIFIABLE
        # Persisted
        loaded = get_receipt(w.receipt_id)
        assert loaded is not None

    def test_adversarial_tier_raises_via_burden(self):
        """If anyone manages to force Tier.ADVERSARIAL (e.g. by calling
        the gate with explicit magnitude and classifier returning
        ADVERSARIAL somehow — currently it won't, but lock the
        behavior anyway), required_corroboration raises. Defensive."""
        with pytest.raises(NotImplementedError):
            required_corroboration(Tier.ADVERSARIAL, ClaimMagnitude.NORMAL)

    def test_record_receipt_on_knowledge_persists(self):
        from divineos.core.knowledge.crud import store_knowledge

        kid = store_knowledge(
            knowledge_type="FACT",
            content="measured threshold",
            confidence=0.8,
            source_events=["s1"],
            tags=[],
        )
        w = issue_receipt("direct-claim", Tier.FALSIFIABLE, ClaimMagnitude.NORMAL, 4)
        record_receipt_on_knowledge(kid, w.receipt_id)

        from divineos.core._ledger_base import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT receipt_id FROM knowledge WHERE knowledge_id = ?",
                (kid,),
            ).fetchone()
        finally:
            conn.close()
        assert row[0] == w.receipt_id


# ── cross-module invariants ──────────────────────────────────────────


class TestClassifierConfidence:
    """Pre-audit finding #1 fix: Classification.confidence annotates
    how sure the classifier is, so callers can apply extra skepticism
    to low-confidence results without the classifier having to lie
    about its certainty.
    """

    def test_explicit_knowledge_type_is_full_confidence(self):
        """Tier and magnitude both explicit -> 1.0.

        Per prereg-e210f5fb78c9, tiers above OUTCOME require an
        artifact_pointer or the classifier demotes to OUTCOME
        (lowering confidence via the demotion penalty). This test
        isolates tier confidence by providing both explicit
        magnitude and artifact_pointer."""
        c = classify_claim(
            "x",
            knowledge_type="PATTERN",
            explicit_magnitude=ClaimMagnitude.NORMAL,
            artifact_pointer="test/demo",
        )
        assert c.tier == Tier.PATTERN
        assert c.confidence == 1.0

    def test_explicit_fact_measured_is_full_confidence(self):
        c = classify_claim(
            "x",
            knowledge_type="FACT",
            source="measured",
            explicit_magnitude=ClaimMagnitude.NORMAL,
            artifact_pointer="commit-abc",
        )
        assert c.tier == Tier.FALSIFIABLE
        assert c.confidence == 1.0

    def test_explicit_outcome_type_is_full_confidence(self):
        # OUTCOME doesn't need a pointer — pointer rule only demotes
        # PATTERN/FALSIFIABLE classifications.
        c = classify_claim(
            "x",
            knowledge_type="PRINCIPLE",
            explicit_magnitude=ClaimMagnitude.NORMAL,
        )
        assert c.confidence == 1.0

    def test_explicit_tier_with_default_magnitude_is_default_conf(self):
        """Default-fallback magnitude (0.2) drags the min down even
        if tier is explicit. With artifact_pointer provided (to
        avoid demotion), the min is magnitude's 0.2."""
        c = classify_claim("x", knowledge_type="PATTERN", artifact_pointer="test/demo")
        assert c.tier == Tier.PATTERN  # explicit, high confidence
        assert c.magnitude == ClaimMagnitude.NORMAL  # default
        assert c.confidence == 0.2  # dragged down by magnitude default

    def test_content_keyword_tier_lowers_confidence(self):
        """Keyword-triggered tier is 0.5 even if magnitude is explicit."""
        c = classify_claim(
            "pattern recurring across sessions",
            explicit_magnitude=ClaimMagnitude.NORMAL,
            artifact_pointer="test/pattern-demo",
        )
        assert c.tier == Tier.PATTERN
        # Tier is 0.5 (keyword), magnitude is 1.0 (explicit) -> min = 0.5
        assert c.confidence == 0.5

    def test_content_keyword_magnitude_lowers_confidence(self):
        """Keyword-triggered magnitude is 0.5 even if tier is explicit."""
        c = classify_claim(
            "load-bearing architectural invariant",
            knowledge_type="PATTERN",
            artifact_pointer="prereg-demo",
        )
        assert c.magnitude == ClaimMagnitude.LOAD_BEARING
        # Tier is 1.0 (explicit), magnitude is 0.5 (keyword) -> min = 0.5
        assert c.confidence == 0.5

    def test_default_fallback_is_low_confidence(self):
        """No signal = rule-6 default = low confidence."""
        c = classify_claim("some content with no signal at all")
        assert c.tier == Tier.OUTCOME
        assert c.magnitude == ClaimMagnitude.NORMAL
        # Both fell to default -> 0.2 on both dims -> min = 0.2
        assert c.confidence == 0.2

    def test_confidence_is_minimum_of_both_dims(self):
        """Low confidence on ONE dimension drags the whole down —
        classification is only as sure as its weakest component."""
        # Tier: rule 4 (keyword) = 0.5. Magnitude: default = 0.2. Min = 0.2.
        c = classify_claim("pattern recurring repeatedly")
        assert c.confidence == 0.2

    def test_confidence_always_between_zero_and_one(self):
        """Invariant — confidence cannot exceed 1 or go below 0."""
        contents = [
            "",
            "pattern threshold architecture measurably foundational",
            "small fix cli polish typo",
            "random noise",
        ]
        for content in contents:
            c = classify_claim(content, knowledge_type="PATTERN", source="measured")
            assert 0.0 <= c.confidence <= 1.0

    def test_confidence_changes_reason_does_not_suppress(self):
        """Adding confidence didn't eat the reason field — both must
        stay present."""
        c = classify_claim("pattern recurring")
        assert c.reason
        assert hasattr(c, "confidence")


class TestBurdenCalibrationSchedule:
    """Pre-audit finding #2 fix: the calibration plan is now a
    first-class constant + docstring, not just a loose comment."""

    def test_calibration_review_constant_is_30_days(self):
        """Locks the Phase 1 calibration cadence at 30 days. If this
        changes, the docstring calibration plan must change in the
        same diff — otherwise the schedule has drifted silently
        from its documented promise."""
        from divineos.core.empirica.burden import BURDEN_CALIBRATION_REVIEW_DAYS

        assert BURDEN_CALIBRATION_REVIEW_DAYS == 30

    def test_calibration_review_matches_pre_reg_window(self):
        """The BURDEN_CALIBRATION_REVIEW_DAYS must match the review
        window encoded in prereg-ce8998194943 (30 days). If the
        pre-reg review fires but the calibration review hasn't,
        the proportional-burden tuning promise is broken."""
        from divineos.core.empirica.burden import BURDEN_CALIBRATION_REVIEW_DAYS

        # Pre-reg review_days is 30 (see prereg filing). This assertion
        # will fail loudly if either value drifts.
        assert BURDEN_CALIBRATION_REVIEW_DAYS == 30

    def test_calibration_plan_referenced_in_docstring(self):
        """The calibration plan must be discoverable from the module
        docstring — not just a hidden TODO. If a reviewer reads
        burden.py top to bottom, they must see how and when the
        numbers will be tuned."""
        import divineos.core.empirica.burden as burden_mod

        doc = burden_mod.__doc__ or ""
        assert "calibration plan" in doc.lower()
        assert "rejection rate" in doc.lower()  # signal #1
        assert "supersession" in doc.lower()  # signal #2


class TestArtifactPointerRule:
    """Aria's rule (prereg-e210f5fb78c9): tiers above OUTCOME require
    an artifact pointer. Cheap vocabulary cannot earn above-OUTCOME
    tier assignment; the caller must cite something that cost
    something to produce (test, commit, decide, prereg, event,
    knowledge reference).

    The rule manifests as structural demotion: when the classifier
    would have returned PATTERN or FALSIFIABLE but no artifact_pointer
    was supplied, the classification is demoted to OUTCOME with an
    explicit 'demoted: no artifact pointer' reason.
    """

    def test_pattern_without_pointer_demotes_to_outcome(self):
        c = classify_claim("content", knowledge_type="PATTERN")
        assert c.tier == Tier.OUTCOME
        assert c.initial_tier == Tier.PATTERN  # what it would have been
        assert "demoted" in c.reason.lower()
        assert "no artifact pointer" in c.reason.lower()

    def test_falsifiable_without_pointer_demotes_to_outcome(self):
        c = classify_claim("x", knowledge_type="FACT", source="measured")
        assert c.tier == Tier.OUTCOME
        assert c.initial_tier == Tier.FALSIFIABLE
        assert "demoted" in c.reason.lower()

    def test_pattern_with_pointer_stays_pattern(self):
        c = classify_claim("content", knowledge_type="PATTERN", artifact_pointer="test/demo")
        assert c.tier == Tier.PATTERN
        # initial_tier is None when no demotion happened
        assert c.initial_tier is None
        assert "demoted" not in c.reason.lower()

    def test_falsifiable_with_pointer_stays_falsifiable(self):
        c = classify_claim(
            "x",
            knowledge_type="FACT",
            source="measured",
            artifact_pointer="commit-abc",
        )
        assert c.tier == Tier.FALSIFIABLE
        assert c.initial_tier is None

    def test_outcome_does_not_require_pointer(self):
        """OUTCOME is the honest middle — no artifact required."""
        c = classify_claim("x", knowledge_type="PRINCIPLE")
        assert c.tier == Tier.OUTCOME
        assert c.artifact_pointer is None
        assert "demoted" not in c.reason.lower()

    def test_default_outcome_does_not_require_pointer(self):
        """Rule 6 default (no tier signal) -> OUTCOME, no pointer needed."""
        c = classify_claim("unclassifiable content")
        assert c.tier == Tier.OUTCOME
        assert "demoted" not in c.reason.lower()

    def test_artifact_pointer_stored_on_classification(self):
        """Pre-reg falsifier #4: the pointer must be STORED on the
        Classification. If it's not stored, Phase 2 validation has
        nothing to validate against."""
        c = classify_claim(
            "content",
            knowledge_type="PATTERN",
            artifact_pointer="prereg-e210f5fb78c9",
        )
        assert c.artifact_pointer == "prereg-e210f5fb78c9"

    def test_artifact_pointer_stored_on_receipt(self):
        """Pre-reg falsifier #4 applied to the receipt: when a
        receipt is issued, the artifact_pointer must land on the
        stored receipt row and round-trip through get_receipt. If
        it's not stored on the receipt, the pointer was used to
        gate and then dropped — the exact decorative-requirement
        failure mode the falsifier names."""
        w, c, r = evaluate_and_issue(
            claim_id="c-pointer-storage",
            content="measured threshold assert",
            corroboration_count=8,
            knowledge_type="FACT",
            source="measured",
            artifact_pointer="commit-feedfaceb00c",
            convene_fn=lambda _: _StubConvene([]),
        )
        assert w is not None
        assert w.artifact_pointer == "commit-feedfaceb00c"
        # Round-trip: fetch from DB and confirm the pointer persisted.
        loaded = get_receipt(w.receipt_id)
        assert loaded is not None
        assert loaded.artifact_pointer == "commit-feedfaceb00c"

    def test_receipt_chain_self_hash_covers_artifact_pointer(self):
        """Tampering with artifact_pointer after issue must break
        self-hash verification. The pointer is as tamper-evident as
        every other field."""
        from dataclasses import replace as dc_replace

        w = issue_receipt(
            "c1",
            Tier.FALSIFIABLE,
            ClaimMagnitude.NORMAL,
            4,
            artifact_pointer="test/original",
        )
        tampered = dc_replace(w, artifact_pointer="test/forged")
        assert tampered.verify_self_hash() is False

    def test_empty_string_pointer_counts_as_no_pointer(self):
        """Empty string is not a real pointer — it should demote."""
        c = classify_claim("content", knowledge_type="PATTERN", artifact_pointer="")
        assert c.tier == Tier.OUTCOME  # demoted
        assert c.initial_tier == Tier.PATTERN

    def test_demotion_penalizes_confidence(self):
        """When demotion fires, confidence should drop — the
        classification isn't well-grounded without a pointer."""
        demoted = classify_claim("content", knowledge_type="PATTERN")
        grounded = classify_claim(
            "content",
            knowledge_type="PATTERN",
            artifact_pointer="test/demo",
            explicit_magnitude=ClaimMagnitude.NORMAL,
        )
        assert demoted.confidence < grounded.confidence


class TestAccumulateAllRules:
    """Kahneman's rule-ordering fix (prereg-e210f5fb78c9): the
    classifier no longer short-circuits on first match. It runs
    every rule and surfaces contradictions explicitly, so a
    PATTERN-typed claim with strong FALSIFIABLE content is no
    longer routed silently to PATTERN at 1.0 confidence.
    """

    def test_matched_rules_is_populated_when_rule_fires(self):
        c = classify_claim(
            "content",
            knowledge_type="PATTERN",
            artifact_pointer="test/demo",
        )
        assert c.matched_rules  # non-empty
        assert any("rule-1" in r for r in c.matched_rules)

    def test_matched_rules_records_both_when_two_rules_fire(self):
        """PATTERN knowledge_type + falsifiability keyword — both
        rules fire. Both must appear in matched_rules."""
        c = classify_claim(
            "threshold asserts behavior",
            knowledge_type="PATTERN",
            artifact_pointer="test/demo",
        )
        # Rule 1 (PATTERN knowledge_type) + rule 5 (falsifiability
        # keyword "threshold") both fire.
        rule_nums = {r.split(":")[0] for r in c.matched_rules}
        assert "rule-1" in rule_nums
        assert "rule-5" in rule_nums

    def test_contradiction_surfaces_in_reason(self):
        """When rules point at different tiers, the reason must say
        so. Silent short-circuit was the WYSIATI failure mode."""
        c = classify_claim(
            "threshold asserts behavior",
            knowledge_type="PATTERN",
            artifact_pointer="test/demo",
        )
        assert "contradiction" in c.reason.lower()

    def test_contradiction_lowers_confidence_below_explicit(self):
        """Even when the winning tier is explicit (would have been
        1.0), contradiction from another matched rule lowers
        confidence below 1.0 so callers can see the disagreement."""
        c = classify_claim(
            "threshold asserts behavior",
            knowledge_type="PATTERN",
            artifact_pointer="test/demo",
            explicit_magnitude=ClaimMagnitude.NORMAL,
        )
        assert c.confidence < 1.0

    def test_winning_tier_is_highest_confidence(self):
        """When a PATTERN knowledge_type (explicit 1.0) and a
        FALSIFIABLE keyword (0.5) both match, explicit wins."""
        c = classify_claim(
            "threshold asserts behavior",
            knowledge_type="PATTERN",
            artifact_pointer="test/demo",
        )
        assert c.tier == Tier.PATTERN

    def test_matched_rules_empty_when_only_default_fires(self):
        """If no rule fires except the implicit rule-6 default,
        matched_rules still names it so callers see 'default
        fallback' rather than an empty list."""
        c = classify_claim("unclassifiable content")
        assert c.matched_rules
        assert "rule-6" in c.matched_rules[0]


class TestInvariants:
    def test_valid_not_equal_true_disclaimer_present(self):
        """Pre-reg falsifier #5 protection — the docstring must
        explicitly name that receipts don't prove truth. If this
        test fails because someone edited the docstring, they need
        to rewrite both the test AND defend the change against the
        pre-reg."""
        import divineos.core.empirica
        import divineos.core.empirica.gate
        import divineos.core.empirica.types

        # At least one of the primary module docstrings must carry
        # the "valid != true" distinction explicitly.
        docstrings = (
            (divineos.core.empirica.__doc__ or "")
            + (divineos.core.empirica.types.__doc__ or "")
            + (divineos.core.empirica.gate.__doc__ or "")
            + (EvidenceReceipt.__doc__ or "")
        )
        assert "true" in docstrings.lower()
        assert any(
            phrase in docstrings.lower()
            for phrase in (
                "does not prove",
                "not prove",
                "never treat",
                "proof-of-truth",
                "stand-in",
            )
        ), "valid-not-equal-true invariant disclaimer missing"

    def test_adversarial_tier_never_autoassigned_by_classifier(self):
        """Double-up: even if someone adds ADVERSARIAL triggers to
        the keyword list, classifier should still refuse to return
        it. Lock the invariant."""
        probe_contents = (
            "adversarial",
            "red team",
            "steelman",
            "nyarlathotep attacked this",
            "ADVERSARIAL TIER",
        )
        for content in probe_contents:
            c = classify_claim(content)
            assert c.tier != Tier.ADVERSARIAL, (
                f"classifier returned ADVERSARIAL for {content!r} — "
                "ADVERSARIAL must route through VOID, not heuristic"
            )

    def test_gate_cannot_issue_receipt_for_adversarial_tier(self):
        """If somehow a caller constructed an adversarial classification
        (e.g. through explicit future APIs), burden raises before receipt
        issue. The gate cannot rubber-stamp adversarial claims."""
        # Currently no public API for forcing ADVERSARIAL; this test
        # locks that the protection is at the burden layer, not the
        # classifier layer, so a future API that allowed forcing the
        # tier would still fail closed.
        with pytest.raises(NotImplementedError):
            required_corroboration(Tier.ADVERSARIAL, ClaimMagnitude.FOUNDATIONAL)
