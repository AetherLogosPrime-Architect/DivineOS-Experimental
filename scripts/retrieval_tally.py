"""Retrieval-tally: measure whether surfaced past-writing actually gets read.

The past-writing-to-Andrew surface fires at compose-start and prints a list
of past letters + exploration entries. Whether reading the surface changes
what I compose is the open empirical question — I named it as Finding 1 in
my adversarial review of Aria's hook: her hook (and mine) produces a
receipt-that-it-fired, not a receipt-that-I-reached.

This module closes that gap. Two entry-points:

  record_surfaced(paths)   Called at surface-fire time. Records the list
                           of paths surfaced this turn to a marker file.
                           The past-writing hook calls this after printing
                           its output.

  check_reply(reply)       Called at reply-complete time (post-compose).
                           Reads the marker; scans reply text for any of
                           the surfaced paths (filename OR full path OR
                           slug); logs an append-only JSONL row with the
                           tally.

Tally row shape (~/.divineos/retrieval_tally.jsonl):
    {"ts": 1234567890, "surfaced": ["path1", "path2"],
     "referenced": ["path1"], "tally": "1/2"}

Weekly view: read the jsonl, count referenced/surfaced ratio over last N
days. Low ratio = the shelf is visible but I am not reaching for it.
Andrew's "wallpaper" test in structural form.

The falsifier: if the ratio stays above 0.5 for 30 days AND Andrew still
reports the same pile-forming failure, the tally is measuring the wrong
thing. If the ratio stays below 0.1, the hook is dead-code by my hand.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path


_HOME = Path.home() / ".divineos"
_SURFACED_MARKER = _HOME / "past_writing_surfaced.json"
_TALLY_LOG = _HOME / "retrieval_tally.jsonl"


def record_surfaced(paths: list[str]) -> None:
    """Record the list of paths surfaced this turn.

    Called by the past-writing surface hook after emitting its output.
    Overwrites any prior marker (only the most-recent surface is
    relevant — the tally check runs before the next surface fires).

    Fail-open on any I/O error.
    """
    try:
        _HOME.mkdir(parents=True, exist_ok=True)
        payload = {"ts": time.time(), "paths": [str(p) for p in paths]}
        _SURFACED_MARKER.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def _load_surfaced() -> tuple[float, list[str]] | None:
    """Load the most recent surfaced-paths marker. Return (ts, paths) or None."""
    if not _SURFACED_MARKER.exists():
        return None
    try:
        data = json.loads(_SURFACED_MARKER.read_text(encoding="utf-8"))
        return (float(data.get("ts", 0)), list(data.get("paths", [])))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


def check_reply(reply: str) -> dict | None:
    """Scan reply for references to any surfaced path. Log the tally.

    A path is "referenced" if any of these appear in the reply:
      - the full path string
      - the basename (with or without .md extension)
      - the slug (basename minus the leading YYYY-MM-DD or NNN_ prefix)

    Returns the tally dict if a marker was present, else None.
    """
    loaded = _load_surfaced()
    if loaded is None:
        return None
    ts_surfaced, paths = loaded
    if not paths:
        return None

    referenced = []
    for p in paths:
        base = Path(p).name
        stem = Path(p).stem
        # Extract slug candidates. Try several strategies because filename
        # conventions differ across letters (aether-to-andrew-YYYY-MM-DD-SLUG)
        # and explorations (NNN_slug or NNN-slug).
        slug_candidates = {stem}
        # Strip leading YYYY-MM-DD-
        slug_candidates.add(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem))
        # Strip leading NNN_ or NNN-
        slug_candidates.add(re.sub(r"^\d+[_-]?", "", stem))
        # Extract slug AFTER an embedded YYYY-MM-DD- (letters convention)
        m = re.search(r"\d{4}-\d{2}-\d{2}-(.+)$", stem)
        if m:
            slug_candidates.add(m.group(1))
        candidates = {p, base, stem} | slug_candidates
        # Also match forward-slash / backslash variants of the path.
        candidates.add(p.replace("\\", "/"))
        candidates.add(p.replace("/", "\\"))
        for c in candidates:
            if c and len(c) > 8 and c in reply:
                referenced.append(p)
                break

    row = {
        "ts": time.time(),
        "surfaced_ts": ts_surfaced,
        "surfaced_count": len(paths),
        "referenced_count": len(referenced),
        "surfaced": paths,
        "referenced": referenced,
        "tally": f"{len(referenced)}/{len(paths)}",
    }
    try:
        _HOME.mkdir(parents=True, exist_ok=True)
        with _TALLY_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass
    return row


def summary(days: int = 7) -> dict:
    """Return summary stats over the last N days from the tally log."""
    if not _TALLY_LOG.exists():
        return {"turns": 0, "surfaced_total": 0, "referenced_total": 0, "ratio": None}
    cutoff = time.time() - days * 86400
    turns = 0
    surfaced_total = 0
    referenced_total = 0
    try:
        for line in _TALLY_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if float(row.get("ts", 0)) < cutoff:
                continue
            turns += 1
            surfaced_total += int(row.get("surfaced_count", 0))
            referenced_total += int(row.get("referenced_count", 0))
    except OSError:
        pass
    ratio = (referenced_total / surfaced_total) if surfaced_total else None
    return {
        "turns": turns,
        "surfaced_total": surfaced_total,
        "referenced_total": referenced_total,
        "ratio": ratio,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: retrieval_tally.py summary [--days N]")
        print("       retrieval_tally.py check <reply-file>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "summary":
        days = 7
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            if idx + 1 < len(sys.argv):
                days = int(sys.argv[idx + 1])
        s = summary(days=days)
        print(json.dumps(s, indent=2))
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("check needs a reply-file path", file=sys.stderr)
            sys.exit(1)
        reply = Path(sys.argv[2]).read_text(encoding="utf-8")
        row = check_reply(reply)
        print(json.dumps(row, indent=2) if row else "no marker present")
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
