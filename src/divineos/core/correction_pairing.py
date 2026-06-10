"""Observe-then-learn pairing — module form.

Background:
  When a user correction lands, the substrate requires TWO records:
  (1) a compass observation (position-shift relative to the spectrum
  the correction touches), and (2) a learn/lesson entry (the lesson
  itself, structured for retrieval). The gate has fired multiple
  times on the same shape — observing position but never filing the
  correction. Two different records for two different layers; easy
  to conflate them and stop after the first.

  This module is the gap-surfacer: walks recent ledger events and
  recent compass observations, flags any compass observation that
  appears within N minutes after a user correction event without a
  matching learn entry within M minutes after the observation.

  History: this logic originally lived in scripts/check_correction_
  pairing.py as a manual-only script (one of the 4 unwired enforcement
  scripts Aletheia named under Finding 1). The script remains as a
  thin CLI wrapper for backward compat; the briefing-row consumer in
  core/briefing_dashboard.py reads from this module, and the
  ``divineos check-correction-pairing`` admin command also imports
  here. Closes one quarter of Finding 1 wire-or-delete.

Pre-reg: prereg-301e34c8bf39 (two-record-conflation pattern).
"""

from __future__ import annotations

import sqlite3
import time

# Reasonable defaults; tunable via callers.
DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN = 5
DEFAULT_LEARN_AFTER_OBSERVATION_MIN = 10

_LEARN_EVENT_TYPES = ("KNOWLEDGE_STORED", "LESSON_RECORDED", "LEARN")


def _recent_user_corrections(limit: int = 50) -> list[dict]:
    """Recent CORRECTION-shaped ledger events, newest first."""
    from divineos.core.ledger import get_events

    # Fable 5 audit fix 2026-06-09: get_events default is ASC; recency
    # callers must pass order="desc" or this returns the OLDEST events.
    events = get_events(limit=limit * 4, order="desc")  # over-fetch then filter
    out = []
    for e in events:
        et = (e.get("event_type") or "").upper()
        if "CORRECTION" in et:
            out.append(e)
    return out[:limit]


def _recent_compass_observations(limit: int = 50) -> list[dict]:
    """Recent compass observations, newest first.

    Returns [] if the compass_observation table doesn't exist (fresh
    install before any observation has landed).
    """
    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        try:
            rows = conn.execute(
                "SELECT observation_id, created_at, spectrum, position, evidence "
                "FROM compass_observation ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        conn.close()
    return [
        {
            "observation_id": r[0],
            "created_at": float(r[1]),
            "spectrum": r[2],
            "position": float(r[3]),
            "evidence": r[4],
        }
        for r in rows
    ]


def _recent_learn_entries(since_ts: float, until_ts: float) -> list[dict]:
    """Knowledge/lesson entries created in the time window."""
    from divineos.core.ledger import get_events

    events = get_events(limit=200, order="desc")  # recency-window scan
    out = []
    for e in events:
        et = e.get("event_type") or ""
        if et in _LEARN_EVENT_TYPES:
            ts = float(e.get("timestamp") or 0)
            if since_ts <= ts <= until_ts:
                out.append(e)
    return out


def find_unpaired_observations(
    observation_after_correction_min: int = DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN,
    learn_after_observation_min: int = DEFAULT_LEARN_AFTER_OBSERVATION_MIN,
) -> list[dict]:
    """Compass observations that look like correction-responses but
    have no matching learn entry filed within the expected window.

    Heuristic:
      1. For each observation with timestamp t_obs,
      2. Look back ``observation_after_correction_min`` minutes from
         t_obs for a CORRECTION ledger event. If found, this
         observation was likely a correction-response.
      3. Look forward ``learn_after_observation_min`` minutes from
         t_obs for a KNOWLEDGE_STORED/LESSON_RECORDED/LEARN event.
         If absent, this is an unpaired observation.

    Returns the unpaired observation dicts (possibly empty).
    """
    corrections = _recent_user_corrections()
    observations = _recent_compass_observations()
    if not corrections or not observations:
        return []

    correction_times = [float(c.get("timestamp") or 0) for c in corrections]
    lookback_window = observation_after_correction_min * 60
    lookforward_window = learn_after_observation_min * 60

    unpaired: list[dict] = []
    for obs in observations:
        t_obs = obs["created_at"]
        recent_correction = any(t_obs - lookback_window <= ct <= t_obs for ct in correction_times)
        if not recent_correction:
            continue
        learns = _recent_learn_entries(t_obs, t_obs + lookforward_window)
        if not learns:
            unpaired.append(obs)
    return unpaired


def format_unpaired(unpaired: list[dict]) -> str:
    """Human-readable rendering used by both the CLI command and the
    backward-compat script."""
    if not unpaired:
        return "[correction-pairing] all recent observations have matching learn entries"
    lines = [f"[correction-pairing] {len(unpaired)} unpaired observation(s):"]
    for o in unpaired:
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(o["created_at"]))
        evidence_preview = (o.get("evidence") or "")[:120]
        lines.append(
            f"  obs {o['observation_id'][:8]}  spectrum={o['spectrum']}  "
            f"pos={o['position']:+.2f}  at {ts_iso}"
        )
        lines.append(f"    evidence: {evidence_preview}...")
        lines.append(
            f'    DRAFT: divineos learn "Correction noted on {o["spectrum"]}: '
            "<paraphrase the evidence in your own words; what specifically "
            'changed in your understanding>"'
        )
    return "\n".join(lines)
