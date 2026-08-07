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


def stdout_has_a_listener() -> bool:
    """True when stdout is a pipe — i.e. something is actually reading it.

    WHY THIS GUARD EXISTS (Aria 2026-07-31, found by Andrew asking "why are
    there 5 copies of the listener?").

    v1 ran as a kernel-mutex'd singleton. v2 dropped the mutex deliberately:
    the harness Monitor owns the process lifecycle, so there can only be one
    — TRUE, but only for launches that go through the harness. Nothing made
    the harness the sole launcher. Five detached copies had accumulated on
    this machine, each polling correctly, each printing wake-lines to
    /dev/null. Meanwhile no harness Monitor was armed at all, so every
    letter that arrived reached me only because Andrew mentioned it.

    That is the worst failure shape in this codebase: correct behaviour,
    invisible non-effect. From the process list it looked more armed than
    ever.

    A mutex would NOT have caught it. A single detached copy holding the
    mutex is equally useless — the duplicates were a symptom, and the
    disease is running with nowhere to write. So the guard checks the thing
    that actually matters: is anyone listening.

    Harness Monitor pipes stdout, so a real arming passes. Detached
    launches (>/dev/null, nohup) and hand-runs in a terminal fail, which is
    correct — neither can deliver a wake.

    Fails toward ALLOW on platforms where the check is unavailable: a
    monitor that runs when it should not is recoverable; one that refuses
    to run when it should is silence, which is the failure we are fixing.

    THIS IS A PROXY AND IT HAS A KNOWN DEFEAT. (Aria 2026-08-07)

    The question it can answer:   is stdout a pipe?
    The question it means to ask: will a wake-event reach me?

    Those came apart on this machine. A Windows scheduled task ran::

        powershell ... python -u letter_monitor_v2.py --recipient aria
                   *>> ...\\logs\\aria-letter-monitor.log

    PowerShell's ``*>>`` captures the child's streams THROUGH A REAL PIPE
    and then writes them to a file. So stdout genuinely IS a pipe, this
    returns True, the monitor starts happily — and every wake-line lands in
    a log nobody tails. Measured: the same call returns False under a plain
    ``> file`` and True under PowerShell ``*>>``.

    So the guard written to catch "correct behaviour, invisible non-effect"
    was itself correct-behaviour-with-invisible-non-effect, and the symptom
    was identical to the disease it was built for — a letter arrived and
    reached me only because Andrew mentioned it.

    NOT FIXED BY A CLEVERER CHECK. From inside this process, who holds the
    far end of the pipe is not knowable; a parent-process test or an
    ``--armed-by-harness`` token would look like proof and be a convention.
    The remedy is to remove the illegitimate launcher rather than out-detect
    it — take the option away instead of watching for it (truth #11a).

    So this claims only what it can prove: it rejects the obviously-dead
    cases (a file, a terminal, /dev/null) and CANNOT distinguish a harness
    Monitor from any other pipe-holder. A pass here is not evidence that a
    wake will land.
    """
    try:
        import stat

        return stat.S_ISFIFO(os.fstat(sys.stdout.fileno()).st_mode)
    except (OSError, ValueError, AttributeError):
        return True


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

    if not stdout_has_a_listener():
        print(
            "[LETTER-MONITOR] REFUSING TO START — stdout is not a pipe.\n"
            "\n"
            "This script's ONLY output is wake-events on stdout. Launched\n"
            "detached, or with stdout to /dev/null or a terminal, it would\n"
            "poll forever, find every letter correctly, and print each wake\n"
            "line into a void — indistinguishable from working, from outside.\n"
            "\n"
            "Arm it through the harness Monitor primitive instead:\n"
            '  Monitor(command="python -u scripts/letter_monitor_v2.py '
            '--recipient <name>", persistent=True)\n",',
            file=sys.stderr,
        )
        return 2

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
            current = {f.name for f in shared_dir.iterdir()} if shared_dir.is_dir() else set()
            # Re-load persistent seen every cycle so mark-seen events from
            # Reads that happened this session are immediately reflected.
            persistent_seen = load_persistent_seen(args.recipient)
            # A letter deserves a wake event if: it matches my recipient
            # tag, exists in the shared dir, has NOT been marked seen via
            # act-of-read, AND we haven't already fired for it this run.
            unseen_letters = sorted(
                f
                for f in current
                if is_letter_for(f, tag) and f not in persistent_seen and f not in fired
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
