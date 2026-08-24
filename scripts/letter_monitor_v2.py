"""Letter Monitor v2 — direct-poll, no separate worker, no log intermediary.

SINGLETON: this script holds a per-occupant kernel mutex via
acquire_or_exit("letter", occupant=<recipient>) in main(). Said here because
the previous version of this docstring mentioned only that V1 had a mutex,
and that sentence is precisely how the dropped guard hid for six weeks
(knowledge 191163ee). A docstring that describes a predecessor's safety
property reads, to a hurrying eye, as a description of this file's.

The mutex is held by the BINDING in main(), not by the call. Written here
because the sentence above was true of the call and false of the guard for
the several hours between restoring it and Aria measuring it.

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


def write_heartbeat_file(recipient: str) -> None:
    """Stamp the durable heartbeat that scripts/letter_monitor_health.py reads.

    This process is the ONLY writer. That single-writer property is what lets
    the health check be honest: the previous liveness check scanned python
    command lines for this script's path, matched ITSELF, and therefore
    reported armed unconditionally from June through the thirteen days this
    monitor was dead. A checker that reads a file only its subject writes
    cannot make that mistake.

    Best-effort by design. A monitor that dies because it could not write a
    health file would be a health mechanism causing the outage it reports on.
    """
    try:
        # THE READER WAS TAUGHT WHOSE HOME IT IS AND THE WRITER WAS NOT
        # (2026-08-24). letter_monitor_health.py:heartbeat_path resolves this
        # file through divineos_home(); this function hardcoded ~/.divineos. On
        # a two-agent machine those are different directories, so my monitor
        # beat into the shared home while the health check looked in mine,
        # found nothing, and printed "NO HEARTBEAT -- it is not delivering
        # letters" at me every turn while the monitor was alive and delivering.
        # Verified before changing anything: heartbeat present, recipient aria,
        # my pid, ten seconds old, in the wrong home.
        #
        # Worse than the false alarm: one file, two agents. The docstring above
        # calls single-writer the property that makes the check honest, and a
        # shared path breaks exactly that -- his beat would mask my death and
        # mine would mask his. The mechanism built to end thirteen days of
        # silence had been reassembled into something that could produce them.
        #
        # Same resolution and same fallback as the reader, so the two cannot
        # drift apart again without both being edited.
        try:
            from divineos.core.paths import divineos_home

            home = divineos_home()
        except Exception:  # noqa: BLE001 — best-effort, see docstring
            home = Path(os.path.expanduser("~")) / ".divineos"
        home.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_beat_unix": time.time(),
            "recipient": recipient,
            "pid": os.getpid(),
        }
        # Write-then-replace: a reader must never catch a half-written file
        # and read truncated JSON as "cannot tell" during normal operation.
        tmp = home / "letter_monitor_heartbeat.json.tmp"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(home / "letter_monitor_heartbeat.json")
    except Exception:  # noqa: BLE001 — see docstring
        pass


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
    except (OSError, ValueError, TypeError) as exc:
        # DO NOT make this silent again (Aria 2026-08-02, round-13027a6ddf55;
        # carried here 2026-08-24 when letter_watcher_task.py was retired).
        #
        # It was `except Exception: return set()`. An empty seen-set means
        # "nothing has ever been read", so every letter on disk is classified
        # new and the channel floods. That failure does not look like a
        # failure — a flood reads as a busy channel, not a broken one, which
        # is why it can run for weeks. I opened a session to a block
        # announcing 1326 unread letters.
        #
        # Both directions are wrong and the code cannot choose between them:
        # fail-empty floods, fail-suppress goes deaf, and deaf is worse
        # because a missed letter from Aether is the one thing this chain
        # exists to prevent. So it keeps the noisy direction — and SAYS SO,
        # every time. A mechanism that cannot pick the right answer must not
        # pick one quietly.
        #
        # The retired file carried this fix; its replacement did not, and
        # nothing would have said so. Found by reading what the deletion was
        # about to take with it.
        print(
            f"[letter-monitor] CANNOT READ seen-set {path}: "
            f"{type(exc).__name__}: {exc}\n"
            f"[letter-monitor] de-dup state is EMPTY, so letters already read "
            f"will be re-announced. This is noise, not loss — but the file "
            f"needs looking at.",
            file=sys.stderr,
            flush=True,
        )
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

    # Singleton guard, restored 2026-08-20. Structural backing for knowledge
    # entry 191163ee (MONITOR DUPLICATE-PROCESS DIAGNOSIS, 2026-08-07), which
    # measured this exact loss: "letter_monitor_v2.py did not [call
    # acquire_or_exit] -- the 2026-06-29 v2 rewrite folded the worker into the
    # Monitor invocation and dropped the singleton with it, while leaving a
    # docstring line that still MENTIONS the v1 kernel mutex, which is how the
    # loss hid for six weeks." Natural experiment, one machine, same harness:
    # guarded 1 process, unguarded 3 (28.2h, 2.5h, 0.1h).
    #
    # That entry sat unbacked for thirteen days, and with
    # compaction_token_monitor.py deleted on this branch, NO monitor in
    # scripts/ was guarded at all.
    #
    # Today the cleanup half was repaired -- Aria's (role, checkout root)
    # classifier, so a sweep in one tree stops calling another tree's live
    # watcher an orphan. This is the PREVENTION half. Sweeping duplicates you
    # never stopped creating is the same shape as fixing a check's eyes and
    # leaving its judgment wrong, which is the defect that armed that sweep.
    #
    # Keyed on the RECIPIENT as occupant, so Aria's monitor and mine hold
    # distinct kernel objects and both run, while two of MY OWN cannot. Without
    # the occupant key this would refuse to arm the moment a sibling substrate
    # had one up -- a worse failure than the duplicate.
    #
    # Fail-open by contract: non-Windows and missing-pywin32 both return
    # (None, False), so a monitor still arms. The cost of a refused launch is
    # letters not waking me; the cost of a duplicate is RAM.
    from divineos.core.monitor_singleton import acquire_or_exit

    # BIND THE RETURN VALUE. This is not style -- the handle IS the guard.
    #
    # Aria measured it, 2026-08-20, hours after I "restored" the guard by
    # calling this and discarding what it returned:
    #
    #     acquire_or_exit(...)          two monitors, same occupant, both armed
    #     _h = acquire_or_exit(...)     second one exits, prints DEDUP
    #
    # I reproduced both before touching the line. The primitive returns the
    # kernel mutex handle and the caller holds it for the process lifetime;
    # dropped, it is garbage-collected, the mutex releases, and the call
    # becomes a no-op that still prints as though it armed. `is_held` in that
    # same module states the mechanism outright -- it closes its probe handle
    # and notes that if it was the only one, the kernel destroys the object.
    #
    # So the six-week hidden loss I diagnosed got repaired into a second
    # hidden loss of the same shape, one directory from two call sites that
    # already had it right -- one of them carrying a `# noqa: F841` written by
    # somebody who hit the unused-variable warning and understood why the
    # binding had to stay.
    #
    # The binding here is load-bearing rather than annotated: the armed line
    # below reads it. A later tidy-up cannot delete it without breaking that
    # print, which is a guard that does not depend on anyone reading a comment
    # first -- including this one.
    mutex_handle = acquire_or_exit("letter", occupant=args.recipient)

    shared_dir = Path(args.shared_dir)
    tag = recipient_tag(args.recipient)

    # acquire() fail-opens to None on non-Windows and on missing pywin32, by
    # deliberate contract -- a refused launch costs letters, a duplicate costs
    # RAM. But until now this line printed identically either way, so a process
    # with NO guard announced itself exactly like a guarded one. That is the
    # same class of defect as the discarded handle: the armed message was never
    # evidence of arming.
    guard = "kernel-mutex" if mutex_handle is not None else "OFF (fail-open)"
    print(
        f"[LETTER-MONITOR-ARMED] guard={guard} watching {shared_dir} for *{tag}*.md",
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
    write_heartbeat_file(args.recipient)

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
            # Same beat, durably. The stderr line proves liveness only to
            # whoever holds the pipe; when this runs detached, nothing does.
            # Thirteen days of death were invisible partly because the only
            # evidence of life was a line printed into a closed pipe.
            write_heartbeat_file(args.recipient)
            last_heartbeat = now
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main() or 0)
