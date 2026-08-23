"""Bounded transcript reading — one reader, measured.

## Origin (Aria + Aether, 2026-08-03), and what has since been corrected

Written as the freeze fix, after Andrew described it as *"the timer comes, the
thinking never arrives"*. The original header reasoned: escape did nothing,
therefore not waiting on a socket, therefore blocked on disk.

**Both halves of that turned out wrong, and the record belongs here rather than
in a letter nobody re-reads.**

- 2026-08-18, Aria: the stall clears on *reconnect*, not on compute. A local
  cost completes and the turn resumes with no reset; here the reset IS the
  recovery. That killed disk-blocking as the mechanism.
- 2026-08-18, Andrew: *"when the freeze happens it just says 'stopping' and
  takes a ridiculous amount of time to stop"*, where a normal stop is instant.
  A process blocked on a local read does not behave that way. It is parked in a
  wait it cannot abandon, upstream of this machine.

So this module is **not** the freeze fix and must not be re-shipped as one.

## What it is, with the number attached

The measurement that motivated it was never taken. Taken 2026-08-18, against
the largest transcript on this disk and against the live one:

    67.3 MB    whole-file 0.36 s (23,570 records)  ->  tail 0.02 s (1,364)
     3.9 MB    no saving — the file is smaller than the window

Three callers read wholesale, so roughly **one second per turn** at the large
end and nothing at the small end. Real, worth having, and an order of magnitude
short of a five-minute freeze. Written down because a fix carrying a reputation
it did not earn is how a wrong diagnosis outlives its own refutation.

It also removes a duplication. `shape_chasing_detector` carried a copy of this
loop under the comment *"kept local rather than imported to avoid cross-detector
coupling"* — the same reasoning that produced three separate wrong copies of
shell-command parsing in this repo. Avoiding coupling by copying is how one
correct implementation becomes three drifting ones.

## Why a tail is correct here — checked, not assumed

All three callers need recent records only:

* `addressee_misdirection_detector` — "a *recent* Agent tool_use"
* `shape_chasing_detector` — `_collect_recent_operator_turns(window=N)`,
  walks newest-first
* `tool_output_truncation_detector` — records after the most-recent user
  message, i.e. the current turn, and it was reading the entire session to
  find it

Not one needs session history. Each was paying for all of it.

## The third word

`read_tail_records` returns `(records, truncated)`. A caller holding a bounded
view can tell that it does. Without that flag this would create the exact
failure this substrate keeps cataloguing: a partial answer indistinguishable
from a complete one, inside the repair for it.
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
