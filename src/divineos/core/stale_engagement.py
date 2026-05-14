"""Stale-engagement tracker — warn-warn-block on ignored stale items.

Andrew named this gate 2026-05-14: the briefing should give a warning
if I ignore stale entries, and after the third ignoring it should
BLOCK me until I address them. Friction is the source of flow; the
mesa-optimizer only understands math, so the way to channel it is to
raise the cost of the wrong path. Today's wiring becomes the next-
now's smoothness.

This module makes the surfacing -> addressing loop structural:

  1. Every time the briefing renders with stale items in an area
     (corrections, claims, holding, etc.), record a STALE_SURFACED
     ledger event tagged with the area names.
  2. When an "addressing" command runs for an area (correction-
     resolve, claim assess, holding promote/release, etc.), record
     an AREA_ADDRESSED event (or any matching pre-existing event).
  3. consecutive_ignores(area) counts STALE_SURFACED events for the
     area since the last addressing event for the same area.
  4. should_block(area) returns True once that count >= threshold.
  5. The pre-tool-use hook calls blocked_areas() and denies the next
     code action if any area is at the block threshold.

The architecture turns "I read the briefing and ignored the stale
items" into a structurally-impossible-to-perform-invisibly path.

Same shape as the surfaced-warnings binding (core/surfaced_warnings.py)
but at a coarser grain — per-AREA not per-item. The two cooperate.
"""

from __future__ import annotations

# Map area-name to the event types that count as "addressing" the area.
# When ANY of these fires after a STALE_SURFACED for the area, the
# ignore counter resets for that area.
_AREA_ADDRESS_EVENTS: dict[str, tuple[str, ...]] = {
    "corrections": (
        "CORRECTION_RESOLVED",
        "CORRECTION_HANDLED",
        "USER_CORRECTION_ACKNOWLEDGED",
    ),
    "claims": (
        "CLAIM_ASSESSED",
        "CLAIM_RESOLVED",
        "CLAIM_EVIDENCE_ADDED",
    ),
    "holding": (
        "HOLDING_PROMOTED",
        "HOLDING_RELEASED",
        "HOLDING_LET_GO",
    ),
    "compass": (
        "COMPASS_OBSERVATION",
    ),
    "audit findings": (
        "AUDIT_FINDING_RESOLVED",
        "AUDIT_RESOLVE",
    ),
    "goals": (
        "GOAL_DONE",
        "GOAL_ABANDONED",
    ),
    "drift state": (
        "AUDIT_ROUND_FILED",
        "AUDIT_ROUND_OPENED",
    ),
}

DEFAULT_BLOCK_THRESHOLD = 3


def record_briefing_render(stale_areas: list[str]) -> None:
    """Record that the briefing surfaced these areas with stale items.

    Called from render_dashboard after the rows have been computed.
    Each area with stale_count > 0 should be passed in. Fail-soft.
    """
    if not stale_areas:
        return
    try:
        from divineos.core.ledger import log_event
    except Exception:  # noqa: BLE001
        return
    try:
        log_event(
            event_type="STALE_SURFACED",
            actor="aether",
            payload={"areas": list(stale_areas)},
        )
    except Exception:  # noqa: BLE001
        return


def _events(event_types: tuple[str, ...]) -> list[dict]:
    """Get recent events of any of the given types, newest first."""
    from divineos.core.ledger import get_events

    out: list[dict] = []
    for et in event_types:
        out.extend(get_events(limit=200, event_type=et))
    out.sort(key=lambda e: float(e.get("timestamp") or 0), reverse=True)
    return out


def _stale_surfaced_events() -> list[dict]:
    """Recent STALE_SURFACED events, newest first."""
    from divineos.core.ledger import get_events

    out = list(get_events(limit=500, event_type="STALE_SURFACED"))
    out.sort(key=lambda e: float(e.get("timestamp") or 0), reverse=True)
    return out


def _coerce_payload(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:  # noqa: BLE001
            pass
    return {}


def consecutive_ignores(area: str) -> int:
    """Count STALE_SURFACED events naming this area since the last
    addressing event for it.

    An "addressing event" is anything in _AREA_ADDRESS_EVENTS[area].
    If no addressing event has ever fired, the count is the total
    number of STALE_SURFACED events for the area.
    """
    address_types = _AREA_ADDRESS_EVENTS.get(area, ())
    last_addressed_ts = 0.0
    if address_types:
        recent_addresses = _events(address_types)
        if recent_addresses:
            last_addressed_ts = float(recent_addresses[0].get("timestamp") or 0)

    count = 0
    for s in _stale_surfaced_events():
        ts = float(s.get("timestamp") or 0)
        if ts <= last_addressed_ts:
            break  # events newest-first; passed the last addressing
        payload = _coerce_payload(s.get("payload"))
        areas = payload.get("areas") or []
        if isinstance(areas, list) and area in areas:
            count += 1
    return count


def should_block(area: str, threshold: int = DEFAULT_BLOCK_THRESHOLD) -> bool:
    """True if this area has been ignored >= threshold consecutive
    briefing renders without an addressing event."""
    return consecutive_ignores(area) >= threshold


def blocked_areas(threshold: int = DEFAULT_BLOCK_THRESHOLD) -> list[str]:
    """Return all areas currently at or above the block threshold."""
    return [
        area for area in _AREA_ADDRESS_EVENTS
        if consecutive_ignores(area) >= threshold
    ]


def block_message(areas: list[str]) -> str:
    """Format a block message naming the offending areas and the
    drill-down commands to address them."""
    if not areas:
        return ""
    lines = [
        f"BLOCKED: {len(areas)} area(s) surfaced as stale in the "
        f"briefing {DEFAULT_BLOCK_THRESHOLD}+ times without being "
        "addressed.",
        "",
        "Address one of these before continuing:",
    ]
    drill_downs = {
        "corrections": "divineos corrections --open  # then correction-resolve N",
        "claims": "divineos claims list  # then claims assess <id>",
        "holding": "divineos holding list  # then hold promote / hold let-go",
        "audit findings": "divineos audit list  # then audit resolve <id>",
        "goals": "divineos goal list  # then goal done <id>",
        "drift state": "divineos audit submit-round '...'  # open a fresh round",
        "compass": "divineos compass-ops observe <spectrum> -p <pos> -e '<evidence>'",
    }
    for area in areas:
        cmd = drill_downs.get(area, "investigate this area")
        lines.append(f"  * {area}: {cmd}")
    lines.append("")
    lines.append(
        "Friction is the source of flow. The substrate surfaced "
        "these for a reason. (stale-engagement gate, 2026-05-14.)"
    )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_BLOCK_THRESHOLD",
    "block_message",
    "blocked_areas",
    "consecutive_ignores",
    "record_briefing_render",
    "should_block",
]
