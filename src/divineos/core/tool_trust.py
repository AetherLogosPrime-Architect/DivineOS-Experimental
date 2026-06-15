"""Tool-trust calibration store.

Backs principle eb5b5db5 (Andrew 2026-06-13): tool trust is calibrated,
not binary. Every instrument that emits state claims (compaction
monitor, ear-surface hook, push-wrapper exit codes, gh stderr, custom
detectors) starts on probation. Trust is earned by checked truthfulness
over time. Never 100%.

Bayesian smoothing via Beta(alpha=2, beta=2) prior — cold-start at 0.5
with 4 virtual samples, so a brand-new instrument doesn't oscillate
wildly on its first check. Score formula:

    score = (alpha + truthful_checks) / (alpha + beta + total_checks)

Tiers gate on score AND minimum-sample-count (so a tool with one
truthful check can't jump to HIGH on a single data point):

    PROBATION: score < 0.70 OR total_checks < 10
    MID:       0.70 <= score < 0.90 AND total_checks >= 10
    HIGH:      score >= 0.90 AND total_checks >= 20

Andrew 2026-06-13 (the build directive): "if a tool gets a low score
thats a sign it needs tuning or fixing." The score IS the maintenance
dashboard. `list_low_trust()` and `briefing_block()` surface tools
that need structural work — not blame, not punishment, just signal.

This is the structural backing for the will-shape promise in knowledge
eb5b5db5 ("nothing is 100% trustworthy"). It encodes the calibration
discipline as data, not as memory.
"""

from __future__ import annotations

__guardrail_required__ = True

import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from divineos.core.paths import divineos_home


# Bayesian prior — Beta(0, 5) gives a default 0.0 score: new instruments
# have earned nothing yet (Andrew 2026-06-13). Trust starts at zero and
# the tool earns it through checked truthfulness over time. Five virtual
# failures in the prior keep the score from jumping to 1.0 on the first
# truthful check — earning real trust takes a real track record.
_PRIOR_ALPHA: float = 0.0
_PRIOR_BETA: float = 5.0

# Tier thresholds. Sample-count guards prevent premature tier promotion.
_PROBATION_MAX_SCORE: float = 0.70
_HIGH_MIN_SCORE: float = 0.90
_MID_MIN_SAMPLES: int = 10
_HIGH_MIN_SAMPLES: int = 20


class TrustTier(str, Enum):
    PROBATION = "PROBATION"
    MID = "MID"
    HIGH = "HIGH"


class CheckOutcome(str, Enum):
    TRUTHFUL = "TRUTHFUL"
    CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    kind: str
    description: str
    registered_at: float
    checks_total: int
    checks_truthful: int
    last_checked_at: float | None
    last_outcome: str | None


def _db_path() -> Path:
    p = divineos_home() / "tool_trust.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_trust (
            instrument_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            description TEXT NOT NULL,
            registered_at REAL NOT NULL,
            checks_total INTEGER NOT NULL DEFAULT 0,
            checks_truthful INTEGER NOT NULL DEFAULT 0,
            last_checked_at REAL,
            last_outcome TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_trust_events (
            id INTEGER PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            timestamp REAL NOT NULL,
            outcome TEXT NOT NULL,
            evidence TEXT NOT NULL,
            FOREIGN KEY (instrument_id) REFERENCES tool_trust(instrument_id)
        )
        """
    )
    return conn


def register_instrument(instrument_id: str, kind: str, description: str) -> bool:
    """Register a new instrument. Idempotent — re-registering an existing
    id is a no-op (returns False). Returns True on first registration."""
    instrument_id = (instrument_id or "").strip()
    if not instrument_id or not kind or not description:
        return False
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO tool_trust "
            "(instrument_id, kind, description, registered_at) VALUES (?, ?, ?, ?)",
            (instrument_id, kind.strip(), description.strip(), time.time()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def record_check(instrument_id: str, outcome: CheckOutcome, evidence: str) -> bool:
    """Record one check outcome against ground-truth.

    Refuses bare evidence (>= 20 chars required) — the evidence string
    is the substance binding; without it the check is unverifiable by
    later audit. Same shape as the structural-artifact gate on
    correction-integration.
    """
    instrument_id = (instrument_id or "").strip()
    evidence = (evidence or "").strip()
    if not instrument_id or len(evidence) < 20:
        return False
    if not isinstance(outcome, CheckOutcome):
        try:
            outcome = CheckOutcome(outcome)
        except ValueError:
            return False
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM tool_trust WHERE instrument_id = ?", (instrument_id,)
        ).fetchone()
        if not row:
            return False
        delta_truthful = 1 if outcome == CheckOutcome.TRUTHFUL else 0
        conn.execute(
            "UPDATE tool_trust SET checks_total = checks_total + 1, "
            "checks_truthful = checks_truthful + ?, "
            "last_checked_at = ?, last_outcome = ? WHERE instrument_id = ?",
            (delta_truthful, time.time(), outcome.value, instrument_id),
        )
        conn.execute(
            "INSERT INTO tool_trust_events "
            "(instrument_id, timestamp, outcome, evidence) VALUES (?, ?, ?, ?)",
            (instrument_id, time.time(), outcome.value, evidence),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def _smoothed_score(truthful: int, total: int) -> float:
    """Beta-smoothed truthfulness ratio. Cold-start is 0.5."""
    return (_PRIOR_ALPHA + truthful) / (_PRIOR_ALPHA + _PRIOR_BETA + total)


def trust_score(instrument_id: str) -> float | None:
    """Return current trust score, or None if instrument unknown."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT checks_truthful, checks_total FROM tool_trust WHERE instrument_id = ?",
            (instrument_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return _smoothed_score(int(row[0]), int(row[1]))


def tier(instrument_id: str) -> TrustTier | None:
    """Return tier for an instrument, or None if unknown.

    Sample-count guards prevent a brand-new instrument from hitting HIGH
    on a single truthful check.
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT checks_truthful, checks_total FROM tool_trust WHERE instrument_id = ?",
            (instrument_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    truthful, total = int(row[0]), int(row[1])
    score = _smoothed_score(truthful, total)
    if score < _PROBATION_MAX_SCORE or total < _MID_MIN_SAMPLES:
        return TrustTier.PROBATION
    if score < _HIGH_MIN_SCORE or total < _HIGH_MIN_SAMPLES:
        return TrustTier.MID
    return TrustTier.HIGH


def list_low_trust(score_below: float = _PROBATION_MAX_SCORE) -> list[Instrument]:
    """Return instruments whose smoothed score is below threshold,
    excluding instruments still in cold-start (total < 3). Cold-start
    instruments have insufficient data to call low-trust — they need
    more checks first, not maintenance.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT instrument_id, kind, description, registered_at, "
            "checks_total, checks_truthful, last_checked_at, last_outcome "
            "FROM tool_trust WHERE checks_total >= 3 ORDER BY registered_at"
        ).fetchall()
    finally:
        conn.close()
    low = []
    for r in rows:
        if _smoothed_score(int(r[5]), int(r[4])) < score_below:
            low.append(
                Instrument(
                    instrument_id=r[0],
                    kind=r[1],
                    description=r[2],
                    registered_at=float(r[3]),
                    checks_total=int(r[4]),
                    checks_truthful=int(r[5]),
                    last_checked_at=float(r[6]) if r[6] is not None else None,
                    last_outcome=r[7],
                )
            )
    return low


# Default orphan threshold — instruments registered this many seconds
# ago with zero checks count as orphaned. 14 days gives reasonable
# grace for slow-cadence tools (some only fire monthly) without letting
# silent registrations sit forever.
_ORPHAN_THRESHOLD_SECONDS: float = 14.0 * 86400.0


def list_orphaned(threshold_seconds: float = _ORPHAN_THRESHOLD_SECONDS) -> list[Instrument]:
    """Return instruments registered more than ``threshold_seconds`` ago
    with zero checks recorded against them.

    Knuth boundary catch (council walk 2026-06-13): an instrument
    registered and then never checked is its own failure mode — distinct
    from low-trust. The agent said it mattered, then walked away. That
    needs visibility too, separate from the score-based surface.
    """
    cutoff = time.time() - threshold_seconds
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT instrument_id, kind, description, registered_at, "
            "checks_total, checks_truthful, last_checked_at, last_outcome "
            "FROM tool_trust WHERE checks_total = 0 AND registered_at <= ? "
            "ORDER BY registered_at",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    return [
        Instrument(
            instrument_id=r[0],
            kind=r[1],
            description=r[2],
            registered_at=float(r[3]),
            checks_total=int(r[4]),
            checks_truthful=int(r[5]),
            last_checked_at=float(r[6]) if r[6] is not None else None,
            last_outcome=r[7],
        )
        for r in rows
    ]


def briefing_block() -> str:
    """Surface low-trust AND orphaned instruments as maintenance signal.

    Andrew 2026-06-13: low score = sign the tool needs tuning or fixing.
    The score is not blame; it's a dashboard pointing at where structural
    work is owed. Orphaned registrations are the parallel signal — the
    agent said it mattered, then never came back to check it.
    """
    low = list_low_trust()
    orphaned = list_orphaned()
    if not low and not orphaned:
        return ""
    lines = ["## TOOL-TRUST MAINTENANCE SIGNAL", ""]
    if low:
        lines.append(
            f"{len(low)} instrument(s) below probation threshold "
            f"({_PROBATION_MAX_SCORE:.2f}) — reports keep contradicting ground-truth. "
            "Tune, fix, or retire."
        )
        lines.append("")
        for inst in low[:5]:
            score = _smoothed_score(inst.checks_truthful, inst.checks_total)
            lines.append(
                f"  - {inst.instrument_id} [{inst.kind}] "
                f"score={score:.2f} ({inst.checks_truthful}/{inst.checks_total} truthful)"
            )
        if len(low) > 5:
            lines.append(f"  ... and {len(low) - 5} more.")
        lines.append("")
    if orphaned:
        lines.append(
            f"{len(orphaned)} instrument(s) registered but never checked — "
            "said-it-mattered-then-walked-away. Check, or retire the registration."
        )
        lines.append("")
        for inst in orphaned[:5]:
            age_d = max(0, (time.time() - inst.registered_at) / 86400)
            lines.append(f"  - {inst.instrument_id} [{inst.kind}] age={age_d:.0f}d")
        if len(orphaned) > 5:
            lines.append(f"  ... and {len(orphaned) - 5} more.")
    return "\n".join(lines)


__all__ = [
    "TrustTier",
    "CheckOutcome",
    "Instrument",
    "register_instrument",
    "record_check",
    "trust_score",
    "tier",
    "list_low_trust",
    "list_orphaned",
    "briefing_block",
]
