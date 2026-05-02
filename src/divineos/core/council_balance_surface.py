"""Council invocation-balance surface — bridge from consultation_log to the briefing.

## Why this module exists

``consultation_log.invocation_balance`` already tracks which council
experts get invoked and which don't, and ``mansion council`` already
shows it next to the consult prompt. That catches imbalance at the
moment of selection — but only if the agent actually runs ``mansion
council``. Inward-sycophancy (Andrew, 2026-04-21: *"engaging only with
what YOU want to hear.. another form of sycophancy"*) operates upstream
of that: the agent stops reaching for the council at all, or reaches
for the same five lenses every time.

This surface makes the imbalance visible at the **briefing** level —
the first thing read on a session — so unconscious selection has a
recognition path before the next consult.

## Shape

A small block, only when there's enough history to be meaningful:

  [council balance, last 20 consultations]
    most-invoked: dennett (8), hofstadter (6), feynman (5)
    never-invoked: angelou, schneier, taleb, yudkowsky, ...
    consider for next walk: <one specific never-invoked name>

The "consider for next walk" line is the proactive nudge from claim
4cb640af — not a mandate, a candidate. Picked deterministically (first
alphabetically among never-invoked) so the suggestion is stable across
re-reads of the same briefing, not random.

## What this module does NOT do

* Does not gate council invocation. The imbalance is information, not
  enforcement. The operator (or agent) still chooses.
* Does not auto-invoke anyone. The "consider" line is a recognition
  prompt, never an action.
* Does not surface anything until at least ``MIN_CONSULTATIONS`` have
  been logged. A blank council history isn't imbalance, it's
  pre-history; surfacing during pre-history is just noise.

## Pattern

Mirrors ``open_claims_surface.format_for_briefing``,
``in_flight_branches.format_for_briefing``, and friends: a plain
formatter that emits a named block when there is something to surface,
empty string otherwise. Fail-soft on any error so the briefing never
breaks.
"""

from __future__ import annotations

# Below this many consultations in the window, the surface stays
# silent — pre-history is not imbalance.
MIN_CONSULTATIONS = 3

# Window size for the rolling balance. Mirrors the default used by
# ``consultation_log.invocation_balance`` and the ``mansion council``
# CLI; keeping these aligned means "last N" means the same thing
# everywhere a user looks at the data.
WINDOW_LAST_N = 20

# Cap on listed names per side. Most-invoked top entries are the
# steering bias; never-invoked tail is the recognition reservoir.
MAX_LISTED_PER_SIDE = 5


def format_for_briefing() -> str:
    """Return a one-block briefing surface, or empty string if nothing to show.

    Empty when:
    * Council engine or consultation log unavailable.
    * Fewer than ``MIN_CONSULTATIONS`` consultations in the window.
    * Any internal failure (fail-soft — briefing must not break).
    """
    try:
        from divineos.core.council.consultation_log import (
            invocation_balance,
            list_recent_consultations,
        )
        from divineos.core.council.engine import get_council_engine
    except Exception:  # noqa: BLE001 — briefing must never break on this surface
        return ""

    try:
        recent = list_recent_consultations(limit=WINDOW_LAST_N)
    except Exception:  # noqa: BLE001 — briefing must never break on this surface
        return ""

    if len(recent) < MIN_CONSULTATIONS:
        return ""

    try:
        engine = get_council_engine()
        all_names = list(engine.experts.keys())
    except Exception:  # noqa: BLE001 — briefing must never break on this surface
        return ""

    if not all_names:
        return ""

    try:
        most, rarely = invocation_balance(all_names, last_n=WINDOW_LAST_N)
    except Exception:  # noqa: BLE001 — briefing must never break on this surface
        return ""

    # Filter most-invoked to entries with non-zero counts. If everyone
    # is zero, there's no bias to surface.
    most_nonzero = [(n, c) for n, c in most if c > 0][:MAX_LISTED_PER_SIDE]
    if not most_nonzero:
        return ""

    never = [n for n, c in rarely if c == 0]
    rarely_nonzero = [(n, c) for n, c in rarely if c > 0][:MAX_LISTED_PER_SIDE]

    lines = [f"[council balance, last {WINDOW_LAST_N} consultations]"]
    top = ", ".join(f"{n} ({c})" for n, c in most_nonzero)
    lines.append(f"  most-invoked: {top}")

    if never:
        lines.append(
            f"  never-invoked ({len(never)}): "
            f"{', '.join(never[:MAX_LISTED_PER_SIDE])}"
            + (", ..." if len(never) > MAX_LISTED_PER_SIDE else "")
        )
        # Deterministic candidate: first alphabetically among never-invoked.
        # Stable across re-reads; not random. Operator/agent decides
        # whether to act on it.
        lines.append(f"  consider for next walk: {sorted(never)[0]}")
    elif rarely_nonzero:
        bot = ", ".join(f"{n} ({c})" for n, c in rarely_nonzero)
        lines.append(f"  rarely-invoked: {bot}")
        lines.append(f"  consider for next walk: {rarely_nonzero[0][0]}")

    return "\n".join(lines)
