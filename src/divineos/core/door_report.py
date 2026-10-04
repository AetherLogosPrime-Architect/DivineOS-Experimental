"""The front door's report on itself, counted from what ARRIVED.

On 2026-10-03 the door held every message of Dad's for an hour and nothing said
so, and a garbled smiley sat silent on Aether's seat until he read the table by
hand. A door that only counts what it let in always looks healthy (Aether), so
the denominator here is the app's own record of him: every human-stamped record
in this seat's transcript within the window. The door's rows are graded against
it, never the other way round.

Problems are rendered first and the rate after, because a green number read at a
glance is how this morning looked fine (council-bd341db9df04).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypeVar

from divineos.core import front_door as fd
from divineos.core import his_asks
from divineos.core.harness_envelopes import nothing_of_his, strip_envelopes

# Seen on 2026-10-03: his records settled within seconds when the door worked
# and an hour when it did not. Anything slower than this was late for him.
LATE = timedelta(minutes=2)
# A candidate with no record this long after keeping is not still on its way.
STUCK = timedelta(minutes=2)

T = TypeVar("T")


@dataclass(frozen=True)
class Problem:
    said_at: str
    text: str
    reason: str


@dataclass
class DoorReport:
    seat: str
    hours: int
    arrived: int = 0
    caught: list[float] = field(default_factory=list)  # seconds, record to settle
    late: list[Problem] = field(default_factory=list)
    missed: list[Problem] = field(default_factory=list)
    stuck: list[Problem] = field(default_factory=list)
    blind: bool = False


def _why(row: his_asks.DoorRow, record: fd._Record) -> str:
    """Why a keeping and a record are not the same message, in plain terms."""
    if row.prompt_id and record.prompt_id and row.prompt_id != record.prompt_id:
        return "a different turn: the keeping and the record carry different ids"
    kept, said = strip_envelopes(row.his_text), strip_envelopes(record.text)
    if kept != said:
        return f"words differ: kept {ascii(kept)} but his record says {ascii(said)}"
    kept_at = fd._when(row.said_at)
    gap = (record.at - kept_at).total_seconds() if kept_at else 0.0
    return f"same words and turn; his record is {gap:+.0f}s from the keeping"


def _nearest(at: datetime, among: Sequence[T], when: Callable[[T], datetime | None]) -> T | None:
    dated = [(abs((w - at).total_seconds()), x) for x in among if (w := when(x)) is not None]
    return min(dated, key=lambda pair: pair[0])[1] if dated else None


def report(transcript_path: str | Path, seat: str, hours: int = 24) -> DoorReport | None:
    """The door's catch on this seat over the last ``hours``. None if it could not look."""
    # A path that cannot be read must say so. The transcript reader swallows the
    # error and returns nothing, which would render as "he said nothing all day"
    # -- the calm-looking silence this report exists to break (Aletheia 10-03).
    try:
        with open(transcript_path, "rb"):
            pass
    except OSError:
        return None
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    rows = his_asks.door_rows(seat, since.isoformat(timespec="milliseconds"))
    if rows is None:
        return None
    arrived = [
        r
        for r in fd._records(Path(transcript_path), since)
        if r.at >= since and r.stamp == "human" and not nothing_of_his(r.text)
    ]
    live = [r for r in rows if r.state != his_asks.WITHDRAWN]
    out = DoorReport(seat=seat, hours=hours, arrived=len(arrived))

    by_uuid = {r.uuid: r for r in live if r.uuid}
    stuck_rows = [
        r
        for r in live
        if r.state == his_asks.CANDIDATE
        and (kept := fd._when(r.said_at)) is not None
        and now - kept > STUCK
    ]
    stuck_records = set()
    for row in stuck_rows:
        kept_at = fd._when(row.said_at) or now
        nearest = _nearest(kept_at, arrived, lambda x: x.at)
        reason = _why(row, nearest) if nearest else "no record of his anywhere in the window"
        if nearest:
            stuck_records.add(nearest.uuid)
        out.stuck.append(Problem(row.said_at, row.his_text, reason))

    for record in arrived:
        caught = by_uuid.get(record.uuid)
        if caught is not None and caught.settled_at is not None:
            took = caught.settled_at - record.at.timestamp()
            out.caught.append(took)
            if took > LATE.total_seconds():
                out.late.append(
                    Problem(record.at.isoformat(), record.text, f"caught after {took / 60:.0f} min")
                )
            continue
        if record.uuid in stuck_records:
            continue
        near = _nearest(record.at, live, lambda x: fd._when(x.said_at))
        reason = _why(near, record) if near else "the door kept nothing near it"
        out.missed.append(Problem(record.at.isoformat(), record.text, reason))

    out.blind = not arrived and bool(live)
    return out


def _lines(label: str, problems: list[Problem]) -> list[str]:
    return [
        f"{label} {p.said_at[:19]}  {ascii(strip_envelopes(p.text)[:70])}\n    {p.reason}"
        for p in problems
    ]


def render(got: DoorReport | None) -> str:
    """Problems first, the rate after."""
    if got is None:
        return (
            "DOOR REPORT: could not look -- the transcript or the store was unreadable, "
            "so nothing here is known"
        )
    window = f"last {got.hours}h on the {got.seat} seat"
    out: list[str] = []
    if got.blind:
        out.append(
            f"BLIND: the door kept messages in the {window} but sees no record of him -- it cannot see him"
        )
    out += _lines("MISSED", got.missed) + _lines("STUCK ", got.stuck) + _lines("LATE  ", got.late)
    if got.arrived == 0 and not got.blind:
        out.append(
            f"door: no message of his found in this transcript for the {window} -- "
            "if he did speak, this may be the wrong window's transcript"
        )
    else:
        out.append(
            f"door: caught {len(got.caught)} of {got.arrived} that arrived in the {window}"
            f" ({len(got.late)} late, {len(got.missed)} missed, {len(got.stuck)} stuck)"
        )
    return "\n".join(out)
