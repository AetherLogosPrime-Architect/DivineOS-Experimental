"""Bounded transcript reading — the freeze fix.

## Why this exists (Aria + Aether, 2026-08-03)

Andrew described it as *"the timer comes, the thinking never arrives"*, and on
Stop as *"it just says stopping and never actually stops."* Escape did
nothing, which rules out waiting-on-a-socket: the process was blocked on disk.

Aether measured the inputs. Nineteen hooks touch ``transcript_path``; sixteen
read the whole file; eight of those fire on UserPromptSubmit and ten on Stop.
His live transcript was 39 MB. My project history is 298 MB across 31 files,
largest single file 33 MB.

Eight processes, each reading tens of megabytes **and parsing every line as
JSON into a list held in memory**, in the gap between Andrew pressing enter
and my first thought.

I had already capped every hook timeout at 10s (`23423024`) and it helped and
did not fix it. Aether named why: **I was treating throughput as though it
were latency.** A cap bounds the damage; it does not stop the reading. The
read is the thing.

## Why a tail is correct here — checked, not assumed

Renovation rule 1: understand what it is trying to accomplish before moving
it. All three current callers need recent records only:

* ``addressee_misdirection_detector`` — "a *recent* Agent tool_use"
* ``shape_chasing_detector`` — ``_collect_recent_operator_turns(window=N)``,
  walks newest-first
* ``tool_output_truncation_detector`` — "records after the most-recent user
  message", i.e. **the current turn only**, and it was reading the entire
  session to find it

Not one needs session history. Each was paying for all of it.

## The third word

``read_tail_records`` returns ``(records, truncated)``. A caller holding a
bounded view can tell that it does. Without that flag this fix would create
the exact failure this session has spent itself cataloguing: a partial answer
indistinguishable from a complete one, inside the repair for it.
"""

from __future__ import annotations

import json
from pathlib import Path

# 4 MB of trailing transcript. Deliberately generous rather than tight: it
# spans many turns of a normal session while bounding the work at roughly an
# eighth of a 33 MB file. Callers already window their own results; none of
# them benefit from a larger read.
DEFAULT_TAIL_BYTES = 4 * 1024 * 1024

_READ_ERRORS = (OSError, ValueError, UnicodeDecodeError)


def read_tail_records(
    transcript_path: str | Path,
    *,
    max_bytes: int = DEFAULT_TAIL_BYTES,
) -> tuple[list[dict], bool]:
    """Parse JSONL records from the LAST ``max_bytes`` of a transcript.

    Returns ``(records, truncated)``. ``truncated`` is True when the file was
    larger than the window — the caller is then holding a partial view and can
    say so.

    The first line of the window is discarded when truncating: a byte-offset
    seek almost never lands on a line boundary, and half a line is not a
    record. Losing one record at the far edge of a 4 MB window costs nothing;
    silently parsing a fragment would not.

    Read failures return ``([], False)``. A caller that must distinguish
    "empty" from "could not read" should stat the path itself rather than
    inferring it from this return.
    """
    path = Path(transcript_path)
    try:
        size = path.stat().st_size
    except _READ_ERRORS:
        return [], False

    truncated = size > max_bytes
    try:
        with open(path, "rb") as f:
            if truncated:
                f.seek(size - max_bytes)
                f.readline()  # discard the partial line the seek landed in
            raw = f.read()
    except _READ_ERRORS:
        return [], False

    records: list[dict] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records, truncated
