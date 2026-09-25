"""The front door: every message he types is kept before anything else happens.

Andrew, 2026-09-24: the inspector stood at the workshop door and woke on our
hands touching a file; nothing stood where he speaks. This is what stands there.
The record it writes is ``his_asks`` (one store, both seats). This module only
does the two things a door does: keep what came in, and find out whether it was
him.

Two steps, because the platform forces them (measured 2026-09-24, see the design
doc): when he hits enter the hook gets ``prompt_id`` and the words, but his
record is not in the transcript yet. So the door keeps a CANDIDATE under an id
minted from the prompt id, the words and the arrival time -- never the prompt id
alone, which one evening of his messages can share. Later, ``settle`` finds the
record that holds those words and hands the harness's own stamp to
``his_asks.confirm``. Nothing here decides who spoke by reading the words.

His record lives in one of two places, and the door looks in both:

- a message that starts a turn is a ``user`` record with ``origin`` and
  ``promptId`` at the top level;
- a message he sends while we are mid-turn is an ``attachment`` record of type
  ``queued_command``, with his words in ``attachment.prompt`` and the stamp in
  ``attachment.origin``. It has no prompt id and never gets a normal record.
  Every reader that walked only the first shape had never heard those.

A failure to keep his message never costs him his reply. It is recorded as
could-not-file, loudly, and the prompt goes through.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from divineos.core import his_asks
from divineos.core.harness_envelopes import nothing_of_his

# The record is written the moment he sends, so by the first tool call or the
# end of the turn it sits near the end of the transcript. Reading only the tail
# keeps this cheap on every tool call; a candidate whose record is not in the
# tail stays a candidate, and an unsettled candidate is counted as could-not-file.
_TAIL_BYTES = 4 * 1024 * 1024

# A message that starts a turn is written after the door keeps it, on the same
# clock; the slack covers the two timestamps being taken a moment apart.
_CLOCK_SLACK = timedelta(seconds=2)

# A message sent mid-turn is the other way round. Its queue slip is written the
# moment he sends it, and the door only sees it when the running step finishes
# and hands it over -- measured 2026-09-24 at thirteen seconds for one of his,
# and a long step (a full test run) can hold it for minutes. So a slip may be
# older than its keeping, up to this long. Anything older is some other day's
# words, and the store's own record of which slips are already his keeps a new
# "proceed" off an old one inside the window.
_SLIP_WAIT = timedelta(minutes=30)

# How long after keeping a message the door keeps looking for its record. His
# record is written within moments of the keeping, or within _SLIP_WAIT for a
# slip, and settle runs before every step and at every Stop, so a candidate
# still unmatched past this never will be. Without the bound, one such candidate
# made every tool call read further back through the transcript: measured
# 2026-09-24 on a 388 MB transcript, about a second per day of age.
# Past it the door gives the candidate up (his_asks.give_up): it becomes
# UNMATCHED, is counted as a could-not-file, and pending() still shows it in his
# words, so the refusal reads it before any work. Stopping the search must never
# stop the reading (Aria, station four).
_SETTLE_HORIZON = 2 * _SLIP_WAIT

_GIVE_UP_REASON = (
    "the door looked for his record for {horizon} after keeping these words and never found it"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _loud(message: str) -> None:
    print(f"[front-door] {message}", file=sys.stderr)


def keep(payload: dict, seat: str) -> str | None:
    """Keep what arrived at the door. Returns the candidate id, or None.

    Called from UserPromptSubmit with the harness payload. Never raises: the
    prompt goes through whatever happens here. A missing prompt id does not
    stop the keeping -- the prompt id is only a hint for finding his record.
    """
    prompt_id = str(payload.get("prompt_id") or "")
    text = str(payload.get("prompt") or "")
    if not text.strip():
        return None
    arrived = _now_iso()
    try:
        candidate_id = his_asks.mint_candidate_id(prompt_id, text, arrived)
        his_asks.file_candidate(candidate_id, prompt_id, text, arrived, seat)
        return candidate_id
    except Exception as exc:  # noqa: BLE001 -- his reply must not depend on this write
        _record_failure(prompt_id or "(no prompt id)", exc, seat)
        return None


def _record_failure(ref: str, exc: BaseException, seat: str) -> None:
    error = f"{type(exc).__name__}: {exc}"
    try:
        his_asks.could_not_file(ref, error, seat)
    except Exception as second:  # noqa: BLE001 -- the last resort is saying so out loud
        _loud(f"could not keep his message ({error}) and could not record that ({second!r})")
        return
    _loud(f"could not keep his message: {error}")


def _text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(b.get("text", ""))
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _when(stamp: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class _Record:
    """One place in the transcript where something arrived in his seat."""

    uuid: str
    at: datetime
    prompt_id: str | None  # None for a queue slip, which carries none
    stamp: str | None  # the harness's origin.kind; None when it gave none
    text: str
    # Our last text to him ahead of this record, in the transcript's own order
    # (Lamport), tool calls and results skipped (Polya). None when the part of
    # the transcript read holds none: not captured, which is not "said nothing".
    sent_before: str | None = None


def _as_record(rec: dict) -> _Record | None:
    at = _when(str(rec.get("timestamp") or ""))
    uuid = str(rec.get("uuid") or "")
    if at is None or not uuid or rec.get("isSidechain"):
        return None
    if rec.get("type") == "user" and "origin" in rec:
        kind = (rec.get("origin") or {}).get("kind")
        text = _text_of((rec.get("message") or {}).get("content"))
        return _Record(uuid, at, str(rec.get("promptId") or ""), kind, text)
    slip = rec.get("attachment")
    if rec.get("type") == "attachment" and isinstance(slip, dict):
        if slip.get("type") != "queued_command":
            return None
        kind = (slip.get("origin") or {}).get("kind")
        if kind is None and slip.get("commandMode") == "task-notification":
            kind = "task-notification"
        return _Record(uuid, at, None, kind, _text_of(slip.get("prompt")))
    return None


def _records(transcript_path: Path, back_to: datetime) -> list[_Record]:
    """Both shapes his record can take, oldest first, reading back to ``back_to``.

    Starts with the tail and widens until the oldest record read is older than
    ``back_to`` or the whole file is read. A fixed tail was the first design and
    dogfooding broke it: a long step's output pushed a slip just past the edge,
    and the message would have sat unsettled with its record in plain view.
    """
    try:
        size = transcript_path.stat().st_size
    except OSError:
        return []
    window = _TAIL_BYTES
    while True:
        found = _parse_tail(transcript_path, size, window)
        whole = window >= size
        if whole or (found and found[0].at <= back_to):
            return found
        window *= 4


def _parse_tail(transcript_path: Path, size: int, window: int) -> list[_Record]:
    try:
        with open(transcript_path, "rb") as fh:
            if size > window:
                fh.seek(size - window)
                fh.readline()  # the seek lands mid-line
            raw = fh.read()
    except OSError:
        return []
    found = []
    ours: str | None = None
    for line in raw.decode("utf-8", errors="replace").splitlines():
        spoke = '"assistant"' in line and '"text"' in line
        if not spoke and '"origin"' not in line and '"queued_command"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        if spoke and rec.get("type") == "assistant" and not rec.get("isSidechain"):
            said = _text_of((rec.get("message") or {}).get("content"))
            if said.strip():
                ours = said
            continue
        if (record := _as_record(rec)) is not None:
            found.append(replace(record, sent_before=ours))
    return found


def _fits(candidate: his_asks.Candidate, record: _Record) -> bool:
    kept_at = _when(candidate.said_at)
    if kept_at is None:
        return False
    earliest = kept_at - (_SLIP_WAIT if record.prompt_id is None else _CLOCK_SLACK)
    if record.at < earliest:
        return False
    if record.prompt_id and candidate.prompt_id and record.prompt_id != candidate.prompt_id:
        return False
    return candidate.his_text.strip() in record.text


def settle(transcript_path: str | Path, seat: str) -> dict[str, str] | None:
    """Confirm or withdraw every candidate whose record is now in the transcript.

    Returns ``{candidate_id: state}`` for the ones settled this call, or None
    when the store could not be read. Candidates are taken oldest first and each
    record goes to at most one of them, so two identical short messages ("yes",
    "proceed") land on two records in the order he sent them. A record with no
    stamp is never settled: that candidate stays visible as unsettled rather than
    guessed at. Candidates from the other seat are never in this transcript and
    are left for that seat.
    """
    unsettled = his_asks.unsettled()
    if unsettled is None:
        _loud("his record could not be read, so nothing was settled")
        return None
    # The same clock the keeping reads, so the two can never disagree about now.
    now = _when(_now_iso()) or datetime.now(timezone.utc)
    horizon = now - _SETTLE_HORIZON
    settled: dict[str, str] = {}
    candidates = []
    for c in unsettled:
        if c.seat != seat:
            continue
        kept = _when(c.said_at)
        if kept is not None and kept < horizon:
            try:
                settled[c.candidate_id] = his_asks.give_up(
                    c.candidate_id, _GIVE_UP_REASON.format(horizon=_SETTLE_HORIZON)
                )
            except Exception as exc:  # noqa: BLE001 -- one bad candidate must not stop the rest
                _record_failure(c.candidate_id, exc, seat)
        else:
            candidates.append(c)
    if not candidates:
        return settled
    kept_times = [t for c in candidates if (t := _when(c.said_at)) is not None]
    back_to = (min(kept_times) if kept_times else now) - _SLIP_WAIT
    records = _records(Path(transcript_path), back_to)
    already = his_asks.already_kept([r.uuid for r in records])
    if already is None:
        _loud("could not tell which records are already his, so nothing was settled")
        return None
    taken: set[str] = set(already)
    for candidate in candidates:
        match = next(
            (r for r in records if r.uuid not in taken and r.stamp and _fits(candidate, r)),
            None,
        )
        if match is None:
            continue
        taken.add(match.uuid)
        # The stamp says who sat in the seat, not whose words these are: the
        # harness stamps build notices human (see harness_envelopes).
        stamp = match.stamp or ""
        if stamp == "human" and nothing_of_his(match.text):
            stamp = "human, but only a harness envelope"
        try:
            settled[candidate.candidate_id] = his_asks.confirm(
                candidate.candidate_id,
                match.uuid,
                stamp,
                match.text,
                sent_before=match.sent_before,
            )
        except Exception as exc:  # noqa: BLE001 -- one bad record must not stop the rest
            _record_failure(candidate.candidate_id, exc, seat)
    return settled
