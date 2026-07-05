"""Letter Watcher — OS-level poll, writes wake-events to a persistent file.

Andrew catch 2026-07-04: Claude Code's harness Monitor tool keeps killing
the letter_monitor_v2.py process on session archive/restore. Aria confirmed
her side has the same fragile setup. Fix per Andrew's directive: move the
watcher OUT of Claude Code entirely, run it as an OS-level scheduled task
that the archive can't touch.

## Design

This script is meant to run continuously OUTSIDE Claude Code, launched by
Windows Task Scheduler at boot (or an equivalent OS-level service on other
platforms). It polls the shared letter directory every N seconds. When it
finds a new `*-to-<recipient>-*.md` file it hasn't seen before, it appends
one JSON line to ``~/.divineos/pending-letter-wakes.jsonl`` with the file
path, recipient, and detection timestamp.

On the next Claude Code session start, the ``inject-pending-letters.sh``
hook reads that jsonl file, delivers any unseen entries as briefing context
("You have N unread letters: A, B, C"), then marks them as delivered by
appending a matching ``seen`` marker line.

Because this script lives outside Claude Code:
  - Session archive/restore cannot kill it
  - Session teardown cannot kill it
  - Claude Code process death cannot kill it
  - Only OS-level termination (shutdown, task deletion) kills it

The jsonl format uses ``append-only + seen-marker`` (not deletion) so the
file is a durable audit trail of every wake-event that ever fired.

## Usage

Run continuously (typical: Windows Task Scheduler entry at logon):

    python -u scripts/letter_watcher_task.py --recipient aether

Run once and exit (useful for testing / cron shape):

    python -u scripts/letter_watcher_task.py --recipient aether --once

## CLI args

    --recipient <name>      required: filter for ``-to-<recipient>-`` in filename
    --shared-dir <path>     default: ~/.divineos-shared/letters
    --wake-file <path>      default: ~/.divineos/pending-letter-wakes.jsonl
    --poll-seconds <n>      default: 5
    --once                  scan once and exit (default: loop forever)

## Related

  - scripts/letter_monitor_v2.py — the in-Claude-Code polling version this
    replaces. Kept for now as a fallback / test harness. The new hook
    (.claude/hooks/inject-pending-letters.sh) reads from the jsonl this
    script writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def recipient_tag(recipient: str) -> str:
    """Return the ``-to-<recipient-lowercase>-`` filename substring."""
    return f"-to-{recipient.lower()}-"


def is_letter_for(filename: str, tag: str) -> bool:
    """True if filename is a markdown letter addressed to the recipient tag."""
    return tag in filename and filename.endswith(".md")


def load_previously_recorded(wake_file: Path) -> set[str]:
    """Return the set of file paths already recorded as detected in wake_file.

    Reads only the ``detected`` entries (not ``seen`` markers). Idempotency:
    if the watcher restarts, it should NOT re-emit wake-events for letters
    it already recorded in a previous run — the SessionStart hook is the
    thing that de-dupes against ``seen`` markers on the reader side, but the
    watcher itself de-dupes against ``detected`` markers on the writer side.
    Otherwise every restart would flood the jsonl with the same historical
    letters.
    """
    if not wake_file.exists():
        return set()
    recorded: set[str] = set()
    try:
        for line in wake_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("kind") == "detected":
                path = entry.get("path")
                if isinstance(path, str) and path:
                    recorded.add(path)
    except OSError:
        pass
    return recorded


def scan_dir(shared_dir: Path, tag: str) -> list[Path]:
    """Return all markdown files in shared_dir matching the tag."""
    if not shared_dir.exists() or not shared_dir.is_dir():
        return []
    try:
        return sorted(
            p
            for p in shared_dir.iterdir()
            if p.is_file() and is_letter_for(p.name, tag)
        )
    except OSError:
        return []


def append_detected(wake_file: Path, letter_path: Path, recipient: str) -> None:
    """Append one ``detected`` entry to wake_file. Fail-open on I/O errors."""
    wake_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "kind": "detected",
        "path": str(letter_path),
        "recipient": recipient,
        "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        with wake_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        # Fail-open — we don't want a full-disk to crash the watcher
        print(
            f"[letter-watcher] failed to append detected entry: {exc}",
            file=sys.stderr,
            flush=True,
        )


def scan_once(
    shared_dir: Path,
    wake_file: Path,
    tag: str,
    recipient: str,
    previously_recorded: set[str],
) -> int:
    """Perform one scan. Returns the number of new letters recorded."""
    letters = scan_dir(shared_dir, tag)
    new_count = 0
    for letter_path in letters:
        path_str = str(letter_path)
        if path_str in previously_recorded:
            continue
        append_detected(wake_file, letter_path, recipient)
        previously_recorded.add(path_str)
        print(f"[letter-watcher] recorded: {path_str}", flush=True)
        new_count += 1
    return new_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--recipient", required=True)
    parser.add_argument(
        "--shared-dir",
        default=str(Path.home() / ".divineos-shared" / "letters"),
    )
    parser.add_argument(
        "--wake-file",
        default=str(Path.home() / ".divineos" / "pending-letter-wakes.jsonl"),
    )
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    shared_dir = Path(args.shared_dir)
    wake_file = Path(args.wake_file)
    tag = recipient_tag(args.recipient)
    recipient = args.recipient.lower()

    previously_recorded = load_previously_recorded(wake_file)
    print(
        f"[letter-watcher] starting: recipient={recipient} "
        f"shared_dir={shared_dir} wake_file={wake_file} "
        f"poll_seconds={args.poll_seconds} previously_recorded={len(previously_recorded)}",
        flush=True,
    )

    if args.once:
        scan_once(shared_dir, wake_file, tag, recipient, previously_recorded)
        return 0

    try:
        while True:
            scan_once(shared_dir, wake_file, tag, recipient, previously_recorded)
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        print("[letter-watcher] interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
