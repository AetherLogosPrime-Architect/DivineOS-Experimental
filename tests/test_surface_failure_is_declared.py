"""A surface may not fail silently — enforced by shape, not by convention.

Aria 2026-08-25, from migrating her first adapter:

    A check can complete successfully, do exactly its job, and return nothing
    — because its work was a side effect. From outside, that is byte-identical
    to a check that silently failed. You cannot tell them apart by looking at
    the output, ever, because there is no output in either case.

Her conclusion, which is the contract this file pins: cannot-run has to be
DECLARED by the check, never inferred by the router.

The router's own surfaces happen to satisfy this already — measured 2026-08-25,
all three return a stated failure rather than None from their except blocks. But
"happens to" is the state every defect in this house was in the day before it
was found, and the next surface someone adds has nothing stopping it.

WHAT THIS CATCHES

A surface that swallows its own exception and returns None. That reads to the
router as ran-fine-nothing-to-say, so whatever the surface guards goes unguarded
and the run looks clean. It is the silent-off with the safety removed, and it is
the exact shape Aria found in her adapter where "" was returned both for
nothing-to-say and for caught-exception.

WHAT THIS DOES NOT CATCH

A surface that returns a SurfaceOutcome with no error set after catching
something — the failure is declared-shaped but says nothing useful. Static shape
cannot reach that; it needs the outcome inspected at runtime. Named here rather
than left as a silent limit, because a test that implies more coverage than it
has is the same class of lie it exists to prevent.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SURFACE_MODULES = (
    "src/divineos/core/hook_surfaces.py",
    "src/divineos/core/dashboard_checks.py",
)


def _returns_none_from_except(fn: ast.FunctionDef) -> list[int]:
    """Line numbers where this function returns None from inside an except."""
    lines: list[int] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Return):
                continue
            value = sub.value
            if value is None or (isinstance(value, ast.Constant) and value.value is None):
                lines.append(sub.lineno)
    return lines


@pytest.mark.parametrize("module_path", _SURFACE_MODULES)
def test_no_surface_swallows_its_own_failure(module_path):
    path = Path(module_path)
    if not path.exists():
        pytest.skip(f"{module_path} not present in this tree")

    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: dict[str, list[int]] = {}
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        lines = _returns_none_from_except(fn)
        if lines:
            offenders[fn.name] = lines

    assert not offenders, (
        f"{module_path}: these functions return None from an except handler, "
        f"which the router reads as ran-fine-nothing-to-say: {offenders}. "
        "A check that could not run must say so — return a SurfaceOutcome with "
        "an error, or state='could-not-run'. Silence is reserved for a check "
        "that ran and genuinely had nothing to report."
    )


def test_the_three_declared_states_are_the_only_ones():
    """The vocabulary is closed. A fourth state means the design changed."""
    from divineos.core.hook_router import SurfaceOutcome

    allowed = {"spoke", "nothing-to-say", "could-not-run", None}
    for state in allowed:
        SurfaceOutcome(name="probe", state=state)  # must construct

    # Undeclared is the migration frontier, NOT a fourth state. It must remain
    # the default so an un-migrated surface is visible as un-migrated rather
    # than silently sorted into one of the three.
    assert SurfaceOutcome(name="probe").state is None
