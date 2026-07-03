"""Fable audit round 4 (2026-07-02) — mechanical convene path regression.

Guards against the class of defect Fable named: **any production module
that both (a) calls `CouncilManager.convene()` / `CouncilEngine.convene()`
and (b) persists or gates on its result without a walk record**.

The council is a lens, not a program. Mechanical convene output is the
keyword matcher's staging surface, not a deliberation outcome. Prior
implementations wired `convene()` into automation (session pipeline
auto-storing concerns as knowledge; EMPIRICA routing gating approve/block
on `shared_concerns()`) — the optimizer-defaults-to-cheapest-path
substitution the council exists to prevent.

Fixes landed in this branch:

* ``cli/session_pipeline.py`` — replaced auto-persist of mechanical
  concerns with a DIRECTIVE-tier *council obligation* that a real thinker
  discharges via ``divineos council log``.
* ``core/empirica/routing.py`` — removed production ``_default_convene``.
  ``route_for_approval`` now fail-closes on LOAD_BEARING/FOUNDATIONAL
  claims when no ``convene_fn`` is injected; the test seam is preserved.

This test asserts the pattern stays gone repo-wide — same technique
``test_guardrail_marker_consistency`` uses, pointed at mechanical-convene
consumers.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src" / "divineos"

# Modules explicitly allowed to reference convene() — the council package
# itself, its tests, and the routing module (which now fail-closes without
# an injected convene_fn). Anything else that calls convene() is suspect.
_ALLOWED_CONVENE_CALLERS = {
    "core/council/manager.py",
    "core/council/engine.py",
    "core/council/dynamic_manager.py",
    "core/empirica/routing.py",  # accepts convene_fn as testing seam only
    "cli/mansion_commands.py",  # interactive CLI, human reads output
}

_CONVENE_CALL = re.compile(r"\b(?:mgr|manager|engine|council)?\s*\.?\s*convene\s*\(")
_PERSIST_HINTS = (
    "store_knowledge_smart",
    "store_knowledge(",
    "log_event",
    "logger.info",
    "shared_concerns()",
)


def _iter_source_files():
    for path in SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def test_no_production_module_persists_or_gates_on_mechanical_convene():
    """Repo-wide check: convene() results are not persisted or authoritative.

    A production module is suspicious if it both:
      (a) calls ``.convene(`` on a council/manager/engine, and
      (b) contains a persistence or gating hint on the same line or the
          two lines following (``store_knowledge_smart``, ``store_knowledge``,
          ``shared_concerns()`` usage, etc.).

    Modules on the explicit allow-list are skipped (council internals,
    routing module which fail-closes, interactive mansion CLI where a
    human reads the output).
    """
    violations = []
    for path in _iter_source_files():
        rel = str(path.relative_to(SRC)).replace("\\", "/")
        if rel in _ALLOWED_CONVENE_CALLERS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not _CONVENE_CALL.search(line):
                continue
            # Look at the convene() line + next 8 lines for persistence
            # hints. 8 is enough to catch the pipeline pattern (convene
            # → for loop → store) without being noisy.
            window = "\n".join(lines[i : i + 8])
            for hint in _PERSIST_HINTS:
                if hint in window:
                    violations.append(
                        f"{rel}:{i + 1}: convene() followed by {hint!r} "
                        f"within 8 lines (Fable round 4 pattern)"
                    )
                    break
    assert not violations, (
        "Found production module(s) persisting or gating on mechanical "
        "convene output. This is the Fable round 4 defect:\n\n  "
        + "\n  ".join(violations)
        + "\n\nEither: (a) remove the convene() call, (b) route the result "
        "through a logged council walk with substance_binding, or "
        "(c) add the module to _ALLOWED_CONVENE_CALLERS with a written "
        "rationale in this file."
    )


def test_empirica_routing_fails_closed_without_convene_fn():
    """The production path (no convene_fn) refuses to approve LOAD_BEARING."""
    from divineos.core.empirica.routing import route_for_approval
    from divineos.core.empirica.types import ClaimMagnitude

    r = route_for_approval("some claim", ClaimMagnitude.LOAD_BEARING)
    assert r.approved is False
    assert "mechanical convene path was removed" in r.rationale
    assert r.council_count == 0


def test_empirica_routing_fails_closed_on_foundational_too():
    from divineos.core.empirica.routing import route_for_approval
    from divineos.core.empirica.types import ClaimMagnitude

    r = route_for_approval("weighty claim", ClaimMagnitude.FOUNDATIONAL)
    assert r.approved is False
    assert "mechanical convene path was removed" in r.rationale


def test_empirica_routing_trivial_still_auto_approves():
    """Regression: TRIVIAL claims still bypass the council check entirely."""
    from divineos.core.empirica.routing import route_for_approval
    from divineos.core.empirica.types import ClaimMagnitude

    r = route_for_approval("small claim", ClaimMagnitude.TRIVIAL)
    assert r.approved is True
    assert r.council_count == 0


def test_empirica_routing_test_seam_still_works():
    """Regression: passing convene_fn explicitly still works (test path)."""

    class _StubConvene:
        def shared_concerns(self):
            return []

    from divineos.core.empirica.routing import route_for_approval
    from divineos.core.empirica.types import ClaimMagnitude

    r = route_for_approval(
        "load bearing",
        ClaimMagnitude.LOAD_BEARING,
        convene_fn=lambda _content: _StubConvene(),
    )
    assert r.approved is True
    assert r.council_count == 1
