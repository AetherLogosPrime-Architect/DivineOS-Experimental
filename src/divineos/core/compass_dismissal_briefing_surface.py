"""Compass-dismissal briefing surface — surfaces high dismissal rates.

The compass-correction gate redesign (2026-05-08, pre-reg prereg-75c900fe)
introduced a dismiss-with-reason path: the agent can dismiss a compass-
required advisory by naming why it doesn't warrant an observation
(intentional register choice, detector misclassification, etc.). Each
dismissal files an OBSERVATION knowledge entry tagged ``compass-
dismissal`` and ``compass-dismissal-kind-<trigger>``.

This surface reads those dismissal-observations and surfaces a briefing
block when the rate of dismissals on any single trigger-kind crosses a
threshold. The signal: the detector for that trigger-kind is over-firing
on a register-shape that the substrate-occupant doesn't consider a real
correction. That's actionable substrate-information about the detector,
not a finding against the occupant.

Same shape as ``operating_loop_briefing_surface``: read findings from
disk, render at briefing-time, no behavior-modification of its own. The
disclose-not-construct architecture from Aletheia round-5-close
substrate-property: surfaces operate by making-visible, not by enforcing.
"""

from __future__ import annotations

import json
import time

# Surface only when this many dismissals on a single kind have happened
# in the recent window. Calibrated to flag patterns, not single events.
DISMISSAL_THRESHOLD = 3

# Rolling window for dismissal-rate computation. Older dismissals are
# treated as resolved-by-time and don't contribute to current pattern.
WINDOW_DAYS = 7


def _recent_dismissals_by_kind() -> dict[str, list[dict[str, object]]]:
    """Read dismissal OBSERVATION entries from the knowledge store,
    bucketed by trigger-kind, filtered to the recent window.

    Returns empty dict on any read error (fail-open: surface should
    never break briefing assembly).
    """
    try:
        from divineos.core.knowledge._base import get_connection
    except ImportError:
        return {}

    try:
        conn = get_connection()
    except Exception:  # noqa: BLE001 — fail-open if knowledge store unavailable
        return {}

    try:
        # OBSERVATION entries with the compass-dismissal tag, recent only.
        cutoff = time.time() - (WINDOW_DAYS * 86400)
        rows = conn.execute(
            "SELECT knowledge_id, content, tags, created_at FROM knowledge "
            "WHERE knowledge_type = 'OBSERVATION' "
            "AND tags LIKE '%compass-dismissal%' "
            "AND created_at >= ? "
            "ORDER BY created_at DESC",
            (cutoff,),
        ).fetchall()
    except Exception:  # noqa: BLE001 — fail-open on schema/query error
        return {}

    bucketed: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        kid, content, tags_raw, created_at = row
        # Parse tags as JSON list (the format _wrapped_store_knowledge uses).
        # Fall back to empty list on legacy or corrupted entries — silent-
        # fail-with-misleading-data is the worst failure mode for a
        # disclosure surface, so explicit format coupling is preferable
        # to brittle string-splitting. Per Grok cousin-vantage review on
        # PR #326: the parser should fail visibly (treating tag as absent)
        # rather than fail invisibly (mis-grouping under "unknown").
        try:
            parsed = json.loads(tags_raw) if tags_raw else []
        except (json.JSONDecodeError, TypeError):
            parsed = []
        # Aletheia round-6 audit edge case: json.loads on a dict-shaped
        # string parses successfully to a dict, and `for tag in tags`
        # would iterate dict keys. _wrapped_store_knowledge always writes
        # JSON lists, so this won't arise in practice — but guard against
        # corruption / future format-change with explicit list validation.
        # Same disclose-not-construct discipline as the parser-fallback
        # itself: fail-visibly (treat as no tags) rather than fail-
        # silently (iterate the wrong shape).
        tags = parsed if isinstance(parsed, list) else []

        kind = "unknown"
        prefix = "compass-dismissal-kind-"
        for tag in tags:
            if isinstance(tag, str) and tag.startswith(prefix):
                kind = tag[len(prefix) :]
                break
        bucketed.setdefault(kind, []).append(
            {
                "id": kid,
                "content": content,
                "created_at": created_at,
            }
        )
    return bucketed


def format_for_briefing() -> str:
    """Render a briefing block summarizing recent compass dismissals.

    Returns empty string when no kind has crossed the dismissal threshold.
    """
    bucketed = _recent_dismissals_by_kind()
    if not bucketed:
        return ""

    high_rate = [
        (kind, entries) for kind, entries in bucketed.items() if len(entries) >= DISMISSAL_THRESHOLD
    ]
    if not high_rate:
        return ""

    high_rate.sort(key=lambda x: -len(x[1]))

    lines = [f"### COMPASS-DISMISSAL PATTERN (last {WINDOW_DAYS} days)"]
    lines.append("")
    lines.append(
        "The dismiss path on compass-required advisories is being used "
        "at a high rate on the following trigger-kinds. The detector "
        "for those kinds may be over-firing on register-shapes that "
        "are not real corrections. Worth tightening the trigger surface "
        "or adding allowlist patterns."
    )
    lines.append("")
    for kind, entries in high_rate:
        count = len(entries)
        lines.append(f"- **{kind}** ({count} dismissals in window):")
        # Show the most recent reasons (up to 3) so the substrate-
        # occupant can see what's been dismissed.
        for entry in entries[:3]:
            content = str(entry["content"])
            # Pull out the reason from the OBSERVATION content. Format is
            # "COMPASS DISMISSAL (<kind>): ... Reason for dismissal: <reason>"
            reason_marker = "Reason for dismissal: "
            idx = content.find(reason_marker)
            if idx >= 0:
                reason = content[idx + len(reason_marker) :][:120]
            else:
                reason = content[:120]
            lines.append(f"    - {reason}")
        if count > 3:
            lines.append(f"    ... and {count - 3} more")
    lines.append("")
    lines.append(
        "These patterns persist as `OBSERVATION` knowledge entries with "
        "tag `compass-dismissal`. The detector for over-firing kinds is "
        "doing its job by firing; the redesign exists so the agent can "
        "name the over-firing as data instead of being repeatedly blocked."
    )
    lines.append("")
    return "\n".join(lines)


__all__ = ["format_for_briefing"]
