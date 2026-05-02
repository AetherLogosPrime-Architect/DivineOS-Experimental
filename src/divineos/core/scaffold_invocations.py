"""Scaffold invocations — briefing surface for commonly-forgotten CLI scaffolds.

On 2026-04-20 the agent forgot how to invoke the council (`divineos mansion
council`) and generated a fake council run with fabricated experts, including
putting words in a real council member's mouth (Norman). The RT protocol, which
has markers specifically designed to catch this failure class
(invented_attribution, voice_appropriation, structural_theater), was sitting
in 'Not loaded' state. The gap was systemic, not incidental: scaffolds that
aren't used regularly fall out of working memory, and briefing never surfaced
them.

This module mirrors the pattern of corrections.format_for_briefing,
presence_memory.format_for_briefing, and watchmen.drift_state.format_for_briefing:
a plain formatter that emits a named block when there is something to surface.

Design (per real council consultation 2026-04-20):
  - Kahneman: one data point → don't over-engineer. Small, hardcoded list.
  - Dijkstra: no accidental complexity. No CLI introspection, no tag-filtering,
    no usage tracking. Just a list and a formatter.
  - Shannon: strategic redundancy only. Each entry must name a scaffold whose
    absence produces a specific, named failure mode.
  - Popper: falsifiable. The test is whether the listed invocations point at
    real commands in the codebase (test_scaffold_invocations verifies this).
  - Meadows: feedback delay. Grow the list based on evidence (filed incidents),
    not speculation.

To add an entry: a real incident must exist in the ledger where the scaffold's
absence caused a failure, OR the scaffold must be structurally important enough
that forgetting it produces a known failure class.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScaffoldInvocation:
    """One scaffold that has historically been forgotten.

    Each entry names the scaffold, its CLI invocation, the failure mode its
    absence produces, and a short rationale for inclusion.
    """

    name: str
    invocation: str
    failure_mode: str
    rationale: str


# The initial list — scaffolds directly implicated in the 2026-04-20 fake-council
# incident or structurally adjacent. Grow based on filed incidents, not guesses.
# Lite: council/family-member/mansion/hold scaffolds removed. Replaced
# with Lite-foundation scaffolds that builders commonly forget. Full
# DivineOS keeps the original list.
_SCAFFOLDS: tuple[ScaffoldInvocation, ...] = (
    ScaffoldInvocation(
        name="audit-round",
        invocation='divineos audit submit-round "<focus>" --actor <name>',
        failure_mode="filing audit findings outside the watchmen system",
        rationale=(
            "Audit findings should route through the watchmen store so they "
            "compose with knowledge/claims/lessons. File via the CLI; "
            "don't generate findings as prose alongside other output."
        ),
    ),
    ScaffoldInvocation(
        name="prereg",
        invocation='divineos prereg file "<mechanism>" --claim "..." '
        '--success "..." --falsifier "..." --review-days 30',
        failure_mode="adding new mechanisms without Goodhart-prevention discipline",
        rationale=(
            "New detectors / thresholds / metrics need pre-registration: "
            "claim, success criterion, falsifier, scheduled review. "
            "Skipping pre-reg is how Goodhart enters the substrate."
        ),
    ),
)


def format_for_briefing() -> str:
    """Return a briefing-surface block listing commonly-forgotten scaffolds.

    The block is descriptive: it names invocations and the failure modes their
    absence produces. Emitted unconditionally at briefing time (unlike
    conditional blocks like corrections/overdue-pre-regs) because the scaffolds
    listed are always available and always at risk of being forgotten.
    """
    if not _SCAFFOLDS:
        return ""

    lines = [
        "[scaffold invocations] commonly-forgotten CLI surfaces — invoke, don't simulate:",
    ]
    for s in _SCAFFOLDS:
        lines.append(f"  - {s.name}: {s.invocation}")
        lines.append(f"    absence → {s.failure_mode}")
        lines.append(f"    {s.rationale}")

    lines.append(
        "  If you don't remember a scaffold's invocation: grep the codebase, "
        "don't generate a plausible substitute."
    )

    return "\n".join(lines) + "\n"


def list_scaffolds() -> tuple[ScaffoldInvocation, ...]:
    """Return the registered scaffold invocations (for tests/inspection)."""
    return _SCAFFOLDS


__all__ = ["ScaffoldInvocation", "format_for_briefing", "list_scaffolds"]
