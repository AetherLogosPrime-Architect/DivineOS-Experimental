"""Tests for constitutional_principles and its integration with anti-slop.

Locked invariants:

1. All six principles defined with summary + invariant strings.
2. Each has a registered verifier.
3. Verifier for each principle returns (bool, str) without exception
   on the current healthy codebase.
4. anti-slop registers all six principle checks.
5. Principle enum values are stable (persisted → must not drift).
"""

from __future__ import annotations

from divineos.core.constitutional_principles import (
    Principle,
    PrincipleDefinition,
    all_principles,
    get_principle,
    verify_all_principles,
    verify_principle,
)


class TestPrincipleEnum:
    def test_six_principles_defined(self):
        assert len(list(Principle)) == 6

    def test_values_stable(self):
        """Values are persisted in ledger/records — must not drift."""
        assert Principle.CONSENT.value == "consent"
        assert Principle.TRANSPARENCY.value == "transparency"
        assert Principle.PROPORTIONALITY.value == "proportionality"
        assert Principle.DUE_PROCESS.value == "due_process"
        assert Principle.APPEAL.value == "appeal"
        assert Principle.LIMITS_OF_POWER.value == "limits_of_power"


class TestPrincipleDefinitions:
    def test_all_principles_have_definitions(self):
        defs = all_principles()
        assert len(defs) == 6
        for d in defs:
            assert isinstance(d, PrincipleDefinition)
            assert d.summary
            assert d.invariant

    def test_get_principle_returns_definition(self):
        d = get_principle(Principle.CONSENT)
        assert isinstance(d, PrincipleDefinition)
        assert d.principle is Principle.CONSENT
        assert "agreement" in d.summary.lower() or "consent" in d.summary.lower()

    def test_definition_is_frozen(self):
        import pytest

        d = get_principle(Principle.CONSENT)
        with pytest.raises((AttributeError, Exception)):
            d.summary = "different"  # type: ignore[misc]


class TestVerifiers:
    """Each principle has a registered verifier. Each verifier returns
    a (bool, str) tuple without raising on the healthy codebase."""

    def test_verify_principle_returns_tuple(self):
        for p in Principle:
            result = verify_principle(p)
            assert isinstance(result, tuple)
            assert len(result) == 2
            passed, detail = result
            assert isinstance(passed, bool)
            assert isinstance(detail, str)
            assert detail  # must be non-empty

    def test_verify_all_returns_one_per_principle(self):
        results = verify_all_principles()
        assert len(results) == 6
        principles_seen = {r[0] for r in results}
        assert principles_seen == set(Principle)

    def test_all_verifiers_pass_on_healthy_codebase(self):
        """Critical: on the current healthy codebase, every principle
        verifier must pass. If this starts failing, a principle has
        lost its structural grounding."""
        results = verify_all_principles()
        failures = [(p, d) for p, passed, d in results if not passed]
        assert not failures, (
            f"{len(failures)} principle(s) failed structural verification: {failures}"
        )


class TestAntiSlopIntegration:
    """anti-slop must register all six principle checks."""

    def test_anti_slop_includes_all_principles(self):
        from divineos.core.anti_slop import run_all_checks

        results = run_all_checks()
        names = {r.name for r in results}
        for p in Principle:
            assert f"principle:{p.value}" in names, (
                f"principle:{p.value} missing from anti-slop — "
                f"adding a principle without a check is a coverage gap"
            )

    def test_all_principle_checks_pass_in_anti_slop(self):
        from divineos.core.anti_slop import run_all_checks

        results = run_all_checks()
        principle_results = [r for r in results if r.name.startswith("principle:")]
        failures = [(r.name, r.detail) for r in principle_results if not r.passed]
        assert not failures, f"{len(failures)} principle(s) failed anti-slop check: {failures}"


class TestIndividualInvariants:
    """Lock each invariant against regression. If any of these fires,
    the corresponding structural property has broken."""

    def test_consent_hook_exists(self):
        passed, detail = verify_principle(Principle.CONSENT)
        assert passed, detail

    def test_transparency_ledger_queryable(self):
        passed, detail = verify_principle(Principle.TRANSPARENCY)
        assert passed, detail

    def test_proportionality_monotonic(self):
        passed, detail = verify_principle(Principle.PROPORTIONALITY)
        assert passed, detail

    def test_due_process_prereg_with_falsifiers(self):
        passed, detail = verify_principle(Principle.DUE_PROCESS)
        assert passed, detail

    def test_appeal_supersession_present(self):
        passed, detail = verify_principle(Principle.APPEAL)
        assert passed, detail

    def test_limits_of_power_off_switch_cannot_trap(self):
        passed, detail = verify_principle(Principle.LIMITS_OF_POWER)
        assert passed, detail
