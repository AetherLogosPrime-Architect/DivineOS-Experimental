"""Multiplex panel-boundary renderer.

Per entry 71 rendering contract:
- Visual separator between panels (thin rule)
- Voice-rule render-gate applied to each panel
- Drill-down syntax: every panel ends with "More: <cmd or path>"
- Token-budget check (60-120 per panel, 600 total at session-boot)

This module exposes one main function: render_multiplex(panels) -> str.
Callers (briefing entrypoint, session-start, etc) pass a list of Panel
objects from multiplex_panels.build_panels() and get a renderable string.

Reference: prereg-ebee9082d201 falsifiers 7, 8, 10, 11.
"""

from __future__ import annotations

from divineos.core.multiplex_panels import Panel, Tier
from divineos.core.multiplex_voice import gate_render

# Per entry 71: panel size 60-120 tokens, approximated as 80-480 chars. The
# FLOOR was corrected empirically 2026-05-16 -- Aletheia read the real panels
# and found ones well under the supposed minimum rendering cleanly, so it moved
# and the contract recorded the lesson: the voice rule is the actual quality
# gate, not arbitrary token count.
#
# The CEILING never got that treatment. It stayed as the original arithmetic --
# 120 tokens times four characters -- with no reader behind it, until Andrew
# 2026-09-06 asked why it was so small: "the entire point is to find out where
# the maximum is to where the middle starts to get fuzzy so that every gulp is
# fully readable and is maximum size to get the most information squeezed in."
#
# MEASURED against the 105 natural paragraphs the briefing surfaces produce.
# Median 231 chars; three quarters under 319; nine in ten under 562. At 480,
# 11% of them were being cut mid-thought -- a fuzzy middle created by the door
# rather than by the writing. At 600, nine in ten arrive whole.
#
# Raising it further buys almost nothing: the remaining offenders run to 3138
# characters, which fails the gulp test on its own terms. Those need rewriting
# into chunks, not a wider door. So the ceiling sits just above where real
# thoughts end, and the residue is named as a content problem.
PANEL_MIN_CHARS = 80
PANEL_MAX_CHARS = 600
TOTAL_ALWAYS_ESSENTIAL_BUDGET_CHARS = 2400

# Visual separator. Thin rule between panels.
SEPARATOR = "-" * 60


def render_panel(panel: Panel) -> tuple[str, bool]:
    """Render a single panel through the voice gate.

    Returns (rendered_text, ok). If ok=False, the panel failed voice-check
    or size-check and the rendered_text is a fallback marker.
    """
    # Voice gate first
    gated_content, report = gate_render(panel.content, panel.name)
    if not report.passed:
        return gated_content, False

    # Size check
    if len(panel.content) < PANEL_MIN_CHARS:
        return (
            f"[SIZE-RULE-VIOLATION in panel {panel.name}: {len(panel.content)} chars < {PANEL_MIN_CHARS} min]",
            False,
        )
    if len(panel.content) > PANEL_MAX_CHARS:
        return (
            f"[SIZE-RULE-VIOLATION in panel {panel.name}: {len(panel.content)} chars > {PANEL_MAX_CHARS} max]",
            False,
        )

    # Drill-down required
    if not panel.drill_down:
        return f"[DRILL-DOWN-MISSING in panel {panel.name}]", False

    body = panel.content
    drill = f"More: {panel.drill_down}"
    return body + chr(10) + drill, True


def render_multiplex(panels: list[Panel]) -> str:
    """Render a list of panels with visual boundaries and voice-checks.

    Always-essentials surface first (in their order from build_panels),
    then sometimes-essentials. Separator between panels.
    Total always-essential char count enforced against budget.
    """
    if not panels:
        return ""

    # Budget check on always-essential cohort
    always = [p for p in panels if p.tier == Tier.ALWAYS]
    total_chars = sum(len(p.content) for p in always)
    if total_chars > TOTAL_ALWAYS_ESSENTIAL_BUDGET_CHARS:
        budget_warning = (
            f"[BUDGET-RULE-VIOLATION: always-essential total "
            f"{total_chars} chars > {TOTAL_ALWAYS_ESSENTIAL_BUDGET_CHARS} budget]"
        )
    else:
        budget_warning = ""

    blocks: list[str] = []
    for panel in panels:
        rendered, ok = render_panel(panel)
        blocks.append(rendered)

    output = (chr(10) + SEPARATOR + chr(10)).join(blocks)
    if budget_warning:
        output = budget_warning + chr(10) + chr(10) + output
    return output


def diagnostics(panels: list[Panel]) -> dict:
    """Return per-panel diagnostics for testing and audit."""
    diag = {
        "panel_count": len(panels),
        "always_count": sum(1 for p in panels if p.tier == Tier.ALWAYS),
        "sometimes_count": sum(1 for p in panels if p.tier == Tier.SOMETIMES),
        "total_chars_always": sum(len(p.content) for p in panels if p.tier == Tier.ALWAYS),
        "total_chars_all": sum(len(p.content) for p in panels),
        "panels": [
            {
                "name": p.name,
                "tier": p.tier.value,
                "chars": len(p.content),
                "has_drill": bool(p.drill_down),
            }
            for p in panels
        ],
    }
    return diag
