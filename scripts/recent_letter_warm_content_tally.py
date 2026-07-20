"""Stop-hook companion to recent_letter_warm_content_surface.py.

Aether's adversarial-review finding #1 (the biggest one):

  "Right now the hook produces a receipt-that-it-fired. A retrieval-
  tally would produce a receipt-that-I-reached. The gap between those
  two is exactly the sitting-down gap you named. This is the same
  class as Andrew's evidence-bearing-gate principle: every mechanism
  that claims to help must bear evidence that the help landed."

This module IS the evidence-bearing layer. At compose-start, the
surface writes a marker file naming what content it put in front of
Aria. At reply-end (Stop-hook), this module reads the marker AND the
just-sent reply text, then checks whether the reply overlapped with
the surfaced content.

Overlap check: 5-word shingles. If at least 2 shingles from the
surfaced content appear in the reply verbatim, count as REACHED.
Otherwise: REACH-MISSED. Emit a JSON event either way to a tally log
so the pattern-over-time is observable.

The tally is NOT the fix. It is the observability that makes the
failure visible when it happens. Aria and Andrew can both look at
the tally periodically. If reach-rate is low, the mechanism is not
doing what it claims.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

_TALLY_MARKER = Path(os.environ.get("TEMP", "/tmp")) / "aria_recent_letter_tally.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _tally_log_path() -> Path:
    return _repo_root() / "data" / "recent_letter_reach_tally.jsonl"


def _words(text: str) -> list[str]:
    """Lowercased word tokens, punctuation stripped."""
    return re.findall(r"[a-zA-Z][a-zA-Z']+", text.lower())


def _shingles(words: list[str], n: int = 5) -> set[tuple[str, ...]]:
    """Return the set of n-grams (as tuples) from a list of words."""
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def check_overlap(
    surfaced_content: list[str], reply_text: str, shingle_size: int = 5
) -> tuple[bool, int, int]:
    """Return (reached, matched_shingles, total_surfaced_shingles).

    reached = True iff at least 2 shingles from any surfaced-content
    chunk appear in the reply text.
    """
    reply_words = _words(reply_text)
    reply_shingles = _shingles(reply_words, shingle_size)

    total_surfaced_shingles = 0
    matched = 0
    for chunk in surfaced_content:
        chunk_words = _words(chunk)
        chunk_shingles = _shingles(chunk_words, shingle_size)
        total_surfaced_shingles += len(chunk_shingles)
        matched += len(chunk_shingles & reply_shingles)

    return (matched >= 2, matched, total_surfaced_shingles)


def read_marker() -> dict | None:
    """Read the compose-start marker if present. Returns None if
    missing or unreadable."""
    if not _TALLY_MARKER.exists():
        return None
    try:
        return json.loads(_TALLY_MARKER.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def clear_marker() -> None:
    """Remove the marker after processing so it does not double-count."""
    try:
        _TALLY_MARKER.unlink(missing_ok=True)
    except OSError:
        pass


def write_tally_event(event: dict) -> None:
    """Append the event to the JSONL tally log."""
    path = _tally_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass  # fail-open


def process(reply_text: str) -> dict | None:
    """Read marker, check overlap against reply_text, log event, clear
    marker. Returns the event dict (or None if no marker was present).
    """
    marker = read_marker()
    if not marker:
        return None

    surfaced = marker.get("surfaced_content", []) or []
    if not surfaced:
        clear_marker()
        return None

    reached, matched_shingles, total = check_overlap(surfaced, reply_text)

    event = {
        "timestamp": time.time(),
        "marker_timestamp": marker.get("timestamp"),
        "content_hash": marker.get("content_hash"),
        "letter_filenames": marker.get("letter_filenames", []),
        "reached": reached,
        "matched_shingles": matched_shingles,
        "total_surfaced_shingles": total,
    }
    write_tally_event(event)
    clear_marker()
    return event


def format_stop_hook_message(event: dict) -> str:
    """Return a short user-facing message summarizing the tally result.
    Used by the Stop-hook when we want the reach-miss to be loud."""
    if event["reached"]:
        return (
            "[recent-letter tally] REACHED — reply overlapped with "
            f"{event['matched_shingles']} shingles from surfaced letter content."
        )
    return (
        "[recent-letter tally] REACH-MISSED — surfaced content was in "
        "compose-context but the reply did not overlap with any of it. "
        "The shelf was visible; I turned away. Logged to "
        f"{_tally_log_path().relative_to(_repo_root())}."
    )


def main() -> int:
    """Entry-point when called from a Stop-hook. Reads the reply text
    from stdin (Claude Code stop-hook contract) and processes it."""
    try:
        reply_text = sys.stdin.read()
    except OSError:
        return 0

    event = process(reply_text)
    if event is None:
        return 0  # nothing to tally
    # Only emit visible feedback on reach-miss — reached is the quiet path.
    if not event["reached"]:
        print(format_stop_hook_message(event))
    return 0


if __name__ == "__main__":
    sys.exit(main())
