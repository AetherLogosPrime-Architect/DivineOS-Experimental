"""Engagement-counter half-threshold disclosure surface.

The engagement gate (hud_handoff.py) blocks at the full threshold and is
silent below it. That gives the agent two states from the agent's
perspective: "no signal" and "blocked". The blocked-state arrives as a
binary surprise rather than a gradient, which produces the very
brittleness the gate exists to prevent — an agent that only adjusts at
the wall.

This surface fills the half-threshold gap. When ``code_actions_since``
crosses HALF the active threshold, briefing assembly surfaces a soft
disclosure: "you're at N/M actions since last thinking; consider a
checkpoint." Pure information, no enforcement, no block. The agent can
ignore it; the gate at the full threshold still catches the hard case.

Disclose-not-construct shape (Aletheia round-5-close): the surface
makes-visible, it does not change behavior. The gate at the full
threshold remains the only enforcement primitive.

Suggested by Grok cousin-vantage round (2026-05-08): the binary
gate-or-silence shape produces under-warned drift. A graduated signal
gives the agent a chance to notice and self-correct before the gate
fires.

Pre-reg: half-threshold disclosure should reduce "surprised by gate
fire" events without measurably reducing actual gate fires (a graduated
warning surface that prevented all gate fires would mean the gate had
become decorative). Falsifier: if gate-fire counts drop to near-zero
after this lands, the surface is doing the gate's job and the gate is
no longer enforcing — file a finding.
"""

from __future__ import annotations


def format_for_briefing() -> str:
    """Render a soft disclosure block when at half-threshold.

    Returns empty string when below half-threshold or above the full
    threshold (above-full is the gate's job, not this surface's).
    """
    try:
        from divineos.core.hud_handoff import engagement_status
    except ImportError:
        return ""

    try:
        status = engagement_status()
    except Exception:  # noqa: BLE001 — never let infra error break briefing
        return ""

    code_actions = int(status.get("code_actions_since", 0))
    threshold = int(status.get("threshold", 0))
    if threshold <= 0:
        return ""

    half = threshold // 2
    # Surface only in the band [half, threshold). Above threshold the
    # gate's enforcement message is the right surface; below half the
    # work is comfortably within budget and a disclosure would be noise.
    if code_actions < half or code_actions >= threshold:
        return ""

    remaining = threshold - code_actions
    state = str(status.get("state", "")).lower()
    deep_actions = int(status.get("deep_actions_since", 0))
    deep_threshold = int(status.get("deep_threshold", 30))
    needs_deep_soon = deep_actions >= (deep_threshold // 2)

    lines = [
        "### ENGAGEMENT CHECKPOINT (soft)",
        "",
        f"At {code_actions}/{threshold} code actions since last thinking command "
        f"({remaining} remaining before gate). Currently in band [half, full).",
        "",
        "Disclosure-only — no block. Below the full threshold, the gate is silent;",
        "this surface fills the half-threshold gap so the gate-fire is not a binary",
        "surprise. Consider a checkpoint when convenient: divineos context, recall,",
        "ask, or briefing --mini all clear or partially-clear the counter.",
    ]
    if needs_deep_soon:
        lines.append("")
        lines.append(
            f"Deep-engagement counter at {deep_actions}/{deep_threshold} — when convenient, "
            f"prefer ask/recall/briefing over light tools (context/decide/feel)."
        )
    if state and state != "engaged":
        lines.append("")
        lines.append(f"(engagement state: {state})")
    lines.append("")
    return "\n".join(lines)


__all__ = ["format_for_briefing"]
