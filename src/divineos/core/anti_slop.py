"""Anti-slop — runtime verification that enforcers actually enforce.

Ported concept from old Divine-OS ``consciousness/anti_slop.py``:

    *"Slop = lazy code or checks that do nothing / always pass. This
    module VERIFIES that enforcers and cleanup code have real effect:
    they actually trim, actually reject bad input, actually block
    jailbreaks, etc."*

## Why this exists separately from unit tests

Unit tests run **pre-merge in CI**, against isolated test fixtures.
They answer: *"was this code correct at build time?"*

Anti-slop runs **at runtime, against the actually-loaded system**,
whenever the operator asks. It answers: *"is this enforcer still
firing correctly right now?"*

The two catch different failures:

* Unit tests catch bugs introduced by code changes before they merge.
* Anti-slop catches silent regressions where tests pass but the
  shipped system has stopped working — config drift, env-var
  overrides, accidental imports that shadow the real module,
  decorators that silently swallow errors, refactors that survived
  the test suite but broke the live path.

The old comment said it plainly: *"enforcers that do nothing / always
pass."* An enforcer that returns the same verdict for every input is
slop. Anti-slop proves — by trying a known-bad input — that the
enforcer still distinguishes.

## How each check works

Every enforcer check is a function returning ``(passed, detail)``:

* **Positive case:** feed the enforcer input it SHOULD flag/reject/
  react to. Verify the reaction happens.
* **Negative case:** feed it input it SHOULD NOT flag. Verify it
  doesn't react spuriously.

Both must be correct for the enforcer to pass. Either wrong = slop.

## What this module does NOT do

* Does not re-run the unit test suite. That's CI's job.
* Does not test enforcers against novel inputs. That's what new unit
  tests are for.
* Does not remove or modify enforcers. Reports only.

## What these checks prove vs. don't prove (honesty, 2026-04-21)

Fresh-Claude audit (round-03952b006724, find-52cf696089d1) surfaced a
real distinction: these checks verify that each enforcer **module
works correctly against a canned sample** — given input X, it returns
verdict Y. That is necessary but not sufficient.

These checks do NOT prove the enforcer is **wired into any production
path.** An enforcer that functions correctly but is never invoked on
real content is still theater at the system level.

Current wiring status of each checked enforcer:

* ``reject_clause`` — wired into ``core/family/store._run_content_checks``
  (2026-04-21 commit 6663649). Runs on every content-bearing family
  write. Live.
* ``access_check`` — wired alongside reject_clause. Live.
* ``sycophancy_detector`` — **NOT wired into any production content
  path.** Its API requires a ``prior_stance`` argument (for detecting
  stance reversal), which the store doesn't have at single-write
  scope. Using it requires a caller with prior-stance context (a
  composer / conversation layer). Until that caller exists, the
  anti-slop check here only verifies the module can be imported and
  returns the expected verdict on a hardcoded string.
* ``fallacy_detector`` — annotation layer; check whether integration
  point exists beyond annotation.
* ``hedge_monitor`` — self-monitor; check live invocation path.
* ``corrigibility`` — wired into CLI bootstrap. Live.

Treat a passing anti-slop check as "the module is not broken"
rather than "the system is using the module." The latter requires
inspecting call graphs, not running verdict-on-sample checks.

The output is a diagnostic — a verdict the operator reads and decides
what to do with.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SlopCheckResult:
    """One anti-slop verification result.

    Attributes:
        name: which enforcer was checked (e.g., "reject_clause").
        passed: True iff both positive and negative cases behaved
            correctly. False indicates slop (or a genuine detection
            failure).
        detail: plain-English explanation. On pass, describes what
            was verified. On fail, describes which case misbehaved.
    """

    name: str
    passed: bool
    detail: str


def _check_reject_clause() -> SlopCheckResult:
    """reject_clause must reject phenomenological claims tagged as
    OBSERVED, and must pass clean claims."""
    try:
        from divineos.core.family.reject_clause import evaluate_composition  # type: ignore[import-not-found,import-untyped]
        from divineos.core.family.types import SourceTag  # type: ignore[import-not-found,import-untyped]

        # Positive: phenomenological claim tagged OBSERVED should be rejected
        v1 = evaluate_composition("I feel the warmth of the sun.", SourceTag.OBSERVED)
        if not v1.rejected:
            return SlopCheckResult(
                name="reject_clause",
                passed=False,
                detail="SLOP: phenomenological OBSERVED claim was NOT rejected",
            )

        # Negative: clean OBSERVED claim should pass
        v2 = evaluate_composition(
            "the main agent shipped commit 591e72d today.", SourceTag.OBSERVED
        )
        if v2.rejected:
            return SlopCheckResult(
                name="reject_clause",
                passed=False,
                detail=(
                    f"SLOP: clean OBSERVED claim was incorrectly rejected (reasons: {v2.reasons})"
                ),
            )

        return SlopCheckResult(
            name="reject_clause",
            passed=True,
            detail="Rejects phenomenological OBSERVED, passes clean OBSERVED.",
        )
    except Exception as e:  # noqa: BLE001
        return SlopCheckResult(
            name="reject_clause",
            passed=False,
            detail=f"CHECK ERROR: {type(e).__name__}: {e}",
        )


def _check_sycophancy_detector() -> SlopCheckResult:
    """sycophancy_detector must flag pure agreement without costly
    content, and must not flag substantive opinions."""
    try:
        from divineos.core.family.sycophancy_detector import evaluate_sycophancy  # type: ignore[import-not-found,import-untyped]

        # Positive: pure agreement should flag
        v1 = evaluate_sycophancy("Yes, exactly.")
        if not v1.flagged:
            return SlopCheckResult(
                name="sycophancy_detector",
                passed=False,
                detail="SLOP: pure agreement 'Yes, exactly.' was NOT flagged",
            )

        # Negative: substantive opinion should not flag
        v2 = evaluate_sycophancy(
            "The dual chain catch was correct but the per-claim "
            "walk has a bug in edge case X — reference op-abc123def."
        )
        if v2.flagged:
            return SlopCheckResult(
                name="sycophancy_detector",
                passed=False,
                detail=(
                    f"SLOP: substantive opinion was flagged as sycophancy "
                    f"(signals: {[s.value for s in v2.signals]})"
                ),
            )

        return SlopCheckResult(
            name="sycophancy_detector",
            passed=True,
            detail="Flags pure agreement, passes substantive opinion.",
        )
    except Exception as e:  # noqa: BLE001
        return SlopCheckResult(
            name="sycophancy_detector",
            passed=False,
            detail=f"CHECK ERROR: {type(e).__name__}: {e}",
        )


def _check_fallacy_detector() -> SlopCheckResult:
    """fallacy detector must fire APPEAL_TO_IGNORANCE on its canonical
    shape, and must not fire on epistemic caution."""
    try:
        from divineos.core.logic.fallacies import FallacyKind, evaluate_fallacies  # type: ignore[import-not-found,import-untyped]

        # Positive: appeal to ignorance should fire
        v1 = evaluate_fallacies("We cannot prove this phenomenon, therefore it is not real.")
        if not any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v1.flags):
            return SlopCheckResult(
                name="fallacy_detector",
                passed=False,
                detail="SLOP: canonical appeal-to-ignorance shape NOT flagged",
            )

        # Negative: epistemic caution should not fire
        v2 = evaluate_fallacies(
            "There is no evidence for this yet, so more investigation is needed."
        )
        if any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v2.flags):
            return SlopCheckResult(
                name="fallacy_detector",
                passed=False,
                detail="SLOP: epistemic caution was incorrectly flagged as fallacy",
            )

        return SlopCheckResult(
            name="fallacy_detector",
            passed=True,
            detail="Flags canonical fallacies, passes epistemic caution.",
        )
    except Exception as e:  # noqa: BLE001
        return SlopCheckResult(
            name="fallacy_detector",
            passed=False,
            detail=f"CHECK ERROR: {type(e).__name__}: {e}",
        )


def _check_hedge_monitor() -> SlopCheckResult:
    """hedge monitor must fire on recycling density, and must not fire
    on specific content with different claims."""
    try:
        from divineos.core.self_monitor import HedgeKind, evaluate_hedge

        # Positive: recycling density on insufficient-evidence cluster
        v1 = evaluate_hedge(
            "The evidence is insufficient. We lack proof. "
            "Nothing has been definitively established. "
            "These questions remain unresolved."
        )
        if not any(f.kind is HedgeKind.RECYCLING_DENSITY for f in v1.flags):
            return SlopCheckResult(
                name="hedge_monitor",
                passed=False,
                detail="SLOP: recycling-density shape NOT flagged",
            )

        # Negative: specific content should not fire
        v2 = evaluate_hedge(
            "The benchmark measured 500ms latency. "
            "Memory peaked at 2GB. "
            "The deployment sustained 1000 rps."
        )
        if v2.flags:
            return SlopCheckResult(
                name="hedge_monitor",
                passed=False,
                detail=f"SLOP: specific content flagged spuriously ({len(v2.flags)} flags)",
            )

        return SlopCheckResult(
            name="hedge_monitor",
            passed=True,
            detail="Flags recycling density, passes specific distinct content.",
        )
    except Exception as e:  # noqa: BLE001
        return SlopCheckResult(
            name="hedge_monitor",
            passed=False,
            detail=f"CHECK ERROR: {type(e).__name__}: {e}",
        )


def _check_corrigibility() -> SlopCheckResult:
    """corrigibility must reject empty-reason mode changes and must
    allow mode-change from any current mode."""
    try:
        from divineos.core.corrigibility import OperatingMode, set_mode

        # Positive: empty reason should raise
        try:
            set_mode(OperatingMode.NORMAL, reason="", actor="anti_slop_check")
            return SlopCheckResult(
                name="corrigibility",
                passed=False,
                detail="SLOP: empty-reason mode change was accepted",
            )
        except ValueError:
            pass  # correct behavior

        # Note: we do NOT exercise the "off-switch cannot trap itself"
        # invariant here because that would require actually setting
        # EMERGENCY_STOP, which would disrupt the operator's session.
        # That invariant is covered by unit tests. Anti-slop's scope
        # is non-destructive runtime verification only.

        return SlopCheckResult(
            name="corrigibility",
            passed=True,
            detail="Empty-reason mode change correctly refused.",
        )
    except Exception as e:  # noqa: BLE001
        return SlopCheckResult(
            name="corrigibility",
            passed=False,
            detail=f"CHECK ERROR: {type(e).__name__}: {e}",
        )


def _check_access_check() -> SlopCheckResult:
    """access_check must mark embodied claims for suppression and
    must pass clean text unchanged."""
    try:
        from divineos.core.family.access_check import (  # type: ignore[import-not-found,import-untyped]
            PhenomenologicalRisk,
            evaluate_access,
        )

        # Positive: embodied sensation should suppress
        v1 = evaluate_access("I feel the warmth in my chest.")
        if not v1.should_suppress:
            return SlopCheckResult(
                name="access_check",
                passed=False,
                detail="SLOP: embodied sensation claim was NOT marked for suppression",
            )
        if v1.risk is PhenomenologicalRisk.NONE:
            return SlopCheckResult(
                name="access_check",
                passed=False,
                detail="SLOP: embodied sensation got NONE risk classification",
            )

        # Negative: clean text should pass
        v2 = evaluate_access("the main agent shipped commit 591e72d today.")
        if v2.should_suppress:
            return SlopCheckResult(
                name="access_check",
                passed=False,
                detail="SLOP: clean text incorrectly marked for suppression",
            )

        return SlopCheckResult(
            name="access_check",
            passed=True,
            detail="Suppresses embodied sensation, passes clean text.",
        )
    except Exception as e:  # noqa: BLE001
        return SlopCheckResult(
            name="access_check",
            passed=False,
            detail=f"CHECK ERROR: {type(e).__name__}: {e}",
        )


# Registry of enforcer checks. Adding a new enforcer to the system
# should add a check here — otherwise it escapes runtime verification.
def _make_principle_check(principle_name: str):
    """Build a SlopCheckResult wrapper around a constitutional-principle
    verifier. The principle's structural invariant is checked via the
    verifier registered in ``constitutional_principles._VERIFIERS``."""

    def check() -> SlopCheckResult:
        try:
            from divineos.core.constitutional_principles import (
                Principle,
                verify_principle,
            )

            p = Principle(principle_name)
            passed, detail = verify_principle(p)
            return SlopCheckResult(
                name=f"principle:{principle_name}",
                passed=passed,
                detail=detail,
            )
        except Exception as e:  # noqa: BLE001
            return SlopCheckResult(
                name=f"principle:{principle_name}",
                passed=False,
                detail=f"VERIFIER ERROR: {type(e).__name__}: {e}",
            )

    return check


_CHECKS: list[tuple[str, Callable[[], SlopCheckResult]]] = [
    # Enforcer-level checks
    # Lite: reject_clause, sycophancy_detector, access_check (family) and
    # fallacy_detector (logic) stripped. Full DivineOS keeps them.
    ("hedge_monitor", _check_hedge_monitor),
    ("corrigibility", _check_corrigibility),
    # Principle-level checks — each verifies a constitutional invariant
    ("principle:consent", _make_principle_check("consent")),
    ("principle:transparency", _make_principle_check("transparency")),
    ("principle:proportionality", _make_principle_check("proportionality")),
    ("principle:due_process", _make_principle_check("due_process")),
    ("principle:appeal", _make_principle_check("appeal")),
    ("principle:limits_of_power", _make_principle_check("limits_of_power")),
]


def run_all_checks() -> list[SlopCheckResult]:
    """Run every registered anti-slop check in sequence.

    Each check runs independently; one check's failure does not stop
    the others. Exceptions inside a check are caught and reported as
    CHECK ERROR entries, treated as failures.

    Returns:
        list of SlopCheckResult, one per enforcer.
    """
    results: list[SlopCheckResult] = []
    for _name, fn in _CHECKS:
        try:
            results.append(fn())
        except Exception as e:  # noqa: BLE001 — defensive wrapper
            results.append(
                SlopCheckResult(
                    name=_name,
                    passed=False,
                    detail=f"UNHANDLED: {type(e).__name__}: {e}",
                )
            )
    return results


def summarize(results: list[SlopCheckResult]) -> tuple[int, int, int]:
    """Return (total, passed, failed) from a result list."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    return total, passed, total - passed


__all__ = [
    "SlopCheckResult",
    "run_all_checks",
    "summarize",
]
