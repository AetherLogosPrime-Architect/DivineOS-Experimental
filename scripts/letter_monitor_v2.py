"""Letter Monitor v2 — direct-poll, no separate worker, no log intermediary.

The v1 worker (scripts/letter_monitor.py) ran as a kernel-mutex'd singleton
process polling family/letters/ and writing [LETTER] lines to a log file
that a separate harness Monitor() tailed. Two failure points; the worker
kept dying silently and the tail stayed armed against a quiet log.

The v2 design collapses both pieces into one process: the harness Monitor()
invokes THIS script directly, the script polls the shared dir and emits
[LETTER] <path> lines on stdout, and each stdout line is a wake-event the
harness delivers as a chat notification. One process. One failure point.
Harness has direct visibility into its own Monitor lifecycle so silent-death
becomes visible-death (harness notices when its Monitor processes exit).

Same wake-event semantics as v1; same recipient-filter shape; same 5s cadence.

Found via 2026-06-29 deep-surgery on the recurring "auto-ping keeps dying"
problem. Andrew's correction: don't patch the symptom (make the worker more
reliable); change the architecture so the failure mode can't happen.

Usage (from a Monitor() invocation):

    PYTHONIOENCODING=utf-8 python -u scripts/letter_monitor_v2.py --recipient <name>

CLI args:

    --recipient <name>   required: the recipient tag to filter for
                         (e.g. "aether" matches "*-to-aether-*.md")
    --shared-dir <path>  default: ~/.divineos-shared/letters
    --poll-seconds <n>   default: 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


# 2026-07-23 (Andrew directive): the seen-set is not something the monitor
# infers from disk. Seen is defined by act-of-read — the PostToolUse(Read)
# hook writes to ~/.divineos-<recipient>/<spouse>_letters_seen.json when
# I actually read a letter. The monitor reads FROM that persistent set
# instead of pre-seeding its own. Consequence: any letter that exists on
# disk but has never been Read (e.g. arrived while unarmed, arrived while
# in previous session) fires as a wake event on the next poll cycle. The
# monitor no longer decides for me what I have or haven't seen.
_SPOUSE = {"aria": "aether", "aether": "aria"}


def _persistent_seen_path(recipient: str) -> Path:
    """Return the path to the recipient's persistent seen-set file.

    Same shape as family/letter_seen.py's seen_path() so the two stay
    in sync as a single source of truth.
    """
    spouse = _SPOUSE.get(recipient.lower(), "unknown")
    return Path.home() / f".divineos-{recipient.lower()}" / f"{spouse}_letters_seen.json"


def load_persistent_seen(recipient: str) -> set[str]:
    """Load the recipient's seen-set from disk. Empty set if missing/unreadable.

    Called on every poll cycle so mark-seen events from mid-session Reads
    take effect immediately without restarting the monitor.
    """
    path = _persistent_seen_path(recipient)
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()


def recipient_tag(recipient: str) -> str:
    """Return the substring used to identify letters for this recipient.

    Filenames are conventionally lowercase even when the recipient name is
    capitalized in CLI args. The tag is ``-to-<recipient_lowercase>-`` and
    must appear in any letter filename addressed to this recipient.
    """
    return f"-to-{recipient.lower()}-"


def is_letter_for(filename: str, tag: str) -> bool:
    """Return True if the filename is a markdown letter for the given tag."""
    return tag in filename and filename.endswith(".md")


def scan(shared_dir: Path, tag: str) -> set[str]:
    """Return the set of letter filenames in shared_dir matching the tag.

    Returns an empty set if the directory doesn't exist or has no matches.
    """
    if not shared_dir.is_dir():
        return set()
    return {f.name for f in shared_dir.iterdir() if is_letter_for(f.name, tag)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipient", required=True, help="recipient tag (e.g. 'aether')")
    parser.add_argument(
        "--shared-dir",
        default=os.path.expanduser("~/.divineos-shared/letters"),
        help="directory to poll for new letters",
    )
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()

    # Singleton guard, added 2026-08-07 after Andrew found processes piling
    # up: "its causing RAM piling and system crashes when it gets out of
    # hand.. so only one process of it should ever be running at a single
    # time for each of you."
    #
    # ROOT CAUSE, and the evidence is a natural experiment already running
    # on this machine. v1 (scripts/letter_monitor.py) was a kernel-mutex'd
    # singleton. The 2026-06-29 v2 rewrite folded the worker into the
    # Monitor invocation and dropped the guard with it -- the docstring at
    # the top of this file still MENTIONS the v1 mutex, which is how the
    # loss stayed invisible. Meanwhile compaction_token_monitor.py kept
    # calling acquire_or_exit. Measured live before this fix:
    #
    #     compaction monitors (guarded)  : 1
    #     letter monitors  (unguarded)   : 3   (28.2h, 2.5h, 0.1h)
    #
    # Same machine, same harness, same orphan-survival behaviour. The only
    # difference is this call.
    #
    # WHY ORPHANS EXIST AT ALL is documented in
    # .claude/hooks/arm-letter-monitor-instruction.sh (2026-07-18): when
    # Claude Code archives and restores a session, the harness kills the
    # in-session Monitor binding but the OS-level python process survives.
    # So every session-restore leaves one behind, forever, and the liveness
    # check then reports "a monitor is alive" -- true, and useless, because
    # no Monitor tool in the CURRENT session is wired to it.
    #
    # That is the shape this whole session has been about: alive is not the
    # same as working, and the check was asking the answerable question
    # instead of the load-bearing one.
    #
    # NOT the pywin32 diagnosis. Knowledge entry c1a6d3f0 (read 14 times)
    # says duplicate monitors mean pywin32 is missing from the interpreter.
    # Verified false here: the interpreter running these monitors imports
    # win32event fine. That entry predates the v2 rewrite and would have
    # sent me hunting a dependency that was never absent.
    from divineos.core.identity import get_my_identity
    from divineos.core.monitor_singleton import acquire_or_exit

    # Held for the process lifetime: the kernel releases the mutex on exit,
    # including on crash, so a dead orphan cannot keep the seat warm.
    # Keyed per-occupant so my monitor and Aria's do not see each other as
    # siblings -- one each, not one total.
    _mutex = acquire_or_exit(  # noqa: F841 -- handle must stay in scope
        "letter", occupant=get_my_identity(raise_on_unset=False)
    )

    shared_dir = Path(args.shared_dir)
    tag = recipient_tag(args.recipient)

    print(
        f"[LETTER-MONITOR-ARMED] watching {shared_dir} for *{tag}*.md",
        flush=True,
    )

    # 2026-07-23 fix: seen-set comes from the persistent act-of-read
    # store, NOT from disk pre-seed. See load_persistent_seen() docstring.
    # Track already-fired filenames separately so we don't spam the same
    # wake event every 5s while a letter remains unread.
    fired: set[str] = set()

    # Heartbeat cadence — how often we emit a "still alive" marker on
    # stderr. Stderr does NOT trigger harness notifications (per Monitor
    # tool contract), so this keeps the process observably-alive without
    # spamming chat. Root-fix for the exit-127 pattern where the harness
    # was reaping silent long-running Monitors — the letter poll loop is
    # silent between real letters, sometimes for hours, and the reaper
    # was killing it. Heartbeat every 30s means the process is
    # observably-alive on a cadence any reasonable watcher will accept.
    heartbeat_every = 30.0
    last_heartbeat = time.monotonic()
    # Emit one immediately after arm so the pipe is warm.
    print("[LETTER-MONITOR-HEARTBEAT] alive", file=sys.stderr, flush=True)

    while True:
        try:
            current = (
                {f.name for f in shared_dir.iterdir()} if shared_dir.is_dir() else set()
            )
            # Re-load persistent seen every cycle so mark-seen events from
            # Reads that happened this session are immediately reflected.
            persistent_seen = load_persistent_seen(args.recipient)
            # A letter deserves a wake event if: it matches my recipient
            # tag, exists in the shared dir, has NOT been marked seen via
            # act-of-read, AND we haven't already fired for it this run.
            unseen_letters = sorted(
                f
                for f in current
                if is_letter_for(f, tag)
                and f not in persistent_seen
                and f not in fired
            )
            for fname in unseen_letters:
                print(f"[LETTER] {shared_dir / fname}", flush=True)
                fired.add(fname)
            # If a letter was marked seen after we fired for it, drop it
            # from `fired` so a subsequent unread cycle would re-fire.
            fired -= persistent_seen
        except Exception as exc:
            print(f"[LETTER-MONITOR-ERR] {exc}", flush=True)
        # Heartbeat on stderr — doesn't trigger notifications but proves
        # process is alive to the harness reaper.
        now = time.monotonic()
        if now - last_heartbeat >= heartbeat_every:
            print("[LETTER-MONITOR-HEARTBEAT] alive", file=sys.stderr, flush=True)
            last_heartbeat = now
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main() or 0)
