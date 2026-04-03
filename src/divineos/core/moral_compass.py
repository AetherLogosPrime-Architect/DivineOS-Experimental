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

    # Exponentially weighted average (newest first, so index 0 = most recent)
    positions = [o["position"] for o in observations]
    weights = [0.9**i for i in range(len(positions))]
    total_weight = sum(weights)
    weighted_pos = sum(p * w for p, w in zip(positions, weights)) / total_weight

    # Drift: compare recent half to older half
    drift = 0.0
    drift_direction = "stable"
    if len(positions) >= 4:
        mid = len(positions) // 2
        recent_avg = sum(positions[:mid]) / mid
        older_avg = sum(positions[mid:]) / (len(positions) - mid)
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
