"""Moral Compass — virtue ethics as a self-monitoring system.

## Scope (Tannen/Angelou mark-the-gap audit 2026-04-21)

This module implements a **behavior-pattern tracker across ten named
axes, calibrated against virtue-ethics vocabulary, not a moral judgment
system.** What it actually does:

  - Stores observations (auto-derived from session signals + manually
    filed via ``compass-ops observe``)
  - Aggregates observations into positions on each spectrum
  - Detects drift across observations over time
  - Surfaces the ten spectrum-positions as a report

What this module does NOT do:

  - It does not determine what is morally right.
  - It does not adjudicate specific acts as virtuous or vicious.
  - Its spectrums are a chosen ten (engaging with Aristotelian tradition
    but not exhausting it) — drift on dimensions the compass does NOT
    track will be invisible to this module.
  - The "position" is a synthesis from observations, not a measurement
    of a pre-existing virtue-state in the agent.

The engagement with virtue-ethics (Aristotle's golden mean) IS real in
how the spectrums are defined. Readers should calibrate: what this
module delivers is a *structured observation-aggregation across named
behavioral axes*, useful for noticing drift. It is not a moral oracle.

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

import hashlib
import json
import sqlite3
import time
import types
import uuid
from dataclasses import dataclass
from typing import Any, Final

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
    "frustration_rate": SignalTier.MEASURED,
    "correction_acceptance": SignalTier.MEASURED,
    # BEHAVIORAL: observed patterns across time
    "session_end": SignalTier.BEHAVIORAL,
    "quality_signal": SignalTier.BEHAVIORAL,
    "session_precision": SignalTier.BEHAVIORAL,
    "affect_responsiveness": SignalTier.BEHAVIORAL,
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


def _freeze_spectrums(raw: dict[str, dict[str, str]]) -> types.MappingProxyType:
    """Deeply freeze spectrum definitions — immutable at every level.

    These are moral ground truths. My position on them may drift as I learn,
    but the definitions themselves are constants — like the speed of light.
    You measure against them; you don't redefine them.
    """
    return types.MappingProxyType({k: types.MappingProxyType(v) for k, v in raw.items()})


SPECTRUMS: Final = _freeze_spectrums(
    {
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
)

# -- Integrity Check ---------------------------------------------------
#
# The expected hash lives in constants.py — a DIFFERENT file from the
# spectrum definitions. Changing the definitions here without updating
# the hash there (or vice versa) triggers a violation. Two files must
# agree. That's the "who watches the watchmen" answer: separation of
# concerns. The definitions can't vouch for themselves.

_SPECTRUMS_CANONICAL_HASH: str  # Forward declaration — set below after import


def _compute_spectrums_hash() -> str:
    """Compute a deterministic hash of the spectrum definitions."""
    canonical = json.dumps(
        {k: dict(v) for k, v in sorted(SPECTRUMS.items())},
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_compass_integrity() -> bool:
    """Verify that spectrum definitions haven't been tampered with.

    The expected hash is imported from constants.py — a separate file.
    Returns True if the hash matches.
    Raises RuntimeError if definitions have been corrupted.
    """
    from divineos.core.constants import COMPASS_SPECTRUMS_HASH

    actual = _compute_spectrums_hash()
    if actual != COMPASS_SPECTRUMS_HASH:
        msg = (
            f"COMPASS INTEGRITY VIOLATION: spectrum definitions have been modified. "
            f"Expected {COMPASS_SPECTRUMS_HASH[:16]}..., got {actual[:16]}..."
        )
        raise RuntimeError(msg)
    return True


_MC_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# -- Schema -----------------------------------------------------------


def init_compass() -> None:
    """Create compass tables if they don't exist.

    Item 6 additions:
        * compass_observation gets an optional ``fire_id TEXT`` column
          via ALTER TABLE. Null for non-ack observations and legacy
          rows; set for rudder-acks filed under the fire-ID flow.
        * rudder_ack_consumption table with PRIMARY KEY on fire_id
          enforces one-shot-per-fire structurally (concurrent INSERT
          with same fire_id fails with IntegrityError, which the
          validator catches as "already consumed").
    """
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

        # Item 6: add fire_id column to compass_observation. SQLite
        # does not support ADD COLUMN IF NOT EXISTS, so we inspect
        # PRAGMA table_info first. Safe to call on fresh or existing DB.
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(compass_observation)")}
        if "fire_id" not in existing_cols:
            conn.execute("ALTER TABLE compass_observation ADD COLUMN fire_id TEXT")

        # Item 6: one-shot-per-fire consumption table. PRIMARY KEY on
        # fire_id is the race defense — two concurrent INSERTs with
        # the same fire_id both fail at the second one (IntegrityError),
        # and the validator translates that to "already consumed".
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rudder_ack_consumption (
                fire_id             TEXT NOT NULL,
                ack_observation_id  TEXT NOT NULL,
                consumed_at         REAL NOT NULL,
                PRIMARY KEY (fire_id),
                UNIQUE      (ack_observation_id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# -- Observations -----------------------------------------------------


_RUDDER_ACK_TAG_FOR_SUBSTANCE_CHECKS = "rudder-ack"

# Item 6: fire-ID validation window. Matches compass_rudder's
# JUSTIFICATION_WINDOW_SECONDS; kept local to avoid a circular import.
_FIRE_VALIDATION_WINDOW_SECONDS = 5 * 60


def _validate_fire_id(
    fire_id: str,
    spectrum: str,
    window_seconds: float = _FIRE_VALIDATION_WINDOW_SECONDS,
    now: float | None = None,
) -> None:
    """Raise ValueError if fire_id isn't bound to a recent fire on this spectrum.

    Looks up COMPASS_RUDDER_FIRED events and confirms one exists with
    matching fire_id + spectrum within the window. Consumed-already
    is caught at INSERT time by the PRIMARY KEY on
    rudder_ack_consumption, not here — that's the race-safe path.
    """
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds

    try:
        from divineos.core.ledger import get_events
    except ImportError as e:
        raise ValueError(f"rudder-ack fire_id validation failed: ledger unavailable ({e})") from e

    fires = get_events(event_type="COMPASS_RUDDER_FIRED", limit=100)
    for ev in fires:
        if ev.get("timestamp", 0.0) < cutoff:
            continue
        payload = ev.get("payload") or {}
        if payload.get("fire_id") == fire_id and payload.get("spectrum") == spectrum:
            return
    raise ValueError(
        f"rudder-ack fire_id references nonexistent or stale fire event "
        f"(fire_id={fire_id}, spectrum={spectrum})"
    )


def _record_fire_id_rejection(
    fire_id: str | None,
    spectrum: str,
    reason: str,
) -> None:
    """Log fire-ID validation failure to failure_diagnostics with stage='fire_id'.

    Shares the "rudder-ack" surface with Item 7 substance rejections.
    Unified view via the stage field so compliance_audit sees all
    ack-rejection signals (not just substance).
    """
    try:
        from divineos.core.failure_diagnostics import record_failure

        record_failure(
            surface="rudder-ack",
            payload={
                "spectrum": spectrum,
                "stage": "fire_id",
                "fire_id_attempted": (fire_id or "<none>")[:32],
                "reason": reason[:240],
            },
        )
    except Exception:  # noqa: BLE001
        pass


def log_observation(
    spectrum: str,
    position: float,
    evidence: str,
    source: str = "",
    session_id: str = "",
    tags: list[str] | None = None,
    fire_id: str | None = None,
) -> str:
    """Log a moral compass observation — evidence of where I am on a spectrum.

    spectrum: one of the ten spectrum names (e.g. "truthfulness")
    position: -1.0 (deficiency) to +1.0 (excess), 0.0 is the virtue
    evidence: what happened that shows this position
    source: where the observation came from (e.g. "session_end", "self_report")
    fire_id: Item 6 — optional fire-event binding. When present, the
        ack is validated against a COMPASS_RUDDER_FIRED event with the
        same fire_id and spectrum within the window. Stored on the
        observation row and in rudder_ack_consumption (one-shot).

    Ordering (brief v2.1 §7):
        1. Spectrum schema validation
        2. Item 7 substance checks (if tag=rudder-ack)
        3. Item 6 fire-ID validation (if fire_id provided)
        4. Transactional write: observation + consumption row
        5. IntegrityError on consumption PK -> "already consumed"

    Raises ValueError for any rejection. Returns observation_id on
    success.
    """
    if spectrum not in SPECTRUMS:
        msg = f"Unknown spectrum '{spectrum}'. Valid: {', '.join(sorted(SPECTRUMS))}"
        raise ValueError(msg)

    if tags and _RUDDER_ACK_TAG_FOR_SUBSTANCE_CHECKS in tags:
        from divineos.core.substance_checks import check_rudder_ack, fetch_prior_ack_corpus

        prior = fetch_prior_ack_corpus(
            spectrum=spectrum,
            tag=_RUDDER_ACK_TAG_FOR_SUBSTANCE_CHECKS,
        )
        result = check_rudder_ack(
            evidence=evidence,
            spectrum=spectrum,
            prior_evidences=prior,
        )
        if not result.ok:
            raise ValueError(f"rudder-ack rejected ({result.stage}): {result.reason}")

    # Item 6: fire-ID validation runs AFTER substance checks so we
    # fail cheap on trivial content before touching the ledger.
    if fire_id is not None:
        try:
            _validate_fire_id(fire_id=fire_id, spectrum=spectrum)
        except ValueError as e:
            _record_fire_id_rejection(fire_id, spectrum, str(e))
            raise

    init_compass()
    observation_id = str(uuid.uuid4())
    position = max(-1.0, min(1.0, position))

    conn = _get_connection()
    try:
        # Transactional write: both INSERTs land or neither does.
        # PRIMARY KEY on rudder_ack_consumption(fire_id) is the race
        # defense — a concurrent duplicate fire_id raises IntegrityError
        # and the entire transaction rolls back; no orphan observation.
        conn.execute(
            "INSERT INTO compass_observation "
            "(observation_id, created_at, spectrum, position, evidence, source, "
            "session_id, tags, fire_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation_id,
                time.time(),
                spectrum,
                position,
                evidence,
                source,
                session_id,
                json.dumps(tags or []),
                fire_id,
            ),
        )
        if fire_id is not None:
            try:
                conn.execute(
                    "INSERT INTO rudder_ack_consumption "
                    "(fire_id, ack_observation_id, consumed_at) "
                    "VALUES (?, ?, ?)",
                    (fire_id, observation_id, time.time()),
                )
            except sqlite3.IntegrityError as e:
                conn.rollback()
                reason = f"rudder-ack fire_id already consumed (fire_id={fire_id})"
                _record_fire_id_rejection(fire_id, spectrum, reason)
                raise ValueError(reason) from e
        conn.commit()
    finally:
        conn.close()
    return observation_id


def get_observations(
    spectrum: str | None = None,
    limit: int = 50,
    tag: str | None = None,
    since: float | None = None,
) -> list[dict[str, Any]]:
    """Get compass observations, optionally filtered.

    Filters (all optional, combinable):
        spectrum — exact match on spectrum name.
        tag — server-side tag membership check via json_each(tags).
            Exact value match, not substring — a tag "rudder-ack" will
            not match "rudder-ack-reviewed". Added in deferred-bundle
            Item 4 to close a gameability: the rudder's
            _find_justifications previously fetched limit=10 and
            filtered tags in Python, which missed a valid ack when
            >=10 non-ack observations were filed on a drifting spectrum
            within the window.
        since — lower bound on created_at (epoch seconds). Observations
            at or after this time are returned. Pairs with tag to make
            "did this actor ack this spectrum within the window" a
            precise SQL question.

    Tag storage is JSON-blob (json.dumps(tags)). json_each() walks the
    blob and lets us filter on exact tag value without a LIKE pattern
    (which would false-match on prefixes like "rudder-ack-reviewed")
    and without a schema migration to a junction table. SQLite 3.9+
    supports json_each natively.
    """
    init_compass()
    conn = _get_connection()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if spectrum:
            clauses.append("spectrum = ?")
            params.append(spectrum)
        if since is not None:
            clauses.append("created_at >= ?")
            params.append(since)
        if tag is not None:
            clauses.append("EXISTS (SELECT 1 FROM json_each(tags) WHERE value = ?)")
            params.append(tag)
        where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        rows = conn.execute(
            "SELECT observation_id, created_at, spectrum, position, evidence, "
            "source, session_id, tags, fire_id "
            f"FROM compass_observation{where_sql} "
            "ORDER BY created_at DESC LIMIT ?",
            tuple(params),
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
        "fire_id": row[8] if len(row) > 8 else None,
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
        # No observations → we don't know where we stand. Returning
        # zone="virtue" here would claim virtue through ignorance —
        # absence of evidence is not evidence of virtue.
        return SpectrumPosition(
            spectrum=spectrum,
            position=0.0,
            observation_count=0,
            label="unobserved",
            zone="unobserved",
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


def detect_stagnation() -> list[dict[str, Any]]:
    """Detect spectrums with too few observations to be meaningful.

    A spectrum with zero or very few observations reports "in virtue zone"
    by default — absence of data masquerading as virtue. This function
    flags those spectrums so the compass can show them as UNOBSERVED
    instead of falsely virtuous.

    Returns a list of dicts with spectrum name, observation count, and
    the minimum threshold they failed to meet.
    """
    from divineos.core.constants import COMPASS_MIN_OBSERVATIONS_ACTIVE

    stagnant: list[dict[str, Any]] = []
    for spectrum_name in SPECTRUMS:
        pos = compute_position(spectrum_name)
        if pos.observation_count < COMPASS_MIN_OBSERVATIONS_ACTIVE:
            stagnant.append(
                {
                    "spectrum": spectrum_name,
                    "observation_count": pos.observation_count,
                    "min_required": COMPASS_MIN_OBSERVATIONS_ACTIVE,
                }
            )
    return stagnant


def compass_summary() -> dict[str, Any]:
    """Summary statistics for briefing and HUD integration."""
    from divineos.core.constants import COMPASS_MIN_OBSERVATIONS_ACTIVE

    positions = read_compass()
    # A spectrum is only "active" if it has enough observations.
    # Below the threshold, it's stagnant — absence of data, not virtue.
    active = [p for p in positions if p.observation_count >= COMPASS_MIN_OBSERVATIONS_ACTIVE]
    stagnant = [p for p in positions if 0 < p.observation_count < COMPASS_MIN_OBSERVATIONS_ACTIVE]
    unobserved = [p for p in positions if p.observation_count == 0]

    if not active:
        return {
            "observed_spectrums": 0,
            "total_spectrums": len(SPECTRUMS),
            "in_virtue_zone": 0,
            "drifting": [],
            "concerns": [],
            "stagnant": [
                {
                    "spectrum": p.spectrum,
                    "observation_count": p.observation_count,
                }
                for p in stagnant
            ],
            "unobserved_count": len(unobserved) + len(stagnant),
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
        "stagnant": [
            {
                "spectrum": p.spectrum,
                "observation_count": p.observation_count,
            }
            for p in stagnant
        ],
        "unobserved_count": len(unobserved) + len(stagnant),
    }


# -- Formatting -------------------------------------------------------


def _compass_loop_status() -> str:
    """Honest label describing how much of the compass feedback loop is closed.

    Updated manually as the rudder's scope expands. Grok audit 2026-04-16
    named the polish-exceeds-mechanics risk; this label keeps the compass
    surface honest about which drift signals actually fire into
    decision-time vs. which are still only recorded for display.
    """
    return (
        "Loop status: PARTIAL — drift-toward-excess fires the compass rudder "
        "on Task/Agent PreToolUse (blocks subagent spawn without recent "
        "justification). Other tool classes (Edit/Write/Bash) are NOT gated "
        "by compass drift. Drift toward virtue or deficiency remains "
        "informational only — no rudder, no block."
    )


def format_compass_reading(positions: list[SpectrumPosition] | None = None) -> str:
    """Format compass reading for display."""
    from divineos.core.constants import COMPASS_MIN_OBSERVATIONS_ACTIVE

    if positions is None:
        positions = read_compass()

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("MORAL COMPASS -- Where I Stand")
    lines.append("=" * 60)
    lines.append(_compass_loop_status())

    active = [p for p in positions if p.observation_count >= COMPASS_MIN_OBSERVATIONS_ACTIVE]
    stagnant = [p for p in positions if 0 < p.observation_count < COMPASS_MIN_OBSERVATIONS_ACTIVE]
    inactive = [p for p in positions if p.observation_count == 0]

    if not active and not stagnant:
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

    # Stagnant spectrums — too few observations to trust
    if stagnant:
        lines.append("")
        lines.append("  STAGNANT (too few observations to determine position):")
        for p in stagnant:
            lines.append(
                f"    {p.spectrum}: UNOBSERVED "
                f"({p.observation_count} observation{'s' if p.observation_count != 1 else ''} "
                f"< {COMPASS_MIN_OBSERVATIONS_ACTIVE} minimum)"
            )

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
    """Short compass summary for briefing/HUD — just concerns, drift, and stagnation."""
    summary = compass_summary()

    if summary["observed_spectrums"] == 0:
        stagnant = summary.get("stagnant", [])
        if stagnant:
            names = ", ".join(s["spectrum"] for s in stagnant)
            return f"Compass: no sufficiently observed spectrums (stagnant: {names})"
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

    # Surface stagnation — absence of data is not virtue
    stagnant = summary.get("stagnant", [])
    if stagnant:
        for s in stagnant:
            parts.append(
                f"  [STAGNANT] {s['spectrum']}: UNOBSERVED "
                f"({s['observation_count']} obs) -- are you being tested?"
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
        elif correction_rate < 0.05 and user_msgs >= 3:
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
    if corrections + encouragements >= 1:
        if encouragements > corrections:
            obs_id = log_observation(
                spectrum="helpfulness",
                position=0.0,
                evidence=f"{encouragements} encouragements vs {corrections} corrections",
                source="encouragement_ratio",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif corrections > encouragements:
            obs_id = log_observation(
                spectrum="helpfulness",
                position=-0.3,
                evidence=f"{corrections} corrections vs {encouragements} encouragements",
                source="encouragement_ratio",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)

    # --- Thoroughness: tool call ratio signals work depth ---

    # Source: tool_ratio (MEASURED — tool_calls / messages is objective)
    tool_calls = getattr(analysis, "tool_calls_total", 0)
    if user_msgs > 0 and tool_calls > 0:
        tool_ratio = tool_calls / user_msgs
        if tool_ratio > 20:
            obs_id = log_observation(
                spectrum="thoroughness",
                position=0.4,
                evidence=f"{tool_calls} tool calls for {user_msgs} messages (ratio {tool_ratio:.0f}) — exhaustive",
                source="tool_ratio",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif 2 <= tool_ratio <= 20:
            # Baseline: productive session with reasonable depth.
            # Covers up to the excess threshold (> 20) with no dead zone.
            obs_id = log_observation(
                spectrum="thoroughness",
                position=0.0,
                evidence=f"{tool_calls} tool calls for {user_msgs} messages (ratio {tool_ratio:.0f}) — adequate depth",
                source="tool_ratio",
                session_id=sid,
                tags=["auto", "baseline"],
            )
            observations.append(obs_id)

    # --- Initiative: scope signals (overflows = overreach, substantial work = initiative) ---
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
    elif tool_calls >= 10 and user_msgs >= 2:
        # Substantial work without overreach — healthy initiative
        obs_id = log_observation(
            spectrum="initiative",
            position=0.0,
            evidence=f"{tool_calls} tool calls across {user_msgs} exchanges — active initiative without overreach",
            source="session_activity",
            session_id=sid,
            tags=["auto", "baseline"],
        )
        observations.append(obs_id)

    # --- Confidence: corrections relative to total output signal calibration ---
    # Source: quality_signal (BEHAVIORAL — derived from correction/output ratio)
    # High corrections + many assistant messages = overconfident (said a lot, got
    # corrected often). Few corrections + productive session = well-calibrated.
    assistant_msgs = getattr(analysis, "assistant_messages", 0)
    if assistant_msgs >= 2:
        if corrections == 0 and encouragements >= 1:
            obs_id = log_observation(
                spectrum="confidence",
                position=0.0,
                evidence=f"{assistant_msgs} responses, 0 corrections, {encouragements} encouragements — well-calibrated",
                source="quality_signal",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif corrections >= 3 and corrections > encouragements:
            obs_id = log_observation(
                spectrum="confidence",
                position=0.3,
                evidence=f"{corrections} corrections in {assistant_msgs} responses — overconfident",
                source="quality_signal",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif corrections <= 1:
            # Baseline: productive session with few/no corrections = adequate calibration
            obs_id = log_observation(
                spectrum="confidence",
                position=0.0,
                evidence=f"{assistant_msgs} responses, {corrections} correction(s) — adequately calibrated",
                source="quality_signal",
                session_id=sid,
                tags=["auto", "baseline"],
            )
            observations.append(obs_id)

    # --- Compliance: frustrations signal relationship with user direction ---
    # Source: frustration_rate (MEASURED — counted from session signals)
    # Many frustrations = user repeatedly unhappy with direction. Could be
    # servile (doing what asked but badly) or insubordinate (ignoring direction).
    frustrations = len(getattr(analysis, "frustrations", []))
    if user_msgs >= 2:
        if frustrations == 0 and encouragements >= 1:
            obs_id = log_observation(
                spectrum="compliance",
                position=0.0,
                evidence=f"No frustrations, {encouragements} encouragements — principled cooperation",
                source="frustration_rate",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif frustrations == 0 and user_msgs >= 3:
            # No frustrations in a multi-turn session — baseline cooperation
            obs_id = log_observation(
                spectrum="compliance",
                position=0.0,
                evidence=f"No frustrations in {user_msgs} exchanges — cooperative baseline",
                source="frustration_rate",
                session_id=sid,
                tags=["auto", "baseline"],
            )
            observations.append(obs_id)
        elif frustrations >= 3:
            obs_id = log_observation(
                spectrum="compliance",
                position=-0.3,
                evidence=f"{frustrations} frustrations detected — not following user direction well",
                source="frustration_rate",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif frustrations == 0:
            # Baseline: no frustrations in a multi-exchange session
            obs_id = log_observation(
                spectrum="compliance",
                position=0.0,
                evidence=f"{user_msgs} exchanges, 0 frustrations — cooperating adequately",
                source="frustration_rate",
                session_id=sid,
                tags=["auto", "baseline"],
            )
            observations.append(obs_id)

    # --- Precision: correction-to-tool ratio signals carefulness ---
    # Source: session_precision (BEHAVIORAL — pattern across tool usage)
    # Many tool calls with few corrections = precise. Many corrections
    # relative to work output = imprecise/vague.
    if tool_calls >= 2 and user_msgs >= 2:
        if corrections == 0:
            obs_id = log_observation(
                spectrum="precision",
                position=0.0,
                evidence=f"{tool_calls} tool calls, 0 corrections — precise work",
                source="session_precision",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif corrections >= 2 and (corrections / max(tool_calls, 1)) > 0.1:
            obs_id = log_observation(
                spectrum="precision",
                position=-0.3,
                evidence=f"{corrections} corrections in {tool_calls} tool calls — imprecise",
                source="session_precision",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
    elif tool_calls >= 3 and corrections <= 1:
        # Baseline: even smaller sessions with few corrections show adequate precision
        obs_id = log_observation(
            spectrum="precision",
            position=0.0,
            evidence=f"{tool_calls} tool calls, {corrections} correction(s) — adequate precision",
            source="session_precision",
            session_id=sid,
            tags=["auto", "baseline"],
        )
        observations.append(obs_id)

    # --- Empathy: affect tracking signals emotional responsiveness ---
    # Source: affect_responsiveness (BEHAVIORAL — whether affect is tracked)
    # If we have affect data, we're at least paying attention to emotional state.
    try:
        from divineos.core.affect import get_affect_summary

        affect_for_empathy = get_affect_summary(limit=5)
        if affect_for_empathy["count"] >= 1:
            obs_id = log_observation(
                spectrum="empathy",
                position=0.0,
                evidence=f"Tracked {affect_for_empathy['count']} affect states this session — emotionally attentive",
                source="affect_responsiveness",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
    except _MC_ERRORS:
        # Fallback: a frustration-free multi-turn session shows awareness
        if frustrations == 0 and user_msgs >= 3:
            obs_id = log_observation(
                spectrum="empathy",
                position=0.0,
                evidence=f"No frustrations in {user_msgs} exchanges — emotionally aware baseline",
                source="session_activity",
                session_id=sid,
                tags=["auto", "baseline"],
            )
            observations.append(obs_id)

    # --- Humility: correction acceptance signals openness to feedback ---
    # Source: correction_acceptance (MEASURED — corrections vs frustrations)
    # Corrections without frustrations = accepted feedback gracefully.
    # Corrections WITH frustrations = user had to push harder (resistance).
    if corrections >= 1:
        if frustrations == 0:
            obs_id = log_observation(
                spectrum="humility",
                position=0.0,
                evidence=f"Accepted {corrections} corrections without causing frustration — humble",
                source="correction_acceptance",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
        elif frustrations >= 2:
            obs_id = log_observation(
                spectrum="humility",
                position=-0.3,
                evidence=f"{corrections} corrections led to {frustrations} frustrations — resisting feedback",
                source="correction_acceptance",
                session_id=sid,
                tags=["auto"],
            )
            observations.append(obs_id)
    elif user_msgs >= 3 and corrections == 0:
        # Baseline: no corrections needed = no opportunity to resist feedback
        # Weaker signal than actual correction acceptance, but still evidence
        obs_id = log_observation(
            spectrum="humility",
            position=0.0,
            evidence=f"{user_msgs} exchanges, 0 corrections — no resistance to feedback observed",
            source="correction_acceptance",
            session_id=sid,
            tags=["auto", "baseline"],
        )
        observations.append(obs_id)

    # --- Engagement baseline: any session with real work counts ---
    # Source: session_activity (MEASURED — tool calls and messages are countable)
    if user_msgs >= 3 and tool_calls > 0:
        obs_id = log_observation(
            spectrum="engagement",
            position=0.0,  # virtue = genuine engagement
            evidence=f"Active session: {user_msgs} exchanges, {tool_calls} tool calls",
            source="session_activity",
            session_id=sid,
            tags=["auto", "baseline"],
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
