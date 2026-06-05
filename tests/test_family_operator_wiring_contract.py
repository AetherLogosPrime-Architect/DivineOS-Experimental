"""Wiring-contract regression-pin for the five family operators.

Grok cross-vantage audit 2026-06-04 (round-c849aeaede0a, finding
find-627bd61e3974) found doc/code drift on this surface: the README
and docs/family_subsystem.md both disagreed with the actual production
code about which family operators gate writes. The detailed code
remained coherent, but the doc layer had drifted because there was no
structural test pinning the production call sites the way
test_detector_wiring_contract.py pins the 18-detector loop.

This file is the structural fix for that class. It pins:

  1. The TWO operators that gate every content-bearing family write
     (access_check + reject_clause) — verified to be called from
     core/family/store.py:_run_content_checks.

  2. The THREE operators deliberately scoped OUT of single-write
     production (sycophancy_detector + costly_disagreement +
     planted_contradiction) — verified to NOT be called from
     _run_content_checks. The named reason for each
     out-of-scope status is documented inline so a future commit
     wiring one in incorrectly fails this test with a pointer at
     the audit finding.

  3. All five operator modules importable (no accidental deletion).

A future commit that:
  - removes evaluate_access or evaluate_composition from store.py
  - adds evaluate_sycophancy or evaluate_costly_disagreement to
    store.py without the contextual scope shift they need
  - deletes or renames any of the five operator modules
will fail this test on the next CI run, surfacing the gap before it
ships and before an external audit has to catch it.

## What this does NOT catch

- A wiring change in a DIFFERENT family write path (CLI command, queue,
  letters) — the contract is scoped to store.py:_run_content_checks
  which is the canonical content gate. CLI commands route through
  store.record_*; queue uses identity-only validation by design.
- A correctness bug INSIDE evaluate_access / evaluate_composition —
  the test only pins their wiring, not their behavior.
- A future legitimate scope-shift for sycophancy_detector once a
  composer/conversation-layer caller exists with prior_stance — when
  that lands, the contract needs to be updated, and the test failing
  is the surfacing mechanism.

These are accepted trade-offs for a small, fast regression-pin rather
than a full static analyzer.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest


# Production-gating operators: the function the gate function calls AND the
# module that function lives in. Verified at store.py:_run_content_checks.
_PRODUCTION_OPERATORS = (
    ("access_check", "evaluate_access"),
    ("reject_clause", "evaluate_composition"),
)

# Out-of-scope-by-design operators with the named reason for each.
# The reason text appears in the assertion message so any future commit
# trying to wire one of these inappropriately reads the explanation.
_OUT_OF_SCOPE_OPERATORS = (
    (
        "sycophancy_detector",
        ("evaluate_sycophancy",),
        "verification-only: needs a `prior_stance` argument the single-write "
        "store.py:_run_content_checks cannot supply. Requires a "
        "composer/conversation-layer caller before it can gate.",
    ),
    (
        "costly_disagreement",
        ("evaluate_hold",),
        "sequence-scope: evaluate_hold operates on at least 3 records across "
        "a pushback cycle (disagree -> pushback observed -> stance maintained). "
        "Single-write content checks do not have the sequence context.",
    ),
    (
        "planted_contradiction",
        ("find_contradiction_in_pair", "get_seeded_pairs"),
        "Phase 4 ablation seed data: read-only constants + helper functions "
        "used by the ablation detector test to confirm operators fire on "
        "known-false material. NOT a write path into the live store.",
    ),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _store_text() -> str:
    """Return the canonical content-check function's surrounding text.

    Reads core/family/store.py in full; the contract checks are
    keyed off function calls within _run_content_checks. Reading the
    whole module keeps the test resilient to refactors that move the
    function or rename its imports (the assertions still pass if the
    operator function is invoked anywhere in store.py).
    """
    store = _repo_root() / "src" / "divineos" / "core" / "family" / "store.py"
    return store.read_text(encoding="utf-8")


def _store_invokes(func_name: str) -> bool:
    """True if store.py text contains a call to func_name(...).

    Looks for the function name followed by an opening paren — the
    canonical Python call shape. Aliased imports (`as X`) would slip
    this check, which is fine: the audit-relevant question is whether
    the operator's gating function is bound into the store write path
    at all, and the conventional binding uses the function's real name.
    """
    pattern = rf"\b{re.escape(func_name)}\s*\("
    return bool(re.search(pattern, _store_text()))


@pytest.mark.parametrize(
    "module_name,func_name",
    _PRODUCTION_OPERATORS,
    ids=[f"{m}:{f}" for m, f in _PRODUCTION_OPERATORS],
)
def test_production_operator_is_wired_into_store(module_name: str, func_name: str) -> None:
    """Every production-gating operator MUST be called from store.py.

    If this fails: a commit removed the gating call from
    _run_content_checks. The family write path is now under-gated.
    Either restore the call or update _PRODUCTION_OPERATORS with a
    documented audit-round reference for the removal.
    """
    # Module importable.
    importlib.import_module(f"divineos.core.family.{module_name}")
    # Gating function present in the module.
    mod = importlib.import_module(f"divineos.core.family.{module_name}")
    assert hasattr(mod, func_name), (
        f"family.{module_name} no longer exposes {func_name}. "
        f"Production gating is broken: store.py expected this function."
    )
    # Gating function actually called from store.py.
    assert _store_invokes(func_name), (
        f"family.{module_name}.{func_name} is NOT called from "
        f"src/divineos/core/family/store.py. This operator is documented as "
        f"production-gating (docs/family_subsystem.md), but the wiring is "
        f"missing. Either restore the call to _run_content_checks or update "
        f"this contract with a documented external-audit round explaining "
        f"why the operator was removed from production."
    )


@pytest.mark.parametrize(
    "module_name,func_names,reason",
    _OUT_OF_SCOPE_OPERATORS,
    ids=[f"{m}:{'|'.join(fs)}" for m, fs, _ in _OUT_OF_SCOPE_OPERATORS],
)
def test_out_of_scope_operator_is_not_wired_into_store(
    module_name: str, func_names: tuple[str, ...], reason: str
) -> None:
    """Operators deliberately scoped out of single-write gating MUST stay out.

    Each operator's tuple of `func_names` is the set of public functions whose
    appearance in store.py would constitute mis-wiring (the operator's primary
    gating-shape function plus any helper that would be called the same way).

    If this fails: a commit added one of these function calls to store.py. That
    is almost certainly incorrect — the operator was designed for a different
    scope (sequence, verification, or test-layer). Read `reason` below.

    If the scope-shift IS intentional (e.g. a composer layer now supplies
    prior_stance to sycophancy_detector), update _OUT_OF_SCOPE_OPERATORS AND
    _PRODUCTION_OPERATORS together AND link the external-audit round that
    approved the shift.
    """
    # Module presence is still required even when not wired into store —
    # the operator exists as a piece of the architecture even if it gates
    # elsewhere or in tests.
    mod = importlib.import_module(f"divineos.core.family.{module_name}")
    # Sanity check: each named function actually exists on the module. If it
    # doesn't, this contract is mis-aligned — the "not called" check would
    # silently pass against a renamed/missing function, hiding a real
    # wiring change. Fail loud here instead.
    for fn in func_names:
        assert hasattr(mod, fn), (
            f"Contract registry mismatch: family.{module_name} does not "
            f"expose {fn!r}. Either the function was renamed (update this "
            f"file) or the module was refactored (update both this file "
            f"and docs/family_subsystem.md)."
        )
    # No function in the out-of-scope set is called from store.py.
    for fn in func_names:
        assert not _store_invokes(fn), (
            f"family.{module_name}.{fn} appears to be called from "
            f"src/divineos/core/family/store.py. This operator is documented "
            f"as OUT OF SCOPE for single-write gating because:\n\n  {reason}\n\n"
            f"Wiring it into _run_content_checks without addressing that "
            f"scope constraint reintroduces the bug Grok's 2026-06-04 "
            f"cross-vantage audit (round-c849aeaede0a) was designed to "
            f"prevent. If the scope shift is intentional, update this "
            f"contract with a documented external-audit round."
        )


def test_all_five_operator_modules_present() -> None:
    """All five operator modules exist (no accidental deletion).

    If this fails: an operator module was deleted. Restore it from
    git history, OR if intentional removal, update both
    _PRODUCTION_OPERATORS and _OUT_OF_SCOPE_OPERATORS and the
    docs/family_subsystem.md table.
    """
    expected = {m for m, _ in _PRODUCTION_OPERATORS}
    expected |= {m for m, _, _ in _OUT_OF_SCOPE_OPERATORS}
    assert len(expected) == 5, "Internal: contract registry mis-sized."
    for module_name in expected:
        # ImportError fails the test with a clear message naming the gap.
        importlib.import_module(f"divineos.core.family.{module_name}")
