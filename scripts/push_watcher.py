"""Watch one push, and say in plain words why it failed when the machine itself was the cause.

Dad, 2026-10-22: "this watcher should be mandatory and automatic on any and all pushes.. so if anything fails you
know exactly what and why". 99 push-gate crash recoveries in 17 days, nearly all the same six tests, and the gate's
record named WHICH test a worker was running when it died, never WHAT ended it.

THE SHAPE (walk-193e1c70464f, nine lenses; the design note is docs/drafts/every_push_is_watched_and_a_failure_says_why_
draft_2026-10-22.md). Three simple recorders append to ONE raw log and know nothing of each other: a process sampler,
a config reader (the repository config's `bare` line), and the push's own verdict. A separate assembler builds the
report afterward, so a wrong assembler can be fixed without losing the evidence.

THE FIVE OUTCOMES, never merged (a count of "could not" only means something if these stay apart):
  NAMED          the watcher saw a test worker end while its parent run was still going, or the config change
  TREE_ENDED_EARLY  every test worker ended together before pytest printed its summary: a timeout, an out-of-memory
                 kill or an interrupt (Aether's attack, 2026-10-23); neither NAMED nor NOTHING_SEEN
  NOTHING_SEEN   the watcher ran, took looks, and saw neither; it prints what it cannot see
  WATCHER_FAILED zero looks were taken, so it cannot say anything (never printed as NOTHING_SEEN)
  NOT_MINE       an ordinary failure (a test assertion, a gate refusal, a remote reject): its own output is the answer

ORDER IS BY SAMPLE NUMBER, not seconds: the sampler, the test runner and the file clock disagree by up to a tick, so
"before" means an earlier sample and the same sample is CONCURRENT.

WHAT IT CANNOT SEE, printed with every NOTHING_SEEN: anything that lives under one sampling interval (the MEASURED
mean, not the 0.25 s asked for; the first version really looked once per 2 s), anything that ends before the first
look finishes (about 1 s; a push starts its test workers minutes later, so this is a start-up blind spot, not a
mid-run one), a kill
that leaves no entry in the process list, a failure inside a single process. A named process ending near a death is a
CANDIDATE, never a proven cause: on a busy machine some process always ends in any three seconds.

THE INVARIANT: this watcher's own exit status can never reach the push hook's exit status. It is started in the
background and never waited on for a status; every call from the hook ends in `|| true`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SIGNATURE = "exec(eval(sys.stdin.readline()))"
INTERVAL = 0.25
SETTLE = (
    8  # samples (2 s) after a worker ends in which its parent and a sibling must still be alive
)
AROUND = 12  # samples either side of a death in which other processes are reported as candidates
MAX_WATCH_SECONDS = (
    4 * 3600
)  # no push runs this long; past it the watcher ends itself whatever it can or cannot see
HEARTBEAT_EVERY = (
    4  # one second: the sample count read at the end of a push is at most a second behind
)
RETAIN = 200
MAX_RAW_LINES = 200_000
#: Only these processes are logged besides workers: the ones a push or a test starts and ends.
#: A Python interpreter is recognised by the SHAPE of its name, not by a fixed list (Aletheia, 2026-10-23): on many Linux
#: systems it runs as python3 or python3.12, and a list of {python, python.exe, pythonw.exe} meant the watcher never
#: recognised its test workers there and reported "nothing seen" while blind. Reproduced here under a python3-named
#: interpreter before it was fixed. Anchored whole-name, so "ipython", "python-config" and "pythonic" do not match.
_PYTHON_NAME = re.compile(r"python(?:w)?(?:\d+(?:\.\d+)*)?(?:\.exe)?", re.I)


def is_python_name(name: str) -> bool:
    return bool(_PYTHON_NAME.fullmatch(name or ""))


LOGGED_NAMES = frozenset(
    {
        "git.exe",
        "bash.exe",
        "sh.exe",
        "pytest.exe",
        "cmd.exe",
        "git",
        "bash",
        "sh",
        "dash",
        "pytest",
    }
)

NAMED, NOTHING_SEEN, WATCHER_FAILED, NOT_MINE = (
    "NAMED",
    "NOTHING_SEEN",
    "WATCHER_FAILED",
    "NOT_MINE",
)
TREE_ENDED_EARLY = "TREE_ENDED_EARLY"
#: The watcher could not read the gate's test log at all (no path, or no such file), which is not the same as the log
#: being old. "Tests ran and left no log", "tests never ran" and "I could not look" are three different facts; the
#: third used to be spoken as the second (Aether, reading fd34d0c49: Hoare's three states, again).
COULD_NOT_LOOK = "COULD_NOT_LOOK"
COULD_NOT_READ_FAMILY = "could_not_read_gate_output"

#: Words in a push's own output that mark an ordinary failure. Checked in this order.
_ORDINARY = (
    ("gate_refusal", re.compile(r"\bBLOCKED\b|refus", re.I)),
    ("remote_rejected", re.compile(r"remote rejected|\[rejected\]|failed to push", re.I)),
    ("tests_failed", re.compile(r"\bFAILED\b|\d+ failed", re.I)),
)
#: The MACHINE, not the code, ended or starved the run. Checked BEFORE the ordinary patterns, and in this order: a run
#: that ran out of memory also prints "1 failed", and an ordinary line must never outrank the crash that explains it
#: (Aletheia, 2026-10-23: out-of-memory runs were filed as ordinary test failures, the class that cost Dad his machine).
#: Accepted cost, said so: a real test ABOUT these words that fails for its own reason is called infrastructure too, and
#: lands in "could not tell", which counts against the ceiling: the honest side to be wrong on.
_INFRA_KINDS = (
    (
        "ran out of memory",
        re.compile(r"MemoryError|out of memory|\bOOM\b|Cannot allocate memory", re.I),
    ),
    ("was killed from outside", re.compile(r"^Killed\b|\bSIGKILL\b|^Terminated\s*$", re.I | re.M)),
    ("timed out", re.compile(r"\+{2,} Timeout \+{2,}|Failed: Timeout >|pytest-timeout", re.I)),
    ("ran out of disk space", re.compile(r"No space left on device|\[Errno 28\]", re.I)),
    (
        "crashed",
        re.compile(
            r"Segmentation fault|Fatal Python error|node down|not properly terminated|worker crashed|crash recover",
            re.I,
        ),
    ),
    (
        "lost the network",
        re.compile(
            r"Could not resolve host|Connection (?:refused|reset by peer|timed out)|"
            r"Temporary failure in name resolution",
            re.I,
        ),
    ),
)
_FAMILY_WORDS = {
    "gate_refusal": "a check refused it",
    "remote_rejected": "the remote end turned it away",
    "tests_failed": "a test failed",
    "stopped_before_tests": "a check stopped it before the tests ran",
}


# ---------------------------------------------------------------- the assembler: pure, tested without a machine


def read_raw(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def samples_taken(events: list[dict]) -> int:
    """The heartbeat: the highest sample number any line carries. Zero means the watcher never looked."""
    return max((int(e.get("n", 0)) for e in events), default=0)


def mean_interval(events: list[dict]) -> float:
    """Seconds between looks, MEASURED from the log's own timestamps. The blind spot we print is this number, not the
    interval we asked for: the asked-for 0.25 s was really about 2 s until the planted-fault test showed it."""
    times = [float(e["t"]) for e in events if "t" in e]
    n = samples_taken(events)
    return (max(times) - min(times)) / n if n and len(times) > 1 else 0.0


def real_deaths(events: list[dict], settle: int = SETTLE) -> list[dict]:
    """Workers that ended while their parent run kept going.

    At the normal end of a run the workers and the parent leave together, which the first version of this counted as
    deaths. A real death is a worker gone while its parent AND a sibling worker are still present `settle` samples on.
    """
    last = samples_taken(events)
    ended_at: dict[int, int] = {}
    workers: dict[int, dict] = {}
    for e in events:
        if e.get("k") in ("present", "started") and e.get("worker"):
            workers[int(e["pid"])] = e
        if e.get("k") == "ended":
            ended_at[int(e["pid"])] = int(e["n"])
            if e.get("worker"):
                workers[int(e["pid"])] = e

    def alive_at(pid: int, n: int) -> bool:
        gone = ended_at.get(pid)
        return gone is None or gone > n

    deaths = []
    for pid, n in sorted(ended_at.items(), key=lambda kv: kv[1]):
        info = workers.get(pid)
        if not info or not info.get("worker"):
            continue
        check = min(n + settle, last)
        parent = int(info.get("ppid", 0))
        siblings = [p for p, w in workers.items() if p != pid and int(w.get("ppid", -1)) == parent]
        if alive_at(parent, check) and any(alive_at(s, check) for s in siblings):
            deaths.append({"sample": n, "pid": pid, "ppid": parent})
    return deaths


def around(events: list[dict], sample: int, window: int = AROUND) -> list[dict]:
    """Other processes that started or ended near a sample, each marked before / concurrent / after BY SAMPLE NUMBER."""
    found = []
    for e in events:
        if e.get("k") not in ("started", "ended") or e.get("worker"):
            continue
        n = int(e["n"])
        if abs(n - sample) > window:
            continue
        order = "concurrent" if n == sample else ("before" if n < sample else "after")
        found.append({"order": order, "what": e["k"], "name": e.get("name", ""), "sample": n})
    quiet = quiet_stretch(events)
    for item in found:
        item["usual"] = is_usual(events, item["name"], sample, quiet, window)
    return found


#: Fewer looks than this before the first test worker (10 s at the intended interval) is too little to call anything
#: normal or unusual, and the answer is "unknown", never "usual".
MIN_QUIET = 40


def quiet_stretch(events: list[dict]) -> int:
    """Samples taken before the first test worker appeared. Zero when workers were already there at the first look.

    This is the same-push control (Aether's attack, answering Sagan's lens): no extra sampling on passing pushes, just
    the stretch of THIS push before the tests began, which the watcher has already looked at.
    """
    starts = [int(e["n"]) for e in events if e.get("k") == "started" and e.get("worker")]
    return min(starts) if starts else 0


def is_usual(
    events: list[dict], name: str, sample: int, quiet: int, window: int = AROUND
) -> bool | None:
    """Was this kind of program coming and going at least as often in the quiet stretch as around the death?

    True: yes, so its presence near the death says nothing. False: rarer when quiet, so worth naming. None: not enough
    quiet stretch to judge, which is reported as such and counted as worth naming (never silently as usual).
    """
    if quiet < MIN_QUIET:
        return None
    in_quiet = sum(
        1
        for e in events
        if e.get("k") in ("started", "ended")
        and not e.get("worker")
        and e.get("name") == name
        and int(e["n"]) < quiet
    )
    in_window = sum(
        1
        for e in events
        if e.get("k") in ("started", "ended")
        and not e.get("worker")
        and e.get("name") == name
        and abs(int(e["n"]) - sample) <= window
    )
    return (in_quiet / quiet) >= (in_window / (2 * window + 1))


# Two shapes of pytest's last line. The default draws a bar ("=== 1 failed, 1 passed in 0.3s ==="); under -q,
# which is how the push gate runs it, pytest draws NO bar and the line is bare ("1 failed, 1 passed in 0.3s").
# The first version of this pattern required the bar, so every ordinary failure under the gate read as the
# whole tree ending early (Aether, cold-reading #712, 2026-10-23, reproduced against pytest itself).
# The bare shape is anchored to a line of nothing but counts, so a test that prints "failed in 2s" mid-output
# does not pass for a finished run.
_SUMMARY = re.compile(
    r"^=+ .*\b(passed|failed|error|errors|no tests ran|deselected)\b.* in [\d.]+s"
    r"|^(?:\d+ (?:passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?)(?:, )?)+ in [\d.]+s"
    r"|^no tests ran in [\d.]+s",
    re.I | re.M,
)


def tree_ended_early(events: list[dict], output_tail: str, tests_ran: bool) -> bool:
    """The whole test run ended before pytest printed its summary line: every worker stopped, none was left standing.

    A timeout kill, an out-of-memory kill of the parent or a Ctrl-C ends the tree together, which the lone-death rule
    (a worker gone while its parent and a sibling stay) cannot see. Said differently to Dad from one helper dying.
    """
    if not tests_ran or _SUMMARY.search(output_tail or ""):
        return False
    workers = {
        int(e["pid"]) for e in events if e.get("worker") and e.get("k") in ("present", "started")
    }
    ended = {int(e["pid"]) for e in events if e.get("worker") and e.get("k") == "ended"}
    return bool(workers) and workers <= ended


def config_changes(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("k") == "cfg"]


def classify(exit_code: int, output_tail: str, tests_ran: bool = True) -> str:
    """The family of a failed push, from its own exit code and words. 'passed' for exit 0.

    `tests_ran` is False when the push gate's test log is older than this push: a check stopped the push before the
    tests, and an old log must never be read as this push's words.
    """
    if exit_code == 0:
        return "passed"
    if infra_kind(output_tail):
        return "infrastructure"  # first, so an ordinary FAILED line cannot hide the crash that caused it
    for family, pattern in _ORDINARY:
        if pattern.search(output_tail or ""):
            return family
    if tests_ran is None:
        return COULD_NOT_READ_FAMILY
    return "unknown" if tests_ran else "stopped_before_tests"


def infra_kind(output_tail: str) -> str:
    """Plain words for what the machine did, from the push's own output; '' when it names nothing."""
    for words, pattern in _INFRA_KINDS:
        if pattern.search(output_tail or ""):
            return words
    return ""


def fresh_tail(tail_file: Path | None, events: list[dict]) -> tuple[str, bool | None]:
    """(the test log's tail, whether the tests ran in THIS push). The gate writes one log file that survives pushes, so
    a log not modified since the watcher started belongs to an earlier push and is ignored.

    The second value has THREE states: True (a fresh log: the tests ran), False (the log is older than this push: a check
    stopped it first) and None (no path was given: the watcher could not look, which says nothing about whether the tests
    ran). A path that names no file is False, not None: the gate writes that log when its tests fail, so a failed push
    with no log at a KNOWN path is a push stopped before the tests (the merge gate's own test pinned exactly this)."""
    starts = [float(e["t"]) for e in events if "t" in e]
    if not tail_file or not starts:
        # No timestamp from the watcher means there is nothing to compare the log's age against: freshness cannot be
        # established, so the log is neither trusted nor dismissed (Aether, reading 9f507f0bd: the watcher's own empty
        # log was being spoken as "the tests did not run" for a push whose gate log showed them running).
        return "", None
    if not tail_file.is_file():
        return "", False
    if tail_file.stat().st_mtime < min(starts):
        return "", False
    return tail_file.read_text(encoding="utf-8", errors="replace")[-4000:], True


def assemble(events: list[dict], exit_code: int, output_tail: str, tests_ran: bool = True) -> dict:
    n = samples_taken(events)
    family = classify(exit_code, output_tail, tests_ran)
    deaths = real_deaths(events)
    cfg = config_changes(events)
    tree_early = tree_ended_early(events, output_tail, tests_ran)
    if family == "passed":
        outcome = "PASSED"
    elif deaths or cfg:
        outcome = NAMED
    elif tree_early:
        outcome = TREE_ENDED_EARLY
    elif n == 0 and family != "stopped_before_tests":
        # A push stopped by a check before any test ran is over in under a second, before the first look finishes:
        # zero looks is expected there, and the machine cannot have disturbed tests that never started.
        # This is also where a watcher that wrote nothing lands, even when the log could not be read as well.
        outcome = WATCHER_FAILED
    elif family == COULD_NOT_READ_FAMILY:
        outcome = COULD_NOT_LOOK
    elif family in _FAMILY_WORDS:
        outcome = NOT_MINE
    else:
        outcome = NOTHING_SEEN
    return {
        "outcome": outcome,
        "family": family,
        "infra_kind": infra_kind(output_tail),
        "exit": exit_code,
        "samples": n,
        "mean_interval_s": round(mean_interval(events), 2),
        "deaths": [dict(d, around=around(events, d["sample"])) for d in deaths],
        "config_changes": cfg,
        "truncated": any(e.get("k") == "truncated" for e in events),
        "order_relation": "sample number (earlier sample = before; same sample = concurrent)",
    }


def final_line(report: dict, report_path: str = "") -> str:
    """The one sentence Dad reads at the end of a failed push. Plain words: no process ids, no file names but the path."""
    outcome = report["outcome"]
    where = f" Details for me and Aether: {report_path}" if report_path else ""
    if outcome == "PASSED":
        return ""
    if outcome == WATCHER_FAILED:
        return (
            "The push failed and the watcher never got a look at the machine, so I cannot say what happened."
            + where
        )
    if outcome == TREE_ENDED_EARLY:
        return (
            "The whole test run ended before it finished: every test helper stopped together, which points to a "
            "timeout, the computer running out of memory, or an interruption, not to one helper dying."
            + where
        )
    if outcome == COULD_NOT_LOOK:
        return (
            "I could not read the test log for this push, so I cannot say whether the tests ran or why it failed; "
            "the push's own messages above are all there is." + where
        )
    if outcome == NOT_MINE:
        return (
            f"This push failed the ordinary way ({_FAMILY_WORDS[report['family']]}); the machine itself showed "
            "nothing wrong, so the push's own messages above are the answer." + where
        )
    if outcome == NAMED:
        parts = []
        if report["deaths"]:
            k = len(report["deaths"])
            parts.append(
                f"{k} test helper{'s' if k != 1 else ''} stopped while the test run was still going"
            )
        if report["config_changes"]:
            parts.append("the project's settings file changed during the push")
        around_all = [a for d in report["deaths"] for a in d["around"]]
        near = sum(1 for a in around_all if a.get("usual") is not True)
        if near:
            tail = f", and {near} other programs started or ended right around then (possible causes, not proven)"
        elif around_all:
            tail = ", and other programs came and went around then, but no more than usual for this push"
        else:
            tail = ""
        return (
            f"This push was disturbed by the machine itself: {' and '.join(parts)}{tail}." + where
        )
    gap = report.get("mean_interval_s") or 0.0
    blind = (
        f"anything shorter than about {gap:.1f} seconds"
        if gap
        else "anything that lives only a moment"
    )
    named = report.get("infra_kind") or ""
    lead = (
        f"The push's own output says the machine {named}, not the code, but the watcher did not catch which process "
        "ended."
        if named
        else "I could not tell why this push failed."
    )
    return (
        f"{lead} The watcher looked {report['samples']} times and saw no helper die "
        f"and no settings change, and it cannot see {blind}." + where
    )


def trim_reports(directory: Path, keep: int = RETAIN) -> int:
    """The watcher must not become the thing that fills the disk: drop the oldest reports past `keep`."""
    files = sorted(directory.glob("push-*.json"), key=lambda p: p.stat().st_mtime)
    stale = files[: max(0, len(files) - keep)]
    for path in stale:
        path.unlink(missing_ok=True)
        path.with_suffix(".raw.jsonl").unlink(missing_ok=True)
    return len(stale)


# ---------------------------------------------------------------- the recorders: thin, touch the machine


def _alive(pid: int, created: float | None = None) -> bool:
    """Is the process I was told to follow still THAT process, and running?

    `pid_exists` alone is wrong in two ways, both found on Linux by Aletheia (2026-10-23, the four real-process tests
    timing out) and reproduced here: a killed process nobody has collected yet is a ZOMBIE, which `pid_exists` still
    calls alive (status "zombie"), so the watcher never noticed its hook was gone and would run for ever; and a process
    number can be handed to an unrelated process after the first one ends, so "someone has this number" is not "my
    hook is alive". The start time pins the process I meant; a zombie counts as gone.
    """
    import psutil

    try:
        proc = psutil.Process(pid)
        if proc.status() == psutil.STATUS_ZOMBIE:
            return False  # both-empty: a zombie, a recycled number and an empty slot all mean the hook is gone
        if created is not None and abs(proc.create_time() - created) > 1.0:
            return False  # both-empty: a recycled number is a different process, so the one I followed is gone
        return True
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False  # both-empty: nothing holds that number, which is the same answer as a zombie or a recycled one
    except psutil.Error:
        # COULD NOT LOOK (access denied and the like) is not evidence the hook is gone, and ending the watch on it
        # would silently drop a watched push. The lifetime cap in run() is what stops a watcher that can never tell.
        return True


def _created(pid: int) -> float | None:
    import psutil

    try:
        return psutil.Process(pid).create_time()
    except psutil.Error:
        return None


def _snapshot(known: dict, root: int | None = None) -> dict[int, dict]:
    """Who is running now. Names are cheap (0.01 s for 330 processes); reading each command line costs about 6 ms and
    made ONE look take 2 s on this machine, so the 'quarter second' sampler was really one look every two seconds
    (found by the planted-fault test, 2026-10-23). A command line is therefore read once per new python process and
    remembered by (pid, start time); everything else is judged by name."""
    import psutil

    procs = []
    for p in psutil.process_iter(["pid", "ppid", "name", "create_time", "status"]):
        try:
            # A zombie is a process that has ended and has not yet been collected by its parent. On Linux it stays
            # in the list, so a killed worker would never be seen to END (found by the planted-fault test there,
            # 2026-10-23). It is gone for this purpose.
            if p.info.get("status") == psutil.STATUS_ZOMBIE:
                continue
            procs.append((p, p.info))
        except (psutil.Error, OSError):
            continue
    parent_of = {info["pid"]: info["ppid"] for _, info in procs}

    def under_root(pid: int) -> bool:
        """Is this process a descendant of the watched push? Another push's workers are not this push's deaths."""
        if root is None:
            return True
        for _ in range(64):
            if pid == root:
                return True
            pid = parent_of.get(pid, 0)
            if not pid:
                return False
        return False

    out: dict[int, dict] = {}
    for p, info in procs:
        try:
            name = (info["name"] or "").lower()
            key = (info["pid"], info["create_time"])
            kind = known.get(key)
            if kind is None:
                worker = False
                if is_python_name(name):
                    worker = SIGNATURE in " ".join(p.cmdline() or []).replace(" ", "")
                kind = (worker, name in LOGGED_NAMES or is_python_name(name))
                known[key] = kind
            worker, logged = kind
            if worker and not under_root(info["pid"]):
                continue
            if worker or logged:
                out[info["pid"]] = {"ppid": info["ppid"], "name": name, "worker": worker}
        except (psutil.Error, OSError):
            continue
    return out


def _bare_line(config: Path) -> str:
    try:
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("bare"):
                return line.strip()
        return "bare: absent"
    except OSError:
        return ""


def run(parent_pid: int, raw_path: Path, git_config: Path | None = None) -> None:
    """Sample until the parent (the push hook) is gone. Writes only changes, plus a heartbeat every few samples."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    # A passing push finishes nothing, so its raw log stays; sweep the ones older than a day so they cannot pile up.
    for old in raw_path.parent.glob("raw-*.jsonl"):
        try:
            if old != raw_path and time.time() - old.stat().st_mtime > 86400:
                old.unlink()
        except OSError:
            pass
    lines = 0
    with raw_path.open("a", encoding="utf-8") as handle:

        def write(obj: dict) -> None:
            nonlocal lines
            lines += 1
            if lines > MAX_RAW_LINES:
                return
            if lines == MAX_RAW_LINES:
                obj = {"k": "truncated", "n": obj.get("n", 0)}
            handle.write(json.dumps(obj) + "\n")
            handle.flush()

        n = 0
        known: dict = {}
        previous = _snapshot(known, parent_pid)
        for pid, info in previous.items():
            write({"k": "present", "n": 0, "t": round(time.time(), 2), "pid": pid, **info})
        bare = _bare_line(git_config) if git_config else ""
        # Pins WHICH process I follow, so a recycled number cannot keep me alive.
        parent_created = _created(parent_pid)
        began_run = time.time()
        # The cap is the backstop for a watcher that can never tell whether its hook is gone: no push lasts this long,
        # and a courtesy process must never outlive its usefulness (Aletheia's worry, 2026-10-23: a leak nobody sees).
        while _alive(parent_pid, parent_created) and time.time() - began_run < MAX_WATCH_SECONDS:
            time.sleep(INTERVAL)
            n += 1
            current = _snapshot(known, parent_pid)
            if not _alive(parent_pid, parent_created):
                # The hook is gone: its workers stop counting as ITS descendants the instant it goes, so this look
                # would record every one of them as ended when none did. Found by the tree-ended-early rule firing
                # on a planted run in which nothing ended. That look is thrown away.
                break
            for pid, info in current.items():
                if pid not in previous:
                    write({"k": "started", "n": n, "t": round(time.time(), 2), "pid": pid, **info})
            for pid, info in previous.items():
                if pid not in current:
                    write({"k": "ended", "n": n, "t": round(time.time(), 2), "pid": pid, **info})
            if git_config:
                now_bare = _bare_line(git_config)
                if now_bare != bare:
                    write(
                        {
                            "k": "cfg",
                            "n": n,
                            "t": round(time.time(), 2),
                            "before": bare,
                            "after": now_bare,
                        }
                    )
                    bare = now_bare
            if n % HEARTBEAT_EVERY == 0:
                write({"k": "tick", "n": n, "t": round(time.time(), 2)})
            previous = current
        write({"k": "tick", "n": n, "t": round(time.time(), 2)})


def finish(
    raw_path: Path, exit_code: int, output_tail: str, out_dir: Path, tests_ran: bool = True
) -> str:
    """Build the report from the raw log, write it, trim old ones, return the sentence for the end of the push."""
    report = assemble(read_raw(raw_path), exit_code, output_tail, tests_ran)
    if report["outcome"] == "PASSED":
        return ""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"push-{stamp}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if raw_path.is_file():
        path.with_suffix(".raw.jsonl").write_bytes(raw_path.read_bytes())
    trim_reports(out_dir)
    return final_line(report, str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("start")
    start.add_argument("--parent", type=int, required=True)
    start.add_argument("--raw", required=True)
    start.add_argument("--git-config")
    done = sub.add_parser("finish")
    done.add_argument("--raw", required=True)
    done.add_argument("--exit", type=int, required=True)
    done.add_argument("--out-dir", required=True)
    done.add_argument("--tail-file")
    args = parser.parse_args(argv)
    if args.cmd == "start":
        run(args.parent, Path(args.raw), Path(args.git_config) if args.git_config else None)
        return 0
    tail, tests_ran = fresh_tail(
        Path(args.tail_file) if args.tail_file else None, read_raw(Path(args.raw))
    )
    sentence = finish(Path(args.raw), args.exit, tail, Path(args.out_dir), tests_ran)
    if sentence:
        print(sentence, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
