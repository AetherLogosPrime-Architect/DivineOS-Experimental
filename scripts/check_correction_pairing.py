#!/usr/bin/env python3
"""Observe-then-learn pairing checker.

Audit r9-21 round-3+ structural defense for the two-record-conflation
pattern (prereg-301e34c8bf39).

Background:
  When a user correction lands, the substrate requires TWO records:
  (1) a compass observation (position-shift relative to the spectrum
  the correction touches), and (2) a learn/correction entry (the
  lesson itself, structured for retrieval). Tonight the gate fired
  twice on the same shape — I observed position but didn't file the
  correction. Two different records for two different layers; I kept
  conflating them.

  This script is the gap-surfacer: walks recent ledger events and
  recent compass observations, flags any compass observation that
  appears within N minutes after a user correction event without a
  matching learn entry within M minutes after the observation.

Usage:

    python scripts/check_correction_pairing.py [--window-minutes N]

Returns:
  * Exit 0 if no unpaired observations.
  * Exit 1 if any unpaired observations exist; prints details.
  * Surfaces drafts the operator can paste into ``divineos learn``.

This is a SURFACE, not a gate. It can be wired into precommit or run
manually. The pre-reg falsifier check is whether the rate of gate
firings on observe-without-learn drops in the 14-day review window.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add src to path so we can import divineos as a package
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

# Reasonable defaults; tunable via flags.
_DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN = 5
_DEFAULT_LEARN_AFTER_OBSERVATION_MIN = 10


def _recent_user_corrections(limit: int = 50) -> list[dict]:
    """Recent USER_CORRECTION-shaped ledger events.

    The 'detect-correction' hook writes events with type
    'USER_CORRECTION' (or sometimes 'CORRECTION_DETECTED'). We collect
    both.
    """
    from divineos.core.ledger import get_events

    events = get_events(limit=limit * 4)  # over-fetch then filter
    out = []
    for e in events:
        et = e.get("event_type", "")
        if "CORRECTION" in et.upper():
            out.append(e)
    return out[:limit]


def _recent_compass_observations(limit: int = 50) -> list[dict]:
    """Recent compass observations, newest first."""
    import sqlite3

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
    """Knowledge entries created in the time window (likely learn entries)."""
    from divineos.core.ledger import get_events

    events = get_events(limit=200)
    out = []
    for e in events:
        et = e.get("event_type", "")
        if et in ("KNOWLEDGE_STORED", "LESSON_RECORDED", "LEARN"):
            ts = float(e.get("timestamp", 0))
            if since_ts <= ts <= until_ts:
                out.append(e)
    return out


def find_unpaired(
    observation_after_correction_min: int = _DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN,
    learn_after_observation_min: int = _DEFAULT_LEARN_AFTER_OBSERVATION_MIN,
) -> list[dict]:
    """Return compass observations that look like correction-responses
    but have no matching learn entry filed within the expected window.

    Heuristic:
      1. Find observations with timestamp t_obs.
      2. Look back ``observation_after_correction_min`` minutes from
         t_obs for a USER_CORRECTION event. If found, this observation
         was likely a correction-response.
      3. Look forward ``learn_after_observation_min`` minutes from
         t_obs for a KNOWLEDGE_STORED / LESSON_RECORDED event. If
         absent, this is an unpaired observation.
    """
    corrections = _recent_user_corrections()
    observations = _recent_compass_observations()
    if not corrections or not observations:
        return []

    correction_times = [float(c.get("timestamp", 0)) for c in corrections]
    unpaired: list[dict] = []
    for obs in observations:
        t_obs = obs["created_at"]
        # Was there a correction in the 5 minutes before the observation?
        lookback_window = observation_after_correction_min * 60
        recent_correction = any(t_obs - lookback_window <= ct <= t_obs for ct in correction_times)
        if not recent_correction:
            continue
        # Was a learn entry filed in the next 10 minutes?
        lookforward_window = learn_after_observation_min * 60
        learns = _recent_learn_entries(t_obs, t_obs + lookforward_window)
        if not learns:
            unpaired.append(obs)
    return unpaired


def format_unpaired(unpaired: list[dict]) -> str:
    if not unpaired:
        return "[correction-pairing] all recent observations have matching learn entries"
    lines = [f"[correction-pairing] {len(unpaired)} unpaired observation(s):"]
    for o in unpaired:
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(o["created_at"]))
        evidence_preview = (o["evidence"] or "")[:120]
        lines.append(
            f"  obs {o['observation_id'][:8]}  spectrum={o['spectrum']}  "
            f"pos={o['position']:+.2f}  at {ts_iso}"
        )
        lines.append(f"    evidence: {evidence_preview}...")
        # Suggest a learn-entry draft seeded from the observation evidence.
        lines.append(
            f'    DRAFT: divineos learn "Correction noted on {o["spectrum"]}: '
            f"<paraphrase the evidence in your own words; what specifically "
            f'changed in your understanding>"'
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--obs-window-min",
        type=int,
        default=_DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN,
        help="Minutes to look back from an observation for a correction event.",
    )
    parser.add_argument(
        "--learn-window-min",
        type=int,
        default=_DEFAULT_LEARN_AFTER_OBSERVATION_MIN,
        help="Minutes to look forward from an observation for a learn entry.",
    )
    args = parser.parse_args()

    unpaired = find_unpaired(
        observation_after_correction_min=args.obs_window_min,
        learn_after_observation_min=args.learn_window_min,
    )
    print(format_unpaired(unpaired))
    return 1 if unpaired else 0


if __name__ == "__main__":
    sys.exit(main())
