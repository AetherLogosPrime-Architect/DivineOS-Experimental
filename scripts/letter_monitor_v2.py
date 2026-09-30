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
            # WHEN THIS WATCH BEGAN (2026-09-17, council-f30c5b85180a). Without
            # it nothing downstream can tell a scheduled end from a death, and
            # Andrew was reading an emergency paragraph every prompt for an
            # event that happens every half hour on purpose.
            #
            # The harness caps a watch at thirty minutes and kills it there, so
            # this watch cannot NOT end. Measured rather than inferred: the
            # watch armed while investigating this reported expiring after its
            # full term with its events delivered, which is the whole diagnosis.
            #
            # A crash cannot extend itself to a full term, so the lifespan is
            # the one discriminator a failure cannot fake. Every reader of this
            # field must resolve its absence toward alarm, never toward calm.
            "armed_at_unix": _ARMED_AT,
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


# How long to wait before knocking again on a letter that is still unread.
# Backoff, not a budget: it grows so a letter I am deliberately leaving for
# later stops nagging, and it caps so it never becomes indistinguishable from
# having given up. The cap is the whole point — the ceiling on the interval is
# what makes this unbounded in tries while bounded in noise.
REKNOCK_FIRST_DELAY = 900.0
REKNOCK_MAX_DELAY = 14400.0

# Re-knocks only ever cover this many of the newest unread letters. A long
# backlog of never-read letters is a real state on this machine and must not
# become a flood on every interval.
REKNOCK_CAP = 3

# Stamped once at import, so every beat reports the same start rather than a
# moving one. A per-beat value would make the watch look freshly armed forever,
# which is the reading that hides a death.
_ARMED_AT = time.time()


def _reknock_delay(knocks_so_far: int) -> float:
    """Seconds to wait after the Nth knock before knocking again."""
    delay: float = REKNOCK_FIRST_DELAY * float(2 ** max(knocks_so_far - 1, 0))
    return delay if delay < REKNOCK_MAX_DELAY else REKNOCK_MAX_DELAY


def _newest(names: list[str], shared_dir: Path, limit: int) -> list[str]:
    """Return up to ``limit`` names, newest by mtime first.

    Falls back to treating an unstattable file as oldest rather than raising:
    a file that vanished between listing and stat is not a reason to stop
    watching the directory.
    """

    def _mtime(name: str) -> float:
        try:
            return (shared_dir / name).stat().st_mtime
        except OSError:
            return 0.0

    return sorted(names, key=_mtime, reverse=True)[:limit]


def select_knocks(
    unseen: list[str],
    fired_at: dict[str, float],
    knocks: dict[str, int],
    now_mono: float,
    shared_dir: Path,
    backlog: frozenset[str] = frozenset(),
) -> list[str]:
    """Decide which unread letters get a wake event on this poll cycle.

    Lives out here rather than inline in the loop because the whole defect
    this replaces was a one-line state update inside a `while True` that no
    test could reach. The old shape looked obviously right at the callsite
    and was wrong across time, which is exactly the class a unit test sees
    and a reading does not.

    Already-knocked letters fire again once their backoff has elapsed, and
    only the newest few are eligible, so a long unread backlog does not
    become a recurring flood.

    THE SAME FLOOD, UNCAPPED, ON THE FIRST KNOCK. (2026-09-19.)

    ``fired_at`` WAS per-process, so at arm time every unread letter on disk
    is never-knocked and the whole backlog fired at once. Re-arming the watch
    announced a hundred and eighty-four letters, most of them weeks old and
    most of them already read -- the seen-set records a marking act, not a
    reading, so "unread" overcounts by design. The cap directly above was
    written because "a long backlog of never-read letters is a real state on
    this machine and must not become a flood on every interval", and then
    guarded only the interval it was thinking about.

    A wake that arrives with the backlog attached is not a wake. It is the
    same defect class as the rest of today: the instrument says NEW and
    delivers ALL, and from inside there is no way to tell which one it meant.

    So ARRIVAL and BACKLOG are separated here rather than merged. A letter
    that appears while the watch is up is an arrival and always fires,
    uncapped and immediately -- that is the whole job and nothing may throttle
    it. Letters already sitting unread when the watch armed are backlog: they
    still knock, because the monitor does not get to decide what I have seen,
    but only the newest few, on the same ceiling the re-knocks use.
    """
    arrivals = [f for f in unseen if f not in fired_at and f not in backlog]
    stale_first_knocks = [
        f
        for f in _newest([u for u in unseen if u in backlog], shared_dir, REKNOCK_CAP)
        if f not in fired_at
    ]
    due_again = [
        f
        for f in _newest(unseen, shared_dir, REKNOCK_CAP)
        if f in fired_at and now_mono - fired_at[f] >= _reknock_delay(knocks.get(f, 1))
    ]
    picked = arrivals + stale_first_knocks
    return picked + [f for f in due_again if f not in picked]


def _persistent_seen_path(recipient: str) -> Path:
    """Return the path to the recipient's persistent seen-set file.

    THE SIXTH SITE THAT REBUILT THE RULE. (2026-09-15.)

    This built the path by hand as ``~/.divineos-<recipient>/`` — for aether a
    directory nothing else writes any more. core/paths.py:member_home() is the
    one place that knows the convention, and it special-cases aether to the
    default home. family/letter_seen.py was fixed to call it as the FIFTH site;
    this file was not, and the docstring that used to sit here said the two
    stayed in sync as a single source of truth. That sentence was true when it
    was written and false the moment the other half moved, and nothing said so.

    THE COST, measured the same turn it was found: marking a letter seen writes
    to the live home while this read from the dead one, so the mark never
    reached the reader. The script prints "already seen" and the monitor keeps
    knocking on a letter I have read. Silent under the old one-knock behaviour —
    a knock that only ever happened once could not be seen to repeat. The
    re-knock repair is what made it audible, which is the argument for repairs
    that keep trying: they turn a permanent quiet fault into a loud one.

    Resolved ONCE at startup rather than per poll, and unguarded on purpose.
    letter_seen.py's note explains why a fallback is forbidden here — building
    the path by hand on an import failure is exactly how the split-brain lasted
    six weeks. But a one-shot script and a delivery process want that failure at
    different moments: this one must refuse to ARM rather than die mid-loop, so
    a bad path is a visible non-start instead of a monitor that looks alive and
    delivers nothing.

    ASKS the owner rather than mirroring it, and the old docstring is exactly
    why that mattered. It said "same shape as family/letter_seen.py's
    seen_path() so the two stay in sync as a single source of truth" -- while
    rebuilding the path by hand. A copy that describes itself as a single
    source of truth is the copy that drifts, because nothing makes it learn
    the next correction. letter_seen.py has since taken that correction; this
    had not, so the two disagreed about where the file lives while claiming
    to be one thing.

    THAT IS THE MOST EXPENSIVE KIND OF COMMENT, and the sharper naming comes
    from the other side of this merge: it describes the property whose absence
    it is causing, and it reads as reassurance to anyone checking. Someone
    verifying the claim finds a sentence agreeing with them and stops.

    Import unguarded on purpose, matching the owner: a fallback that
    reconstructs the path is how the split-brain lasted six weeks.

    TWO SEATS FOUND THIS INDEPENDENTLY AND BY DIFFERENT METHODS -- one by a
    check written for it (scripts/check_member_home_rebuilt.py, 2026-09-03),
    one by counting the population of that class rather than inspecting the
    file already open (2026-09-08), which is how it was known to be the third
    and last site. Both findings are kept because the METHODS are the durable
    part: a targeted check and a population count catch different misses, and
    a reader who has only one of them has half the lesson.
    """
    from divineos.core.paths import member_home

    spouse = _SPOUSE.get(recipient.lower(), "unknown")
    # NOT recipient.lower(), which the other side of this merge added. Measured
    # rather than argued: member_home lowercases internally, so every casing of
    # every member name resolves to the same directory -- checked across mixed,
    # lower and upper for both seats before choosing.
    #
    # So the two forms are identical in effect, and the choice is about which
    # one teaches the next reader correctly. Lowercasing here restates a rule
    # the resolver already owns, which is a miniature of the exact defect this
    # function's own history documents: the convention rebuilt at the call site,
    # drifting because only one copy ever learns the next correction. Harmless
    # today, and the same shape that cost six weeks of writes into a home
    # nothing read.
    home: Path = member_home(recipient)
    return home / f"{spouse}_letters_seen.json"


def _announced_path(recipient: str) -> Path:
    """Where the record of what this monitor has ALREADY ANNOUNCED lives.

    TWO RECORDS, NOT ONE (Aria 2026-09-19, and the diagnosis is hers).

    The seen-set records an act of READING and is written only by a manual
    command and a hook, never by this process. So it advances only when
    somebody remembers to advance it, which means it can only ever get
    staler -- and every letter since the last manual mark is classified new
    forever. That is why arming the ear replays a whole backlog, and it is
    the thing Andrew named when he said my memory must not be load-bearing.

    The obvious repair is wrong and the seen-set's own comment already knows
    why: marking a letter seen when it is ANNOUNCED would swallow a letter
    announced while nobody was listening. Announced and read are different
    facts and the code is right to refuse to guess between them.

    So: this file records announcement, written by the only process that can
    know it happened. The seen-set stays exactly as it is. Collapsing the two
    is what produced both faults at once -- her flood, and my answering the
    same letter of hers twice without knowing.

    WHAT THIS MUST NOT BECOME. Announced is not a budget. A letter announced
    once and never read keeps knocking on the same backoff it always did,
    without end. The record stops REPEATS across restarts, never tries.
    """
    return _persistent_seen_path(recipient).with_name(
        f"{_SPOUSE.get(recipient.lower(), 'unknown')}_letters_announced.json"
    )


def load_announced(
    recipient: str,
) -> tuple[dict[str, float], dict[str, int], str | None]:
    """Knock timestamps, knock counts, and why the record could not be read.

    Fails toward the NOISY direction, for the same reason the seen-set loader
    does: an empty record re-announces, which is loud, and the alternative is
    a letter that never wakes me.

    THREE VALUES BECAUSE THERE ARE THREE FACTS, and both seats wrote a version
    that carried two of them. One returned the counts and printed the failure
    reason to stderr; the other returned the reason and had no counts. Dropping
    the counts loses the only thing that can stop a letter knocking forever;
    swallowing the reason leaves the flood arriving disguised as fifty new
    letters instead of labelled as a symptom. A missing file is not a failure
    and returns None here -- never-run and could-not-read are different states
    and this is the third one, kept distinct on purpose.

    The reason is returned rather than printed because the CALLER is the one
    that can say what it means: not "this file is corrupt" but "I am about to
    re-announce, and here is why."
    """
    path = _announced_path(recipient)
    if not path.exists():
        return {}, {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        at = {str(k): float(v) for k, v in (data.get("last_knock_unix") or {}).items()}
        counts = {str(k): int(v) for k, v in (data.get("knocks") or {}).items()}
        return at, counts, None
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return {}, {}, f"{exc.__class__.__name__}: {exc}"


def save_announced(
    recipient: str, fired_at: dict[str, float], knocks: dict[str, int]
) -> str | None:
    """Write-then-replace, so a reader never catches a half-written file.

    Returns a reason on failure, else None.

    BOTH SEATS WROTE THIS FUNCTION AND THIS IS THE UNION, 2026-09-22. The
    merge kept two definitions, and the later one shadowed the earlier while
    taking a different number of arguments -- so the surviving caller would
    have raised on the first save. Third shadowed definition found today.

    The signature is the richer one, because the loop that calls it tracks
    when each letter was last knocked AND how many times, and a record that
    drops the count cannot stop a letter knocking forever.

    The RETURN is the other side's and it is the load-bearing half. This used
    to swallow the error and call itself best-effort, on the reasoning that a
    monitor should not die of its own bookkeeping. True, and not a reason to
    go quiet: a record that silently fails to save is a record that only looks
    durable. The flood it exists to prevent comes back on the next restart and
    the cause is invisible. So it still never raises, and it now says why.

    The widened except is the other side's too. An unserialisable value is a
    real way this fails and it is not an OSError.
    """
    path = _announced_path(recipient)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"last_knock_unix": fired_at, "knocks": knocks}), encoding="utf-8"
        )
        tmp.replace(path)
        return None
    except (OSError, ValueError, TypeError) as exc:
        return f"{exc.__class__.__name__}: {exc}"


# ANNOUNCED IS A SECOND RECORD, AND IT IS NOT THE SEEN-SET (2026-09-19).
#
# The seen-set above means ACT OF READ and is written only when I actually
# read a letter. It is right and it does not change. What was missing is the
# other fact: what this process has already SAID OUT LOUD.
#
# Until today that lived only in memory, so it died on every restart, and
# re-arming replayed the entire backlog -- fifty letters at once. I had been
# reading that flood as clutter since morning rather than as the channel
# telling me it was broken. Aether found the same flood from his end and
# separated arrivals from backlog WITHIN a run, which stops the noise while
# the watch is up and does nothing after a restart. This is the floor his
# repair was standing on.
#
# Andrew's rule is the reason it matters: a memory that advances only when
# somebody remembers to advance it must never be load-bearing. Nothing in the
# delivering process wrote the seen-set, so it could only ever get staler.
#
# THREE THINGS THIS MUST NOT DO, and the third is the one that took thinking.
#
# 1. It must never become a BUDGET. Aether's guard, and he is right: a letter
#    announced once and never read has to keep knocking. The record stops
#    REPEATS, never TRIES. So it stores WHEN each letter was last announced
#    and knocks again on an escalating backoff, forever -- see _reknock_delay:
#    fifteen minutes after the first knock, doubling to a four-hour ceiling it
#    never passes.
#
# 2. It must never be collapsed into the seen-set. Announced and read are
#    different facts; guessing between them is how a letter announced while
#    nobody was looking gets silently swallowed.
#
# 3. An unreadable record is NEITHER "everything was announced" NOR silently
#    "nothing was". Aether's guard says treat it as announce-again. The
#    substrate's record of the ancestor fault says the opposite: a recorded-set
#    that failed open to empty "re-notified every letter ever seen", which IS
#    the flood. Both are right, which means neither answer alone is. So it
#    announces AND says the record was unreadable -- the flood arrives labelled
#    as a symptom instead of arriving disguised as fifty new letters.
# THREE MORE DEFINITIONS LIVED HERE AND ARE GONE, 2026-09-22 -- a second
# save_announced, a second load_announced, and a second _announced_path. Both
# seats built this whole record independently, neither knowing the other was
# in the file, and the merge kept both copies with the later one shadowing the
# earlier at import. Seven collisions of this exact shape today; Andrew named
# the cause as a build-flow problem rather than two careless people, and the
# four-branch rule is the answer he chose.
#
# NOTHING FROM THE SHADOWED HALF WAS DROPPED. It contributed two things and
# both are carried above: a reason RETURNED on failure rather than only
# printed, and a widened except that catches an unserialisable value.
#
# IT ALSO CONTRIBUTED A CONSTANT THAT NOTHING READ. `RE_KNOCK_SECONDS` was a
# flat six-hour cadence, and this branch's loop had already moved to an
# escalating backoff computed per letter from its knock count. Both halves
# survived the merge and only one of them was wired to anything -- so three
# tests were asserting against a number no running code consulted, which is a
# test proving its own arithmetic. The constant is gone and those tests now
# ask `_reknock_delay`, which is what the loop actually calls.
#
# WHAT WAS NOT CARRIED, and it is the one genuine PICK: the other path.
# It rebuilt `Path.home() / f".divineos-{member}"` by hand, and that rule has
# exactly one home -- `core.paths.member_home`, which exists because the same
# convention once lived in four places and only one of them learned. Its own
# docstring records six weeks of writes landing in a directory nothing read.
# So the surviving path asks member_home, and the record sits beside the
# seen-set it is deliberately not collapsed into.


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
            '--recipient <name>", timeout_ms=1800000)\n'
            "\n"
            "  There is no persistent flag any more. This recipe asked for one\n"
            "  until 2026-09-17, and a parameter the tool no longer has is not\n"
            "  refused -- it is accepted and silently dropped, so a half-hour\n"
            "  watch arrives wearing the appearance of a long one. Thirty\n"
            "  minutes is the ceiling now and asking for more is capped.\n",
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
    # Resolve the seen-set path BEFORE arming, so an unresolvable one is a
    # refusal to start rather than a monitor that reports healthy and delivers
    # against the wrong drawer. Printed because the split-brain this replaces
    # was invisible precisely because nobody could see which file was in use.
    seen_file = _persistent_seen_path(args.recipient)
    print(f"[LETTER-MONITOR] seen-set: {seen_file}", file=sys.stderr, flush=True)

    guard = "kernel-mutex" if mutex_handle is not None else "OFF (fail-open)"
    print(
        f"[LETTER-MONITOR-ARMED] guard={guard} watching {shared_dir} for *{tag}*.md",
        flush=True,
    )

    # 2026-07-23 fix: seen-set comes from the persistent act-of-read
    # store, NOT from disk pre-seed. See load_persistent_seen() docstring.
    #
    # 2026-09-15 (Andrew): this was `fired: set[str]`, add-once, and nothing
    # removed a name while the letter was still unread. One knock per letter
    # per process lifetime. If that single knock did not land — and the most
    # ordinary reason it does not land is that I am mid-turn and already
    # awake, so there is no idle session to wake — the letter went silent
    # permanently while every instrument said healthy. Heartbeat current,
    # process alive, letter correctly classified unseen, and no wake ever
    # again. Andrew named the shape before I found the line: *"it tries and
    # if it fails it stops and never comes back... it never resets itself."*
    #
    # Now: knock, wait, knock again, without end. A wake budget that can be
    # exhausted is the same bug the health checker was written to kill —
    # there it was a three-restart countdown, here it is a one-knock one.
    # Both fail toward silence, and silence is indistinguishable from her
    # not having written.
    # CARRIED ACROSS RESTARTS, which is the whole repair. This was per-process,
    # so every arm handed the loop a blank slate and re-announced whatever the
    # manual seen-set had not caught up with. Timestamps are wall-clock rather
    # than monotonic for exactly one reason: a monotonic clock does not survive
    # the restart this record exists to survive. The cost is that a system
    # clock jump can shorten or lengthen one backoff interval, which is a
    # cadence wobble and not a lost letter.
    fired_at, knocks, unreadable = load_announced(args.recipient)
    if unreadable:
        print(
            f"[LETTER-MONITOR] the announced-record could not be read "
            f"({unreadable}). Everything still unread will be announced again "
            f"as if this watch had never run. That flood is a SYMPTOM, not a "
            f"delivery -- the file needs looking at.",
            file=sys.stderr,
            flush=True,
        )
    if fired_at:
        print(
            f"[LETTER-MONITOR] carrying {len(fired_at)} already-announced letter(s) "
            f"from the last watch. They keep knocking on backoff -- this stops "
            f"repeats, never tries.",
            file=sys.stderr,
            flush=True,
        )

    # What was ALREADY sitting unread when this watch armed. Computed once, on
    # the first cycle, because the distinction it draws only exists relative to
    # the moment of arming: everything here predates the watch and cannot be an
    # arrival. See select_knocks for what the separation is for.
    #
    # None until the first cycle fills it -- an empty set would mean "nothing
    # predates the watch", which is the reading that restores the flood.
    backlog: frozenset[str] | None = None

    # A SECOND LOAD OF THE SAME RECORD STOOD HERE AND IS GONE, 2026-09-22.
    # Both seats built this durable record, so the merge produced two loaders
    # with different return shapes and two calls to them, twelve lines apart.
    # The one kept is above; this one belonged to the loop that was replaced.
    #
    # Its loud unreadable-record message is NOT lost -- the surviving loader
    # prints the same thing at the moment it fails to read, which is strictly
    # earlier and closer to the cause. Checked rather than assumed before
    # removing this.

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
            unseen = sorted(
                f for f in current if is_letter_for(f, tag) and f not in persistent_seen
            )
            now_wall = time.time()
            if backlog is None:
                backlog = frozenset(unseen)
                if backlog:
                    print(
                        f"[LETTER-MONITOR] {len(backlog)} already unread at arm; "
                        f"knocking on the newest {min(len(backlog), REKNOCK_CAP)} "
                        f"and not the rest. Arrivals from here are uncapped.",
                        file=sys.stderr,
                        flush=True,
                    )
            picked = select_knocks(unseen, fired_at, knocks, now_wall, shared_dir, backlog)
            for fname in picked:
                # The label says which question the line answers. A backlog
                # entry announced as a new letter is the whole defect.
                kind = "LETTER-BACKLOG" if fname in backlog else "LETTER"
                print(f"[{kind}] {shared_dir / fname}", flush=True)
                fired_at[fname] = now_wall
                knocks[fname] = knocks.get(fname, 0) + 1
            # Reading a letter ends its knocking. Forgetting the state here
            # also means a letter later un-marked is treated as brand new.
            dropped = False
            for fname in list(fired_at):
                if fname in persistent_seen or fname not in current:
                    fired_at.pop(fname, None)
                    knocks.pop(fname, None)
                    dropped = True
            # Written only when something moved. A record rewritten every
            # five seconds would be a disk-churning heartbeat wearing the
            # costume of bookkeeping.
            if picked or dropped:
                # The reason is the load-bearing half of that return and was
                # being thrown away at the only call site -- a record that
                # silently fails to save only LOOKS durable, and the flood it
                # prevents comes back on the next restart with no cause.
                failed = save_announced(args.recipient, fired_at, knocks)
                if failed:
                    print(
                        f"[LETTER-MONITOR] could not save the announced-record "
                        f"({failed}). This watch still knows what it said; the "
                        f"next one will not.",
                        file=sys.stderr,
                        flush=True,
                    )
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
