"""Tests for the confidence_basis fix — closes Aletheia's 2026-05-12 dogfood
finding that 108 of 109 claims (grown to 202 of 203 by 2026-06-06) were
stuck at default confidence 0.5 because there was no path to encode a
filer's prior or an assessor's judgment without quantified evidence.

The fix distinguishes uncommitted defaults from real credences via a
confidence_basis column. These tests pin the four required behaviors:

  1. file_claim() with no confidence → basis='uncommitted'
  2. file_claim(confidence=X, basis_text=Y) → basis='filer-prior'
  3. set_claim_confidence_judgment() → basis='assessor-judgment'
  4. add_evidence() → basis='evidence-derived' via recalculate

And the structural guard:

  5. confidence without basis_text raises ValueError (the 'no naked credences' rule)
"""

from __future__ import annotations

import pytest

from divineos.core.claim_store import (
    BASIS_ASSESSOR_JUDGMENT,
    BASIS_EVIDENCE_DERIVED,
    BASIS_FILER_PRIOR,
    BASIS_LEGACY_DEFAULT,
    BASIS_UNCOMMITTED,
    TIER_THEORETICAL,
    add_evidence,
    file_claim,
    get_claim,
    list_uncommitted_claims,
    set_claim_confidence_judgment,
)


class TestConfidenceBasisOnFile:
    """Filing path: with/without confidence → correct basis stored."""

    def test_file_without_confidence_is_uncommitted(self) -> None:
        cid = file_claim("Test: bare filing is uncommitted", tier=TIER_THEORETICAL)
        claim = get_claim(cid)
        assert claim is not None
        # Storage default stays 0.5 for backward compat with existing readers,
        # but basis distinguishes it from a held 0.5 credence.
        assert claim["confidence"] == 0.5
        assert claim["confidence_basis"] == BASIS_UNCOMMITTED
        assert claim["confidence_basis_text"] == ""
        assert claim["confidence_set_at"] is None

    def test_file_with_confidence_and_basis_is_filer_prior(self) -> None:
        cid = file_claim(
            "Test: explicit prior records filer-prior",
            tier=TIER_THEORETICAL,
            confidence=0.7,
            confidence_basis_text="analogous-case prior from earlier similar claim",
        )
        claim = get_claim(cid)
        assert claim is not None
        assert claim["confidence"] == 0.7
        assert claim["confidence_basis"] == BASIS_FILER_PRIOR
        assert "analogous-case" in claim["confidence_basis_text"]
        assert claim["confidence_set_at"] is not None

    def test_file_with_confidence_without_basis_raises(self) -> None:
        with pytest.raises(ValueError, match="basis"):
            file_claim(
                "Test: bare confidence is rejected",
                tier=TIER_THEORETICAL,
                confidence=0.8,
                confidence_basis_text="",
            )

    def test_file_with_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
            file_claim(
                "Test: out-of-range confidence is rejected",
                tier=TIER_THEORETICAL,
                confidence=1.5,
                confidence_basis_text="should never reach storage",
            )


class TestAssessorJudgmentPath:
    """set_claim_confidence_judgment: assessor-judgment basis is written."""

    def test_judgment_override_writes_assessor_basis(self) -> None:
        cid = file_claim("Test: judgment overrides start-uncommitted", tier=TIER_THEORETICAL)
        set_claim_confidence_judgment(
            cid, 0.85, "structural framework match: this fits the X pattern"
        )
        claim = get_claim(cid)
        assert claim is not None
        assert claim["confidence"] == 0.85
        assert claim["confidence_basis"] == BASIS_ASSESSOR_JUDGMENT
        assert "framework match" in claim["confidence_basis_text"]

    def test_judgment_supports_prefix_id(self) -> None:
        cid = file_claim("Test: prefix-id resolution for assess", tier=TIER_THEORETICAL)
        prefix = cid[:8]
        set_claim_confidence_judgment(prefix, 0.6, "smoke-test of prefix resolution")
        claim = get_claim(cid)
        assert claim is not None
        assert claim["confidence"] == 0.6
        assert claim["confidence_basis"] == BASIS_ASSESSOR_JUDGMENT

    def test_judgment_without_basis_raises(self) -> None:
        cid = file_claim("Test: judgment requires basis", tier=TIER_THEORETICAL)
        with pytest.raises(ValueError, match="basis"):
            set_claim_confidence_judgment(cid, 0.7, "")

    def test_judgment_unknown_id_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            set_claim_confidence_judgment("does-not-exist", 0.5, "should never reach")


class TestEvidenceDerivedBasis:
    """Evidence-add path: recalculate writes evidence-derived basis."""

    def test_evidence_add_sets_evidence_derived_basis(self) -> None:
        cid = file_claim("Test: evidence recalculation writes basis", tier=TIER_THEORETICAL)
        # Pre-evidence: uncommitted
        assert get_claim(cid)["confidence_basis"] == BASIS_UNCOMMITTED
        # Add supporting evidence
        add_evidence(cid, "supporting evidence content", direction="SUPPORTS", strength=0.8)
        claim = get_claim(cid)
        assert claim is not None
        # Recalculated: only supporting evidence → confidence approaches 1.0
        assert claim["confidence"] > 0.5
        assert claim["confidence_basis"] == BASIS_EVIDENCE_DERIVED
        assert "support" in claim["confidence_basis_text"].lower()


class TestUncommittedSurface:
    """list_uncommitted_claims surfaces the gap."""

    def test_uncommitted_surface_finds_uncommitted(self) -> None:
        cid = file_claim("Test: surface includes uncommitted", tier=TIER_THEORETICAL)
        uncommitted = list_uncommitted_claims(limit=500, include_legacy=False)
        ids = {c["claim_id"] for c in uncommitted}
        assert cid in ids

    def test_uncommitted_surface_excludes_committed(self) -> None:
        # Filer-prior → not uncommitted
        cid_prior = file_claim(
            "Test: filer-prior is NOT uncommitted",
            tier=TIER_THEORETICAL,
            confidence=0.65,
            confidence_basis_text="explicit prior",
        )
        # Assessor-judgment → not uncommitted
        cid_judg = file_claim("Test: post-judgment is NOT uncommitted", tier=TIER_THEORETICAL)
        set_claim_confidence_judgment(cid_judg, 0.9, "expert framework match")

        uncommitted = list_uncommitted_claims(limit=500, include_legacy=False)
        ids = {c["claim_id"] for c in uncommitted}
        assert cid_prior not in ids
        assert cid_judg not in ids

    def test_uncommitted_surface_includes_legacy_default_by_default(self) -> None:
        # The surface should accept legacy-default rows as part of the gap.
        # Empty result is fine on a fresh DB; on a real substrate the set is
        # bases ⊆ {uncommitted, legacy-default}.
        all_uncommitted = list_uncommitted_claims(limit=500, include_legacy=True)
        bases = {c["confidence_basis"] for c in all_uncommitted}
        assert bases.issubset({BASIS_UNCOMMITTED, BASIS_LEGACY_DEFAULT})


class TestBackwardCompatibility:
    """The fix preserves existing reader contracts."""

    def test_existing_confidence_field_still_present(self) -> None:
        cid = file_claim("Test: existing readers still see 'confidence' key", tier=TIER_THEORETICAL)
        claim = get_claim(cid)
        assert "confidence" in claim
        assert isinstance(claim["confidence"], float)

    def test_new_basis_fields_present(self) -> None:
        cid = file_claim("Test: new basis fields surface in row dict", tier=TIER_THEORETICAL)
        claim = get_claim(cid)
        assert "confidence_basis" in claim
        assert "confidence_basis_text" in claim
        assert "confidence_set_at" in claim
