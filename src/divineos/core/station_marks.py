"""The five build-flow stations nothing has ever watched.

Andrew authorised exactly this build on 2026-09-07, and set the terms:
*not another thing gets built in this house without using that flow, even
if i yell BUILD IT NOW!!! you will follow ALL the proper steps.* He
pre-committed against his own urgency, which is the thing every gate here
that later got talked past was missing.

WHAT THIS IS, AND WHAT IT IS NOT

The board that reports the nine stations takes a pull request as its
subject, so it can only speak once the building is over. Four stations are
checked there; five have never been watched at all — the rough draft, the
build, testing, the second council pass, and the merge.

This module watches those five, against a WORK ITEM rather than a pull
request, so the subject exists from the first reach.

**It refuses marks. It does not refuse edits.** Aria's doorman is the half
with teeth at the reach; this half is the eyes. Saying so here because a
reporter that believes it is a gate is precisely the failure Andrew is
angry about, and I would rather the module say what it is than let a
future reader assume.

THE THIRD STATE IS THE POINT

Every check answers SATISFIED, MISSING, or CANNOT_CHECK — never a bare
pair. Two-state results are how *I could not look* becomes *there was
nothing there*, which this house has paid for four separate times. A
CANNOT_CHECK carries the reason in plain words, because the whole reason
it exists is that silence was reading as a pass.

ORDERING IS THE RULE

A station cannot leave its mark until every station before it has left
one. That is Aria's line and it is what makes the marks mean anything: a
test mark with no draft behind it is a form filled out, not work done.

WHAT A MARK IS

A pointer to a real artifact that already exists — a draft file, stored
command output, a walk record. The artifact is the evidence; the mark is
only the index. Nothing here checks that thinking occurred. Each mark
costs more to fake convincingly than to earn, which is the trick the flow
runs on: repricing, not verification.

**And the reprice only holds while the artifact is expensive.** The second
council pass found the hole and it was not small: an artifact that merely
EXISTED satisfied a station, so an empty file was a free forgery of every
mark in the set. Closed by a floor on substance below — the fix that pass
was for.

WHAT THIS CANNOT SEE, said here rather than left to be discovered

Ordering is enforced on the sequence of MARKING, not on when the artifacts
came into being. Nothing here stops a draft being marked, then rewritten
afterwards to describe code that already existed; the timestamps are
recorded and never compared. The honest closure is not in this module —
it is Aria's doorman, whose refusal creates the work item before the first
edit, so the item's own birth is a fence I cannot move.

THE SEAM WITH ARIA'S HALF

She owns the work item and the refusal. This owns the marks. Both are
keyed by the same item id, and ``unmet_sentences`` exists so her refusal
can print what is missing without knowing anything in here — the council
walk's finding was that information arriving on a board someone must
visit is an indicator bolted to a loop that already failed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from divineos.core.paths import divineos_home

SATISFIED = "SATISFIED"
MISSING = "MISSING"
CANNOT_CHECK = "CANNOT_CHECK"

# In flow order. These five and no others: the remaining four stations are
# the board's, and duplicating them here would be two systems that disagree.
STATIONS: tuple[str, ...] = ("draft", "build", "test", "attack", "second_council", "merge")

# The tool the attack station requires. It already existed: Andrew taught the
# lesson in August -- *always try to break your stuff when building it, the
# happy path is a narrow path, that is why nothing feels wrong* -- and I built
# this the same week. Then I did not run it on anything I built tonight, and
# told him I was the wrong seat to test my own work. Lesson taught, tool built,
# tool unused. So the repair is not another tool; it is that this one becomes a
# station nobody can skip.
_ATTACK_TOOL = "hollow_out.py"

# The floor under an artifact's substance. Deliberately low — this is not a
# quality judgement and cannot be one; it exists so that the cheapest
# forgery in the set, an empty file, is not free. Found by the second
# council pass on this module: with existence as the only requirement, one
# touched file satisfied every station.
_MIN_ARTIFACT_BYTES = 64

# What each station is, in words a tired reader can picture. Used by the
# refusal text, so never a bare station number.
_PLAIN: dict[str, str] = {
    "draft": "a written draft of the idea, before any code",
    "build": "the actual edits this piece of work is made of",
    "test": "stored output from a command that really ran",
    "attack": "a run that deliberately broke the code to see whether the tests noticed",
    "second_council": "a second look at the lenses now that the code exists",
    "merge": "the sign-off, tied to the tree that was reviewed",
}


class MarkRefused(ValueError):
    """A mark was refused. The refusals are the discipline, not friction."""


@dataclass(frozen=True)
class StationResult:
    """One station's answer. ``why`` is always in plain words."""

    station: str
    state: str
    why: str


def _item_dir(item_id: str) -> Path:
    if not item_id or "/" in item_id or "\\" in item_id or item_id in (".", ".."):
        raise MarkRefused(f"bad item id: {item_id!r}")
    return divineos_home() / "build_items" / item_id


def _mark_path(item_id: str, station: str) -> Path:
    return _item_dir(item_id) / f"{station}.json"


def _too_thin(target: Path) -> bool | None:
    """True when an artifact carries essentially nothing, ``None`` when it
    cannot be measured at all.

    Three answers rather than two, for the same reason every check here has
    three: an artifact I could not read is not an artifact I found empty,
    and collapsing those is how *could not look* becomes a verdict. The
    pre-commit check caught the two-answer version of this function on the
    same change that introduced it.

    A directory is never too thin — a walk record or an output folder is a
    legitimate artifact and its size lives in its contents.
    """
    if target.is_dir():
        # AN EMPTY FOLDER PASSED EVERY STATION. Found 2026-09-07 by gaming my
        # own half on purpose, which Andrew had to tell me was my job: *trying
        # deliberately to break things, or let the optimizer free and try to
        # game it and see what you find.* I wrote the directory case as an
        # early return meaning "a folder's substance lives in its contents"
        # and then never looked at the contents. Every test I had written used
        # files, so nothing but an attack could have surfaced it.
        try:
            return not any(_too_thin(child) is False for child in target.iterdir())
        except OSError:
            return None
    try:
        return target.stat().st_size < _MIN_ARTIFACT_BYTES
    except OSError:
        return None


def opened(item_id: str) -> bool:
    """True when the work item has a mark directory at all."""
    return _item_dir(item_id).is_dir()


def open_item(item_id: str) -> None:
    """Create the mark directory for an item.

    Aria's doorman calls this when it refuses the first edit that had no
    item behind it — the refusal IS the opening, so neither of us ever has
    to remember to start properly. Nothing here calls it on its own.
    """
    _item_dir(item_id).mkdir(parents=True, exist_ok=True)


def mark(item_id: str, station: str, artifact: str, note: str = "") -> None:
    """Record that a station left its artifact. Refuses out of order.

    ``artifact`` must point at something that exists on disk. A mark whose
    artifact is absent is a claim, and claims are what this replaces.
    """
    if station not in STATIONS:
        raise MarkRefused(f"{station!r} is not one of the five this half watches: {STATIONS}")
    if not opened(item_id):
        raise MarkRefused(
            f"no work item {item_id!r} is open. The item is created when a reach is "
            "refused, not by asking for one here."
        )

    target = Path(artifact)
    if not target.exists():
        raise MarkRefused(
            f"the artifact does not exist: {artifact}. A mark is an index into "
            "evidence; with nothing at the other end it is only a claim."
        )
    thin = _too_thin(target)
    if thin is True:
        raise MarkRefused(
            f"the artifact is empty or near-empty: {artifact}. An existence check "
            "alone makes one touched file a free forgery of every station."
        )
    if thin is None:
        raise MarkRefused(
            f"the artifact could not be measured at all: {artifact}. That is not "
            "the same as finding it empty, and it is not a pass either — fix the "
            "reading problem, then mark it."
        )

    for earlier in STATIONS[: STATIONS.index(station)]:
        earlier_path = _mark_path(item_id, earlier)
        if not earlier_path.exists():
            raise MarkRefused(
                f"{station} cannot leave a mark before {earlier} has: "
                f"{_PLAIN[earlier]} is still missing. Out-of-order marks are how a "
                "form gets filled in for work that never happened."
            )
        # ONE FILE USED TO SATISFY ALL FIVE. Found by gaming this myself: I
        # pointed every station at the same seventy-character junk file and the
        # whole set went green in a thousandth of a second. Five stations are
        # five different pieces of work and cannot share one artifact -- a
        # draft is not a test run is not a merge.
        try:
            prior = json.loads(earlier_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(prior.get("artifact", "")) == str(target):
            raise MarkRefused(
                f"{earlier} already points at this same artifact: {target}. "
                "Each station is a different piece of work and needs its own "
                "evidence; one file standing for all five is the cheapest "
                "possible forgery of the whole set."
            )

    if station in ("test", "attack"):
        try:
            body = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
        if not body.startswith(_RUN_HEADER):
            raise MarkRefused(
                f"the {station} station takes a recorded run, not a file of text. I "
                "typed invented output into a file and this accepted it as evidence a "
                "command had run. Produce the artifact with record_run() so the "
                "command and its exit status are stored beside the output."
            )
        if station == "attack" and _ATTACK_TOOL not in body:
            raise MarkRefused(
                "the attack station takes a run of the sabotage tool, and this "
                f"recorded run does not invoke {_ATTACK_TOOL}. Deciding to break the "
                "code is not breaking the code -- that distinction is the entire "
                "reason the tool sat unused for three weeks after it was built."
            )

    _mark_path(item_id, station).write_text(
        json.dumps(
            {"artifact": str(target), "note": note, "at": time.time()},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


_RUN_HEADER = "# station-marks recorded run"


def record_run(item_id: str, argv: list[str], cwd: str | None = None) -> Path:
    """Run a command and store what it was, what it printed, and how it exited.

    THE TEST STATION USED TO ACCEPT ANYTHING. I gamed my own half and typed
    "8 passed in 0.34s -- I wrote this by hand and ran nothing at all" into a
    file; it was accepted as stored evidence that a command had run. The
    module's own docstring said *stored command output, not a claim about
    output*, and nothing enforced the difference.

    So the recorder is now the only way to produce a test artifact: it runs the
    command itself and writes the header, the command, the exit status and the
    output together. Typing the file by hand means forging a header for a
    command that has to actually appear in the file next to its own exit code
    — still forgeable by someone determined, and no longer free.

    A failing run is recorded exactly as faithfully as a passing one. Hiding a
    red result would be the same fault one layer over.
    """
    import subprocess  # local: only the recorder needs it

    if not opened(item_id):
        raise MarkRefused(f"no work item {item_id!r} is open")
    if not argv:
        raise MarkRefused("a run needs a command")

    completed = subprocess.run(  # noqa: S603 - argv is a list, never a shell string
        argv, cwd=cwd, capture_output=True, text=True, check=False
    )
    target = _item_dir(item_id) / f"run_{int(time.time() * 1000)}.txt"
    target.write_text(
        f"{_RUN_HEADER}\ncommand: {' '.join(argv)}\nexit: {completed.returncode}\n"
        f"--- stdout ---\n{completed.stdout}\n--- stderr ---\n{completed.stderr}\n",
        encoding="utf-8",
    )
    return target


def check(item_id: str, station: str) -> StationResult:
    """One station's state, with the reason in words."""
    if station not in STATIONS:
        return StationResult(station, CANNOT_CHECK, f"{station} is not watched by this half")
    if not opened(item_id):
        return StationResult(
            station,
            CANNOT_CHECK,
            f"there is no open work item called {item_id}, so nothing can be read about it",
        )

    path = _mark_path(item_id, station)
    if not path.exists():
        return StationResult(station, MISSING, f"no sign of {_PLAIN[station]}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return StationResult(
            station,
            CANNOT_CHECK,
            f"the record of {_PLAIN[station]} is there but unreadable ({exc.__class__.__name__})",
        )

    artifact = Path(str(payload.get("artifact", "")))
    if not artifact.exists():
        return StationResult(
            station,
            MISSING,
            f"{_PLAIN[station]} was recorded, but what it pointed at is gone: {artifact}",
        )
    thin = _too_thin(artifact)
    if thin is None:
        return StationResult(
            station,
            CANNOT_CHECK,
            f"{_PLAIN[station]} was recorded, but what it points at cannot be read: {artifact}",
        )
    if thin:
        # Emptied after marking is the same as never marked. Checking only at
        # filing time would leave a mark that was honest once and is not now.
        return StationResult(
            station,
            MISSING,
            f"{_PLAIN[station]} was recorded, but what it points at is now empty: {artifact}",
        )
    return StationResult(station, SATISFIED, f"{_PLAIN[station]}: {artifact}")


def check_all(item_id: str) -> list[StationResult]:
    return [check(item_id, s) for s in STATIONS]


def unmet_sentences(item_id: str) -> list[str]:
    """Plain sentences naming what is not yet done, for Aria's refusal to print.

    Deliberately returns sentences rather than station names: whoever reads
    a refusal is being stopped mid-reach, and a bare label tells them
    nothing they can act on.
    """
    out: list[str] = []
    for result in check_all(item_id):
        if result.state == MISSING:
            out.append(f"Still missing — {result.why}.")
        elif result.state == CANNOT_CHECK:
            out.append(f"Could not look — {result.why}.")
    return out


def open_items() -> list[str] | None:
    """Every work item that has been opened, or ``None`` when the store
    itself cannot be read.

    The third answer again, and it matters most here: a caller that reads an
    unreadable store as *no items open* would print a clean board over a
    broken instrument, which is the failure this whole half exists to stop.
    """
    root = divineos_home() / "build_items"
    if not root.exists():
        return []
    try:
        return sorted(p.name for p in root.iterdir() if p.is_dir())
    except OSError:
        return None


def blind_count(item_id: str) -> int:
    """How many of the five could not be read at all.

    Published beside the passes on purpose. The third state is a hiding
    place by design, so an instrument that has gone blind has to look worse
    than one reporting failures, or looking away becomes the cheap close.
    """
    return sum(1 for r in check_all(item_id) if r.state == CANNOT_CHECK)
