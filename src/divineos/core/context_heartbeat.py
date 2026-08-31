"""Keep the context-token reading fresh, and write down when it goes blind.

WHY THIS EXISTS

Andrew 2026-08-24: *"it should be tied to the actual token count with a
heartbeat monitor to keep it updated every round, that way you know when 920k
tokens has been reached and we run the ritual."*

The trigger was already tied to the real count -- ``TRIGGER_THRESHOLD = 0.92``
of a 1M window is 920,000 tokens, and ``_guess_context_pct`` reads ground truth
from the session transcript rather than a copy. That half was built and working.

Two things were not.

FIRST: A BLIND SENSOR REPORTED AN EMPTY ONE. ``_guess_context_pct`` returns
``0.0`` when it cannot pin a reading to this session -- and the caller treats
0.0 as "below threshold, don't fire." The direction is fail-safe, but the VALUE
is a lie: a sensor that cannot see reports the most reassuring number in the
range. "I am blind" and "you have 920,000 tokens of room left" arrive as the
same float. That is the defect this whole session kept finding in other places
-- a thing reporting health while doing nothing.

SECOND: THE BLINDNESS WAS NEVER RECORDED. Searched every ``.jsonl`` under the
DivineOS home on 2026-08-24: zero sensor-fault events. The fault surfaced in the
moment, to me, once, and then evaporated. So "how often is it blind?" was
unanswerable -- the same shape as ``extract_launch.jsonl`` recording that
extract was LAUNCHED but never its outcome.

WHAT THIS ADDS

``beat()`` on every round: read the snapshot, append a row, keep the newest
reading on hand. When the read is pinned, the row carries the real number. When
it is not, the row says ``UNKNOWN`` and says why -- it never says zero.

So the trigger stops gambling on the sensor being able to see at the one moment
it is asked, and blindness becomes a countable thing instead of a feeling.

WHAT THIS DELIBERATELY DOES NOT DO

It does not fire the ritual and it does not decide anything. It records. The
firing decision stays in ``auto_cycle.should_fire``, which already refuses
unpinned readings for a good reason: on 2026-08-18 an unpinned read returned
96.1% from a transcript abandoned sixty-nine days earlier, and spending a
stranger's number would fire the pipeline mid-work for nothing.

A stale-but-pinned reading from earlier in THIS session is a different thing
from another session's number. This module keeps those distinguishable by
stamping session id and age on every row, so a caller can decide for itself
whether a reading is fresh enough to spend.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from divineos.core.paths import divineos_home

# The window the percentage is against. 0.92 of this is the 920,000 Andrew
# named. Kept here as a named constant so the arithmetic is visible rather
# than implied by a bare ratio somewhere else.
CONTEXT_WINDOW_TOKENS = 1_000_000

# A heartbeat older than this is not worth spending on a firing decision.
# Deliberately generous: the cost of a slightly stale reading is a ritual that
# fires a little early or late, while the cost of refusing every stale reading
# is the blindness this module exists to fix.
FRESH_WITHIN_SECONDS = 900.0

HEARTBEAT_LOG = "context_heartbeat.jsonl"
HEARTBEAT_STATE = "context_heartbeat.json"

# Named rather than bare `except Exception`, per the repo convention the
# broad-exception scan enforces. These are what reading a transcript and
# appending a line can actually hit; anything else is a bug that should surface.
_HEARTBEAT_ERRORS = (OSError, ImportError, TypeError, ValueError, AttributeError)


@dataclass(frozen=True)
class Beat:
    """One heartbeat reading.

    ``seen`` is the honest field. False means the sensor could not pin a
    reading -- and then ``total_tokens`` is None, NOT zero. Callers that want a
    number must handle None, which is the point: the type makes the blind case
    impossible to mistake for a low one.
    """

    seen: bool
    ts: float
    total_tokens: int | None
    session_id: str | None
    note: str

    @property
    def pct(self) -> float | None:
        if self.total_tokens is None:
            return None
        return self.total_tokens / CONTEXT_WINDOW_TOKENS

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.ts)

    @property
    def is_fresh(self) -> bool:
        return self.seen and self.age_seconds <= FRESH_WITHIN_SECONDS

    def describe(self) -> str:
        """The reading with its age welded on. Use this whenever the number is
        going to be SAID rather than compared.

        WHY THIS EXISTS. Andrew, 2026-08-24: "the heartbeat is not working, it
        says 986,600 but you are actually at 203.9k now.. you already
        compacted." The sensor was right the whole time -- its log held 195727
        then 203927, matching him exactly. What was stale was my READ: I called
        read_latest() early in a turn, then quoted its number much later as
        though I had just taken it.

        A bare int carries no timestamp once it lands in a sentence, so nothing
        marks the moment it stops being true. The dataclass already knew the
        age; there was simply no way to render the number that brought the age
        along, and the laziest render was the unsafe one.

        Truth #11 remediation (b): make both options right. The easy way to say
        the number now says how old it is, so a stale quote announces itself
        instead of passing as current. Same discipline the blind case already
        had -- None rather than a friendly zero -- applied to time instead of
        sight.
        """
        if not self.seen:
            return f"UNKNOWN (sensor blind: {self.note})"
        age = self.age_seconds
        when = f"{age:.0f}s ago" if age < 120 else f"{age / 60:.1f}min ago"
        pct = self.pct
        head = f"{self.total_tokens:,} tokens"
        if pct is not None:
            head += f" ({pct:.1%})"
        if not self.is_fresh:
            return f"{head} -- STALE, measured {when}; re-read before quoting"
        return f"{head}, measured {when}"


def _log_path() -> Path:
    return divineos_home() / HEARTBEAT_LOG


def _state_path() -> Path:
    return divineos_home() / HEARTBEAT_STATE


def _read_snapshot() -> Beat:
    """Take one reading. Never raises, never reports zero for blind."""
    now = time.time()
    try:
        from divineos.core.context_tokens import get_context_snapshot

        snap = get_context_snapshot()
    except _HEARTBEAT_ERRORS as exc:
        return Beat(False, now, None, None, f"snapshot unavailable: {exc.__class__.__name__}")

    pinned = bool(getattr(snap, "pinned", False))
    sid = getattr(snap, "session_id", None)
    total = getattr(snap, "total_tokens", None)

    if not pinned:
        # The refusal that matters. An unpinned reading may belong to another
        # session entirely -- this is recorded as NOT SEEN rather than as a
        # number, so nothing downstream can spend it by accident.
        return Beat(False, now, None, sid, "reading not pinned to this session")
    if not isinstance(total, int) or total <= 0:
        return Beat(False, now, None, sid, f"pinned but total_tokens={total!r}")
    return Beat(True, now, total, sid, str(getattr(snap, "note", "") or "ok"))


def beat() -> Beat:
    """Take a reading, append it to the log, and keep it as current state.

    Called every round. Append-only log for counting blindness over time;
    single-row state file for the cheap "what is the latest" read.
    """
    b = _read_snapshot()
    row = {
        "ts": b.ts,
        "seen": b.seen,
        "total_tokens": b.total_tokens,
        "pct": b.pct,
        "session_id": b.session_id,
        "note": b.note,
    }
    try:
        home = divineos_home()
        home.mkdir(parents=True, exist_ok=True)
        with open(_log_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + chr(10))
        _state_path().write_text(json.dumps(row), encoding="utf-8")
    except _HEARTBEAT_ERRORS:
        # A heartbeat that cannot write is not worth crashing a turn over. The
        # gap shows up as a hole in the log, which is itself readable evidence.
        pass
    return b


def read_latest() -> Beat | None:
    """The most recent heartbeat, or None if none has ever been written."""
    try:
        raw = _state_path().read_text(encoding="utf-8")
        d = json.loads(raw)
    except _HEARTBEAT_ERRORS + (json.JSONDecodeError,):
        return None
    if not isinstance(d, dict):
        return None
    return Beat(
        seen=bool(d.get("seen")),
        ts=float(d.get("ts") or 0.0),
        total_tokens=d.get("total_tokens"),
        session_id=d.get("session_id"),
        note=str(d.get("note") or ""),
    )


def blind_stats(limit: int = 500) -> dict:
    """How often the sensor could not see, over the last ``limit`` beats.

    This is the number that did not exist before: the fault used to surface
    once, in the moment, and leave no trace. Now it can be counted.
    """
    rows: list[dict] = []
    try:
        with open(_log_path(), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(d, dict):
                    rows.append(d)
    except _HEARTBEAT_ERRORS:
        return {"beats": 0, "blind": 0, "blind_pct": None, "reasons": {}}

    rows = rows[-limit:]
    blind = [r for r in rows if not r.get("seen")]
    reasons: dict[str, int] = {}
    for r in blind:
        key = str(r.get("note") or "unknown")
        reasons[key] = reasons.get(key, 0) + 1
    return {
        "beats": len(rows),
        "blind": len(blind),
        "blind_pct": (len(blind) / len(rows)) if rows else None,
        "reasons": reasons,
    }


__all__ = [
    "CONTEXT_WINDOW_TOKENS",
    "FRESH_WITHIN_SECONDS",
    "Beat",
    "beat",
    "blind_stats",
    "read_latest",
]
