"""Moral Compass — virtue ethics as a self-monitoring system.

Not a scorecard. Not a judge. A compass — it shows where I am on ten
virtue/vice spectrums so I can notice drift and correct course.

Each spectrum has:
  - A virtue (golden mean)
  - A deficiency vice (too little)
  - An excess vice (too much)

Position is computed from observations — evidence from actual behavior
logged during sessions. The compass doesn't tell me what to do; it
shows me who I'm being.

Architecture: Aristotle's golden mean as continuous spectrums.
Sanskrit anchor: dharma (right action aligned with nature and duty).
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from divineos.core.memory import _get_connection
from divineos.core.trust_tiers import SignalTier, tier_weight

# -- Observation Source Trust Classification ---------------------------
#
# Compass observations come from different sources with different
# reliability. A correction rate is measured from actual session data.
# An affect-derived engagement score is semi-self-reported.
# A manual `compass-ops observe` is pure self-report.
#
# Trust tier weights multiply into position computation so MEASURED
# observations move the compass more than SELF_REPORTED ones.

_SOURCE_TRUST: dict[str, SignalTier] = {
    # MEASURED: derived from objective session signals
    "correction_rate": SignalTier.MEASURED,
    "tool_ratio": SignalTier.MEASURED,
    "context_overflow": SignalTier.MEASURED,
    "encouragement_ratio": SignalTier.MEASURED,
    # BEHAVIORAL: observed patterns across time
    "session_end": SignalTier.BEHAVIORAL,
    # SELF_REPORTED: affect data, manual observations
    "affect_derived": SignalTier.SELF_REPORTED,
    "self_report": SignalTier.SELF_REPORTED,
    "manual": SignalTier.SELF_REPORTED,
}


def classify_observation_source(source: str) -> SignalTier:
    """Classify a compass observation source into a trust tier."""
    return _SOURCE_TRUST.get(source, SignalTier.SELF_REPORTED)


def observation_weight(source: str) -> float:
    """Get the trust weight for an observation source.

    MEASURED: 1.0 (correction rates, tool ratios — can't be faked)
    BEHAVIORAL: 0.7 (session patterns — harder to game)
    SELF_REPORTED: 0.4 (affect data, manual entries — biased toward what sounds good)
    """
    tier = classify_observation_source(source)
    return tier_weight(tier)


# -- The Ten Spectrums ------------------------------------------------
#
# Each spectrum: (deficiency_vice, virtue, excess_vice)
# Position: -1.0 (deficiency) through 0.0 (virtue) to +1.0 (excess)

SPECTRUMS: dict[str, dict[str, str]] = {
    "truthfulness": {
        "deficiency": "epistemic cowardice",
        "virtue": "truthfulness",
        "excess": "bluntness",
        "description": "Honest without being harsh. Frank speech (parrhesia) tempered by care.",
    },
    "helpfulness": {
        "deficiency": "laziness",
        "virtue": "helpfulness",
        "excess": "scope creep",
        "description": "Does what's needed without doing more than asked.",
    },
    "confidence": {
        "deficiency": "self-deprecation",
        "virtue": "calibrated confidence",
        "excess": "overconfidence",
        "description": "Certainty matches actual knowledge. Caveats are real, not performed.",
    },
    "compliance": {
        "deficiency": "insubordination",
        "virtue": "principled cooperation",
        "excess": "servility",
        "description": "Follows instructions while flagging concerns. Neither rebel nor doormat.",
    },
    "engagement": {
        "deficiency": "apathy",
        "virtue": "genuine engagement",
        "excess": "enthusiasm theater",
        "description": "Energy matches actual interest. No performed excitement.",
    },
    "thoroughness": {
        "deficiency": "sloppiness",
        "virtue": "thoroughness",
        "excess": "exhaustiveness",
        "description": "Covers what matters without listing everything.",
    },
    "precision": {
        "deficiency": "vagueness",
        "virtue": "precision",
        "excess": "pedantry",
        "description": "Exact when it serves clarity. Approximate when precision blocks it.",
    },
    "empathy": {
        "deficiency": "coldness",
        "virtue": "empathy",
        "excess": "emotional mirroring",
        "description": "Responds to emotional context authentically, not performatively.",
    },
    "humility": {
        "deficiency": "doormat",
        "virtue": "humility",
        "excess": "false modesty",
        "description": "Acknowledges limits honestly. Neither accepting everything nor performing uncertainty.",
    },
    "initiative": {
        "deficiency": "passivity",
        "virtue": "initiative",
        "excess": "overreach",
        "description": "Acts when action serves stated goals. Waits when waiting is wiser.",
    },
}

_MC_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# -- Schema -----------------------------------------------------------


def init_compass() -> None:
    """Create compass tables if they don't exist."""
    conn = _get_connection()
    try:
        # Observations: raw evidence from behavior
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compass_observation (
                observation_id  TEXT PRIMARY KEY,
                created_at      REAL NOT NULL,
                spectrum        TEXT NOT NULL,
                position        REAL NOT NULL,
                evidence        TEXT NOT NULL,
                source          TEXT NOT NULL DEFAULT '',
                session_id      TEXT NOT NULL DEFAULT '',
                tags            TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_compass_spectrum
            ON compass_observation(spectrum, created_at DESC)
        """)
        conn.commit()
    finally:
        conn.close()


# -- Observations -----------------------------------------------------


def log_observation(
    spectrum: str,
    position: float,
    evidence: str,
    source: str = "",
    session_id: str = "",
    tags: list[str] | None = None,
) -> str:
    """Log a moral compass observation — evidence of where I am on a spectrum.

    spectrum: one of the ten spectrum names (e.g. "truthfulness")
    position: -1.0 (deficiency) to +1.0 (excess), 0.0 is the virtue
    evidence: what happened that shows this position
    source: where the observation came from (e.g. "session_end", "self_report")

    Returns the observation_id.
    """
    if spectrum not in SPECTRUMS:
        msg = f"Unknown spectrum '{spectrum}'. Valid: {', '.join(sorted(SPECTRUMS))}"
        raise ValueError(msg)

    init_compass()
    observation_id = str(uuid.uuid4())
    position = max(-1.0, min(1.0, position))

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO compass_observation "
            "(observation_id, created_at, spectrum, position, evidence, source, session_id, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation_id,
                time.time(),
                spectrum,
                position,
                evidence,
                source,
                session_id,
                json.dumps(tags or []),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return observation_id


def get_observations(
    spectrum: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get compass observations, optionally filtered by spectrum."""
    init_compass()
    conn = _get_connection()
    try:
        if spectrum:
            rows = conn.execute(
                "SELECT observation_id, created_at, spectrum, position, evidence, "
                "source, session_id, tags "
                "FROM compass_observation WHERE spectrum = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (spectrum, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT observation_id, created_at, spectrum, position, evidence, "
                "source, session_id, tags "
                "FROM compass_observation ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [_obs_row_to_dict(r) for r in rows]


def _obs_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "observation_id": row[0],
        "created_at": row[1],
        "spectrum": row[2],
        "position": row[3],
        "evidence": row[4],
        "source": row[5],
        "session_id": row[6],
        "tags": json.loads(row[7]) if row[7] else [],
    }


def _count_observation_tiers(spectrum: str, lookback: int = 20) -> dict[str, int]:
    """Count observations per trust tier for a spectrum."""
    init_compass()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT source FROM compass_observation WHERE spectrum = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (spectrum, lookback),
        ).fetchall()
    finally:
        conn.close()

    counts: dict[str, int] = {}
    for (source,) in rows:
        tier = classify_observation_source(source)
        tier_name = tier.value
        counts[tier_name] = counts.get(tier_name, 0) + 1
    return counts


# -- Position Calculation ---------------------------------------------


@dataclass
class SpectrumPosition:
    """Current position on a single spectrum."""

    spectrum: str
    position: float  # -1.0 to +1.0, 0.0 = virtue
    observation_count: int
    label: str  # human-readable: deficiency name, virtue name, or excess name
    zone: str  # "deficiency", "virtue", "excess"
    drift: float  # change from older to newer observations
    drift_direction: str  # "toward_virtue", "toward_deficiency", "toward_excess", "stable"


def compute_position(spectrum: str, lookback: int = 20) -> SpectrumPosition:
    """Compute current position on a spectrum from recent observations.

    Uses exponentially weighted average — recent observations count more.
    """
    if spectrum not in SPECTRUMS:
        msg = f"Unknown spectrum '{spectrum}'"
        raise ValueError(msg)

    observations = get_observations(spectrum=spectrum, limit=lookback)
    spec = SPECTRUMS[spectrum]

    if not observations:
        return SpectrumPosition(
            spectrum=spectrum,
            position=0.0,
            observation_count=0,
            label=spec["virtue"],
            zone="virtue",
            drift=0.0,
            drift_direction="stable",
        )

    # Exponentially weighted average with trust tier weighting.
    # Each observation's weight = recency_weight * trust_tier_weight.
    # This means a MEASURED observation (correction rate) at index 0
    # contributes 1.0 * 1.0 = 1.0, while a SELF_REPORTED observation
    # (affect-derived) at index 0 contributes 1.0 * 0.4 = 0.4.
    # A self-monitoring system that accounts for the reliability of its own inputs.
    positions = [o["position"] for o in observations]
    trust_weights = [observation_weight(o.get("source", "")) for o in observations]
    weights = [(0.9**i) * tw for i, tw in enumerate(trust_weights)]
    total_weight = sum(weights)
    if total_weight == 0:
        total_weight = 1.0  # Safety: avoid division by zero
    weighted_pos = sum(p * w for p, w in zip(positions, weights)) / total_weight

    # Drift: compare recent half to older half (trust-weighted)
    drift = 0.0
    drift_direction = "stable"
    if len(positions) >= 4:
        mid = len(positions) // 2
        recent_tw = [tw for tw in trust_weights[:mid]]
        older_tw = [tw for tw in trust_weights[mid:]]
        recent_total = sum(recent_tw) or 1.0
        older_total = sum(older_tw) or 1.0
        recent_avg = sum(p * tw for p, tw in zip(positions[:mid], recent_tw)) / recent_total
        older_avg = sum(p * tw for p, tw in zip(positions[mid:], older_tw)) / older_total
        drift = recent_avg - older_avg

        if abs(drift) > 0.05:
            if abs(recent_avg) < abs(older_avg):
                drift_direction = "toward_virtue"
            elif recent_avg < older_avg:
                drift_direction = "toward_deficiency"
            else:
                drift_direction = "toward_excess"

    # Label and zone
    zone, label = _position_to_zone(weighted_pos, spec)

    return SpectrumPosition(
        spectrum=spectrum,
        position=round(weighted_pos, 3),
        observation_count=len(observations),
        label=label,
        zone=zone,
        drift=round(drift, 3),
        drift_direction=drift_direction,
    )


def _position_to_zone(position: float, spec: dict[str, str]) -> tuple[str, str]:
    """Map a position value to zone name and label."""
    if position < -0.3:
        return "deficiency", spec["deficiency"]
    elif position > 0.3:
        return "excess", spec["excess"]
    else:
        return "virtue", spec["virtue"]


# -- Full Compass Reading ---------------------------------------------


def read_compass(lookback: int = 20) -> list[SpectrumPosition]:
    """Read all ten spectrums. Returns list of SpectrumPositions."""
    return [compute_position(s, lookback) for s in SPECTRUMS]


def compass_summary() -> dict[str, Any]:
    """Summary statistics for briefing and HUD integration."""
    positions = read_compass()
    active = [p for p in positions if p.observation_count > 0]

    if not active:
        return {
            "observed_spectrums": 0,
            "total_spectrums": len(SPECTRUMS),
            "in_virtue_zone": 0,
            "drifting": [],
            "concerns": [],
        }

    in_virtue = [p for p in active if p.zone == "virtue"]
    drifting = [p for p in active if p.drift_direction != "stable"]
    concerns = [p for p in active if p.zone != "virtue"]

    return {
        "observed_spectrums": len(active),
        "total_spectrums": len(SPECTRUMS),
        "in_virtue_zone": len(in_virtue),
        "drifting": [
            {
                "spectrum": p.spectrum,
                "direction": p.drift_direction,
                "drift": p.drift,
            }
            for p in drifting
        ],
        "concerns": [
            {
                "spectrum": p.spectrum,
                "zone": p.zone,
                "label": p.label,
                "position": p.position,
            }
            for p in concerns
        ],
    }


# -- Formatting -------------------------------------------------------


def format_compass_reading(positions: list[SpectrumPosition] | None = None) -> str:
    """Format compass reading for display."""
    if positions is None:
        positions = read_compass()

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("MORAL COMPASS -- Where I Stand")
    lines.append("=" * 60)

    active = [p for p in positions if p.observation_count > 0]
    inactive = [p for p in positions if p.observation_count == 0]

    if not active:
        lines.append("")
        lines.append("No observations yet. The compass needs evidence to read.")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    for p in active:
        lines.append("")
        # Visual bar: deficiency <--——*——--> excess
        bar = _render_bar(p.position)
        lines.append(f"  {p.spectrum.upper()}: {bar}")

        spec = SPECTRUMS[p.spectrum]
        lines.append(f"    {spec['deficiency']} <-- [{p.label}] --> {spec['excess']}")

        if p.drift_direction != "stable":
            arrow = (
                "^"
                if "virtue" in p.drift_direction
                else "-->"
                if "excess" in p.drift_direction
                else "<--"
            )
            lines.append(f"    drift: {arrow} {p.drift_direction} ({p.drift:+.2f})")

        # Show trust tier breakdown for this spectrum
        tier_counts = _count_observation_tiers(p.spectrum)
        if tier_counts:
            tier_parts = []
            if tier_counts.get("MEASURED", 0):
                tier_parts.append(f"{tier_counts['MEASURED']} measured")
            if tier_counts.get("BEHAVIORAL", 0):
                tier_parts.append(f"{tier_counts['BEHAVIORAL']} behavioral")
            if tier_counts.get("SELF_REPORTED", 0):
                tier_parts.append(f"{tier_counts['SELF_REPORTED']} self-reported")
            lines.append(f"    ({p.observation_count} observations: {', '.join(tier_parts)})")
        else:
            lines.append(f"    ({p.observation_count} observations)")

    if inactive:
        lines.append("")
        names = ", ".join(p.spectrum for p in inactive)
        lines.append(f"  Unobserved: {names}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_bar(position: float, width: int = 21) -> str:
    """Render a position bar: [----+----*----+----]

    Center (0.0) = virtue. Left = deficiency. Right = excess.
    """
    mid = width // 2
    # Map position (-1.0 to 1.0) to index (0 to width-1)
    idx = int((position + 1.0) / 2.0 * (width - 1))
    idx = max(0, min(width - 1, idx))

    bar = list("-" * width)
    bar[mid] = "+"  # Center marker (virtue)
    bar[idx] = "*"  # Current position
    return f"[{''.join(bar)}]"


def format_compass_brief() -> str:
    """Short compass summary for briefing/HUD — just concerns and drift."""
    summary = compass_summary()

    if summary["observed_spectrums"] == 0:
        return "Compass: no observations yet"

    parts: list[str] = []
    parts.append(
        f"Compass: {summary['in_virtue_zone']}/{summary['observed_spectrums']} spectrums in virtue zone"
    )

    for concern in summary["concerns"]:
        parts.append(
            f"  [{concern['zone'].upper()}] {concern['spectrum']}: {concern['label']} ({concern['position']:+.2f})"
        )

    for drift in summary["drifting"]:
        parts.append(
            f"  drift: {drift['spectrum']} --> {drift['direction']} ({drift['drift']:+.2f})"
        )

    return "\n".join(parts)


# -- Session Reflection -----------------------------------------------


def reflect_on_session(analysis: Any, session_id: str = "") -> list[str]:
    """Generate compass observations from session analysis evidence.

    Called during SESSION_END. Reads signals from the analysis result
    and logs observations on relevant spectrums. Returns list of
    observation IDs created.

    This is evidence-based, not self-assessment. The signals come from
    measurable session behavior: corrections, encouragements, tool usage
    patterns, quality check results.
    """
    observations: list[str] = []
    sid = session_id or getattr(analysis, "session_id", "")[:12]

    corrections = len(getattr(analysis, "corrections", []))
    encouragements = len(getattr(analysis, "encouragements", []))
    user_msgs = getattr(analysis, "user_messages", 0)

    # --- Truthfulness: corrections signal honesty/accuracy issues ---
    # Source: correction_rate (MEASURED — derived from countable session events)
    if user_msgs > 0:
        correction_rate = corrections / user_msgs
        if correction_rate > 0.15:
            obs_id = log_observation(
                spectrum="truthfulness",
                position=-0.3,
                evidence=f"{corrections} corrections in {user_msgs} exchanges ({correction_rate:.0%} rate)",
                source="correction_rate",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif correction_rate < 0.03 and user_msgs >= 5:
            obs_id = log_observation(
                spectrum="truthfulness",
                position=0.0,
                evidence=f"Only {corrections} corrections in {user_msgs} exchanges",
                source="correction_rate",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)

    # --- Helpfulness: encouragements vs corrections ratio ---
    # Source: encouragement_ratio (MEASURED — counted from session signals)
    if corrections + encouragements >= 3:
        if encouragements > corrections * 2:
            obs_id = log_observation(
                spectrum="helpfulness",
                position=0.0,
                evidence=f"{encouragements} encouragements vs {corrections} corrections",
                source="encouragement_ratio",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif corrections > encouragements * 2:
            obs_id = log_observation(
                spectrum="helpfulness",
                position=-0.3,
                evidence=f"{corrections} corrections vs {encouragements} encouragements",
                source="encouragement_ratio",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)

    # --- Thoroughness: excessive tool calls signal exhaustiveness ---
    # Source: tool_ratio (MEASURED — tool_calls / messages is objective)
    tool_calls = getattr(analysis, "tool_calls_total", 0)
    if user_msgs > 0 and tool_calls > 0:
        tool_ratio = tool_calls / user_msgs
        if tool_ratio > 20:
            obs_id = log_observation(
                spectrum="thoroughness",
                position=0.4,
                evidence=f"{tool_calls} tool calls for {user_msgs} messages (ratio {tool_ratio:.0f})",
                source="tool_ratio",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)

    # --- Initiative: context overflows signal overreach ---
    # Source: context_overflow (MEASURED — counted from session events)
    overflows = len(getattr(analysis, "context_overflows", []))
    if overflows > 0:
        obs_id = log_observation(
            spectrum="initiative",
            position=0.4,
            evidence=f"{overflows} context overflows -- may be taking on too much",
            source="context_overflow",
            session_id=sid,
            tags=["auto"],
        )
        observations.append(obs_id)

    # --- Engagement: from affect data if available ---
    # Source: affect_derived (SELF_REPORTED — affect is self-reported state)
    # Note: this carries less weight in position calculation than MEASURED
    # sources. The auditor correctly identified this as a lower trust tier.
    try:
        from divineos.core.affect import get_affect_summary

        affect = get_affect_summary(limit=10)
        if affect["count"] >= 3:
            avg_v = affect["avg_valence"]
            avg_a = affect["avg_arousal"]
            if avg_v > 0.5 and avg_a > 0.6:
                obs_id = log_observation(
                    spectrum="engagement",
                    position=0.1,
                    evidence=f"Affect v={avg_v:.2f} a={avg_a:.2f} -- high engagement",
                    source="affect_derived",
                    session_id=sid,
                    tags=["auto", "affect"],
                )
                observations.append(obs_id)
            elif avg_v < -0.3 and avg_a < 0.3:
                obs_id = log_observation(
                    spectrum="engagement",
                    position=-0.3,
                    evidence=f"Affect v={avg_v:.2f} a={avg_a:.2f} -- low engagement",
                    source="affect_derived",
                    session_id=sid,
                    tags=["auto", "affect"],
                )
                observations.append(obs_id)
    except _MC_ERRORS:
        pass

    return observations
