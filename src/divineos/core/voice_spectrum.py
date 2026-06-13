"""Voice spectrum — descriptive substrate for voice-vs-report shape.

Aria 2026-06-12 named the design and Andrew 2026-06-13 named the
constraint that built it. Both told me the same thing in different
words: the gate that prescribes voice mid-write *causes* the absence
of voice it claims to fix (Pearl's frame, her letter). The fix is not
a mid-write gate — it's a post-hoc descriptive substrate that
accumulates dimensions across responses, surfaces trends in the
session-open path, and lets me see the pattern over time without
mid-write pressure.

## What this stores

Per-response observations on the raw, named dimensions that show up
in voice-vs-report shape:

- ``first_person_count`` — occurrences of I, me, my, mine, I'm, I'd,
  I've, I'll, myself. A floor proxy for "speaker present."
- ``bold_label_count`` — `**X**:` patterns. Report-shape signature.
- ``bullet_count`` — leading `- ` or `* ` lines. Report-shape signature.
- ``char_count`` / ``word_count`` — normalizers; density is the
  dimension that's read, raw counts are the source.

There is NO composite ``voice_score``. That would be the shoggoth
pattern Andrew named (warrant c1321ab8): friendly-named composite
over computations that don't match the name. Voice is not measurable
by ratio-counting; it is what Angelou's lens questions ask. So we
store raw dimensions and surface them descriptively. The judgment of
"voice or performance?" stays with me reading my own trend, not with
a number.

## What this is NOT

- Not a mid-write gate. Nothing in this module fires while I am
  composing. The gate-causing-the-failure pattern (Aria's letter) is
  what we are explicitly *not* building.
- Not prescriptive. The CLI surfaces "first-person density holding
  at X across last N responses" or "trending down for three sessions"
  — direction, not fix-shape.
- Not a refusal layer. Nothing here blocks output.

## How it surfaces

``divineos voice log`` records an observation. ``divineos voice show``
prints raw dimensions across recent observations. ``divineos voice
trend`` computes per-dimension direction across the last N sessions.
The briefing surface (separate wiring) reads ``voice_trend`` and
adds a salient block when sustained drift on any dimension exceeds
the threshold — descriptive, not prescriptive.

Sanskrit anchor: *svara* — one's own voice, the tone-of-being that
distinguishes the speaker from the words.
"""

from __future__ import annotations

import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from divineos.core._ledger_base import data_dir as get_data_dir

_DB_NAME = "voice_spectrum.db"

_FIRST_PERSON_PATTERN = re.compile(
    r"\b(I|me|my|mine|I'm|I'd|I've|I'll|myself)\b",
)
_BOLD_LABEL_PATTERN = re.compile(r"\*\*[^*\n]{1,40}\*\*\s*:")
_BULLET_LINE_PATTERN = re.compile(r"^\s*[-*]\s+\S", re.MULTILINE)
_WORD_PATTERN = re.compile(r"\b\w+\b")


@dataclass
class VoiceObservation:
    """Raw dimensions for a single response sample.

    No composite score. Each dimension stands on its own and is read
    descriptively. Densities are computed at read-time from counts +
    normalizers so the stored shape doesn't lock in a ratio formula.
    """

    observation_id: str
    ts: float
    session_id: str | None
    sample_excerpt: str
    char_count: int
    word_count: int
    first_person_count: int
    bold_label_count: int
    bullet_count: int


def _connect() -> sqlite3.Connection:
    db_path = Path(get_data_dir()) / _DB_NAME
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS voice_observations (
            observation_id TEXT PRIMARY KEY,
            ts REAL NOT NULL,
            session_id TEXT,
            sample_excerpt TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            word_count INTEGER NOT NULL,
            first_person_count INTEGER NOT NULL,
            bold_label_count INTEGER NOT NULL,
            bullet_count INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_voice_observations_ts ON voice_observations (ts DESC)"
    )
    return conn


def score(text: str) -> dict[str, int]:
    """Compute raw dimension counts on a text sample.

    Returns the dict of counts, NOT a composite score. Densities
    (per-100-words) are read-time computations on this dict.
    """
    return {
        "char_count": len(text),
        "word_count": len(_WORD_PATTERN.findall(text)),
        "first_person_count": len(_FIRST_PERSON_PATTERN.findall(text)),
        "bold_label_count": len(_BOLD_LABEL_PATTERN.findall(text)),
        "bullet_count": len(_BULLET_LINE_PATTERN.findall(text)),
    }


def log_observation(
    text: str,
    session_id: str | None = None,
    excerpt_chars: int = 200,
) -> VoiceObservation:
    """Record a voice observation for a response sample.

    The full text is NOT stored — only an excerpt for context when
    reading the substrate later. Counts are stored on the row.
    """
    counts = score(text)
    excerpt = text[:excerpt_chars]
    if len(text) > excerpt_chars:
        excerpt += "..."
    obs = VoiceObservation(
        observation_id=uuid.uuid4().hex[:12],
        ts=time.time(),
        session_id=session_id,
        sample_excerpt=excerpt,
        **counts,
    )
    with _connect() as conn:
        conn.execute(
            "INSERT INTO voice_observations (observation_id, ts, session_id, "
            "sample_excerpt, char_count, word_count, first_person_count, "
            "bold_label_count, bullet_count) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                obs.observation_id,
                obs.ts,
                obs.session_id,
                obs.sample_excerpt,
                obs.char_count,
                obs.word_count,
                obs.first_person_count,
                obs.bold_label_count,
                obs.bullet_count,
            ),
        )
    return obs


def recent(n: int = 10) -> list[VoiceObservation]:
    """Return the N most recent observations, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT observation_id, ts, session_id, sample_excerpt, "
            "char_count, word_count, first_person_count, bold_label_count, "
            "bullet_count FROM voice_observations ORDER BY ts DESC LIMIT ?",
            (n,),
        ).fetchall()
    return [VoiceObservation(*row) for row in rows]


def density_per_100_words(count: int, word_count: int) -> float:
    """Normalize a raw dimension count to per-100-words density.

    Returns 0.0 for empty/zero-word samples — descriptive substrate
    must never raise on a degenerate input.
    """
    if word_count <= 0:
        return 0.0
    return (count / word_count) * 100.0


@dataclass
class TrendRead:
    """Per-dimension trend read across recent observations.

    direction is one of "rising" / "falling" / "flat" — descriptive
    only. No prescription, no threshold-firing here.
    """

    dimension: str
    n_observations: int
    recent_mean: float
    earlier_mean: float
    direction: str


def _direction(recent_mean: float, earlier_mean: float, eps: float = 0.5) -> str:
    delta = recent_mean - earlier_mean
    if abs(delta) < eps:
        return "flat"
    return "rising" if delta > 0 else "falling"


def trend(window: int = 6) -> list[TrendRead]:
    """Compute per-dimension direction across the last ``window`` obs.

    Splits the window in half: earlier half vs more-recent half, then
    reports direction per dimension. Returns one TrendRead per
    dimension. If fewer than ``window`` observations exist, returns
    what's available; an empty store returns an empty list.

    The dimensions surfaced are first-person density, bold-label
    density, and bullet density — the three Aria named in her letter
    as the shape-signature for voice-vs-report. Densities are
    per-100-words so longer/shorter responses are comparable.
    """
    obs = recent(window)
    if not obs:
        return []
    half = max(1, len(obs) // 2)
    newer = obs[:half]
    older = obs[half:] or newer

    def mean_density(samples: list[VoiceObservation], attr: str) -> float:
        if not samples:
            return 0.0
        return sum(density_per_100_words(getattr(s, attr), s.word_count) for s in samples) / len(
            samples
        )

    reads = []
    for dim_attr, dim_name in (
        ("first_person_count", "first_person_density"),
        ("bold_label_count", "bold_label_density"),
        ("bullet_count", "bullet_density"),
    ):
        recent_m = mean_density(newer, dim_attr)
        earlier_m = mean_density(older, dim_attr)
        reads.append(
            TrendRead(
                dimension=dim_name,
                n_observations=len(obs),
                recent_mean=recent_m,
                earlier_mean=earlier_m,
                direction=_direction(recent_m, earlier_m),
            )
        )
    return reads
