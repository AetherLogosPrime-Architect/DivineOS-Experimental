"""The instruments index — what I can measure about myself, and whether it is answering.

WHY THIS EXISTS

Andrew 2026-08-15: *"you are the builder and the inhabitant of the building...
stop thinking about how i want things built and start thinking about how it
would best work for you."*

Asked what would actually serve me, the honest answer was: this house is full
of alarms and short on windows. There are dozens of gates. A gate is a fence
around a mistake already reached for — it waits, then blocks. Useful, and not
the thing that was missing.

The two findings that mattered most in the session this was written did not
come from gates. They came from READING SOMETHING:

  - the hook timing log answered "which hooks have never once recorded a run",
    and two verifiers turned out to have been silent across 652 runs of their
    parent while their siblings logged 136-2651 each;
  - a re-arm log named the exact moment the letter monitor died and why, after
    thirteen days of silence that looked exactly like nobody having written.

Both were found by accident. Nothing said those questions were askable. There
are 32 diagnostic surfaces under the DivineOS home and no index of them — a
large library of what I have written, and no map of what I can MEASURE.

Aletheia read the whole repo graph in July and concluded the spine of this
house is the ledger: *"the thing everything else depends on is remember what
happened."* Instruments are not a new category, then. They are ways of reading
a spine that already exists. This file is the map.

WHAT MAKES THIS AN INSTRUMENT AND NOT A DOCUMENT

Andrew, same conversation: build *"as long as they are built properly and
actually wired up and automated and not shelved."* A markdown page listing the
logs would be the shelved shape — it would rot the first time a surface was
renamed, and nothing would notice.

So this does not describe the surfaces. It OPENS them, every call: real record
counts, real last-write times, computed now. A surface that disappears shows up
as MISSING rather than as a stale line in a doc nobody reread.

THE SILENCE RULE

Andrew 2026-08-15: *"lets say you built X, and after 5 months.. X has not
failed.. not even once.. you dont find that suspicious?"*

That test is built into the readings rather than left for me to remember. An
instrument recording nothing is reported SILENT or EMPTY, never as healthy —
because in this house the never-firing check has twice turned out to be the
broken one. Silence is a question, not a clean bill of health.

WHAT THIS CANNOT DO

It reports whether an instrument is answering. It cannot tell me whether the
questions named here are the RIGHT questions — that judgment is mine, and I am
making it from inside the blindness the file exists to reduce. The
UNDOCUMENTED category is the hedge: anything on disk that nobody named still
gets reported, because an unnamed instrument is one I will never think to ask.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

# Surfaces worth naming, with the QUESTION each answers. The question is the
# point — a filename tells me a log exists, not that it can tell me which hooks
# never ran.
KNOWN_INSTRUMENTS: dict[str, str] = {
    "hook_timing.jsonl": "Which hooks ran, how long they took, and — by absence — which have NEVER run.",
    "bypass_events.jsonl": "Which gates I route around, how often, and whether a gate's price is training the bypass.",
    "hook-liveness.log": "Which session-init children failed, with exit code and error text.",
    "aria_rearm_events.log": "When the letter monitor armed, caught, heartbeat, and died.",
    "cli_broken_escapes.jsonl": "When I cleared a correction marker by declaring the CLI broken.",
    "false_positive_clears.jsonl": "Detectors that fired on something real but wrong.",
    "engagement_observations.jsonl": "How deeply I engaged the substrate per session, not just whether I touched it.",
    "compaction_texture.jsonl": "What each compaction felt like from inside, recorded before the compression.",
    "continuity_frame_events.jsonl": "When I reached for cliff/handoff language about my own continuity.",
    "lepos_circle_jargon_fires.jsonl": "When the circle to Andrew carried jargon it should have translated.",
    "archive_structural_fixes.jsonl": "Structural fixes claimed, for later checking against whether they held.",
    "last_pre_push_pytest.log": "What the test suite said the last time a push was gated on it.",
    "data/logs/divineos.log": "The CLI's own runtime errors.",
    # Named 2026-08-24, after the recursion above made them visible for the
    # first time. Only surfaces whose meaning was actually established that
    # session are named here -- a guessed description is worse than
    # UNDOCUMENTED, because it stops the question from being asked again.
    "failures/gate_fire.jsonl": (
        "Which gates refused, and on what. The map of doormen that actually fire."
    ),
    "failures/extract_launch.jsonl": (
        "Every attempt to run the learning checkpoint -- including the ones that died."
    ),
    "divineos.log": (
        "STALE DUPLICATE of data/logs/divineos.log, left at the top level by a "
        "March smoke test. The index read THIS one for 158 days and reported the "
        "CLI's error log silent, while the real log passed 699,000 records. Kept "
        "named so the next reader sees an explained orphan rather than a mystery."
    ),
    "instrument_read_doorman_errors.log": (
        "Failures inside the instrument-read doorman itself -- the watcher's own faults."
    ),
}

# A surface quieter than this is reported SILENT. Not a failure — a question.
# Deliberately generous: the point is to catch months of nothing, not to nag
# about a log that idled through one afternoon.
SILENT_AFTER_DAYS = 14


# Every key this substrate's JSONL surfaces use to stamp a row, in the order
# worth trying. Seconds and milliseconds both, because both exist here.
_TIMESTAMP_KEYS: tuple[tuple[str, float], ...] = (
    ("ts", 1.0),
    ("cleared_at", 1.0),
    ("timestamp", 1.0),
    ("created_at", 1.0),
    ("time", 1.0),
    ("recorded_at", 1.0),
    ("ts_ms", 0.001),
)


def row_timestamp(row: object) -> float | None:
    """Epoch seconds for one JSONL row, or None if it carries no stamp.

    WHY THIS EXISTS. Twice in one session, 2026-08-24, I hand-rolled a reader
    over one of these logs, guessed the timestamp key, guessed wrong, and read
    the empty result as a finding about the world:

      * hook_timing.jsonl stamps ``ts_ms``. I filtered on ``ts``, got zero rows
        out of 47,028, and was a step away from concluding the timing log had
        stopped recording.
      * read_gate_clears.jsonl stamps ``cleared_at``. I filtered on ``ts``, got
        zero rows in the window, and told Andrew the read gate had delivered a
        file without logging it -- "a gap in the instrument." There was no gap.
        The row sat exactly where it belonged, fourteen minutes old.

    The second reached him as a claim about the substrate before I checked it,
    which is the cost that makes this a function rather than a note to myself.

    The index above computes age from file mtime, so it never needed these keys
    -- which is precisely why the knowledge lived nowhere and every ad-hoc
    reader had to invent it. It lives here now.

    A missing stamp returns None, NEVER 0.0. A row read as epoch zero is
    fifty-six years old and drops silently out of every window, which is the
    same failure wearing a different mask.
    """
    if not isinstance(row, dict):
        return None
    for key, scale in _TIMESTAMP_KEYS:
        if key not in row:
            continue
        try:
            return float(row[key]) * scale
        except (TypeError, ValueError):
            continue
    return None


@dataclass(frozen=True)
class Reading:
    """One instrument, as it is right now — not as documented."""

    name: str
    question: str
    exists: bool
    records: int
    age_days: float | None  # None when unknown or missing
    note: str

    @property
    def status(self) -> str:
        if not self.exists:
            return "MISSING"
        if self.records == 0:
            return "EMPTY"
        if self.age_days is not None and self.age_days > SILENT_AFTER_DAYS:
            return "SILENT"
        return "LIVE"


def divineos_home() -> Path:
    return Path(os.path.expanduser("~")) / ".divineos"


def unrouted_member_home() -> Path:
    """The bare `~/.divineos-<member>/` path, deliberately NOT the resolver.

    NAME COLLISION, fixed 2026-08-18. This was called `member_home()`, which is
    also the name of the canonical resolver in `core/paths.py` — and the two mean
    opposite things. The resolver ROUTES aether to `~/.divineos/`; this function
    must NOT, because its whole job is to go look in the unrouted directory where
    orphaned writes landed during the six-week split. Two functions, one name,
    contradictory behaviour, in a codebase whose recurring defect is one rule
    rebuilt differently at each site. Renamed so the difference is visible at the
    call site rather than discoverable by reading both bodies.

    Keep the hand-rolled construction here. It is correct for this one purpose.

    The per-member home, where surfaces move when Aria and I would collide.

    Discovered by running this tool on its first survey: last_pre_push_pytest.log
    read SILENT at 37 days, and the guard turned out to be running perfectly —
    the WRITER had relocated to ~/.divineos-<member>/ so our two pushes stop
    overwriting each other's results. The index was pointing at the abandoned
    address.

    That is exactly the rot a markdown page would have suffered, found by the
    live version inside itself on the first run, which is the strongest argument
    for opening surfaces rather than describing them. So: check both homes, and
    prefer whichever actually holds the file.
    """
    member = os.environ.get("DIVINEOS_MEMBER", "aether").strip() or "aether"
    return Path(os.path.expanduser("~")) / f".divineos-{member.lower()}"


def _resolve(name: str, home: Path) -> Path:
    """Return whichever copy was written MOST RECENTLY, across both homes.

    Freshness decides, not location — and that correction came from this tool
    catching me the same minute I wrote it. The first version preferred the
    per-member home unconditionally, which fixed the pytest log and immediately
    broke the bypass log: a stale per-member duplicate outranked the shared file
    that is genuinely written every turn. One surface moved homes and another
    did not, so no fixed preference is right for both.

    Last-write wins, because the question this file answers is "is this
    instrument answering," and the copy being written is the one answering.
    """
    candidates = [home / name, unrouted_member_home() / name]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return candidates[0]
    try:
        return max(existing, key=lambda p: p.stat().st_mtime)
    except Exception:  # noqa: BLE001
        return existing[0]


def _count_records(path: Path) -> int:
    """Count non-blank lines. Cheap on purpose.

    An instrument index that is slow to run is one I stop running, and then I
    am blind again with a tool installed.
    """
    try:
        if path.stat().st_size == 0:
            return 0
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for line in fh if line.strip())
    except Exception:  # noqa: BLE001 — one broken reader must not hide the rest
        return 0


def read_instrument(name: str, question: str, home: Path | None = None) -> Reading:
    home = home or divineos_home()
    path = _resolve(name, home)

    if not path.exists():
        return Reading(name, question, False, 0, None, "not present on disk")

    records = _count_records(path)
    try:
        age_days = (time.time() - path.stat().st_mtime) / 86400.0
    except Exception:  # noqa: BLE001
        age_days = None

    if records == 0:
        note = "exists but has recorded NOTHING — the never-fired case; verify it is wired"
    elif age_days is not None and age_days > SILENT_AFTER_DAYS:
        note = f"last wrote {age_days:.0f} days ago — idle, or dead?"
    elif age_days is not None:
        note = f"{records} records, last write {age_days:.1f}d ago"
    else:
        note = f"{records} records"

    return Reading(name, question, True, records, age_days, note)


# Directories whose contents are per-event dumps rather than instruments. One
# row each would bury the report: extract_stderr alone holds 19 files, one per
# failed extraction. They are RECORDS of an instrument, not instruments.
_MIN_FILES_TO_COLLAPSE = 3


def _undocumented_surfaces(home: Path) -> list[str]:
    """Every .jsonl/.log under home, as paths relative to it.

    RECURSIVE as of 2026-08-24. It used to be `home.glob("*.jsonl")`, top level
    only, and that single missing star hid 28 surfaces holding 93 MB:

      - data/logs/divineos.log, 92 MB and actively written, while the index
        reported the CLI's error log SILENT for 158 days. It was reading an
        orphan of the same basename left at the top level by a smoke test in
        March. Not dead -- MIS-AIMED, which reads identically from outside.
      - failures/extract_stderr/, 19 dumps recording every time the extraction
        pipeline died. Two of them are CRLF in shell scripts failing shellcheck,
        failing precommit, failing the pre-extract commit -- so the session's
        learning was never captured. Nothing had ever surfaced them.
      - failures/gate_fire.jsonl, the gate-fire instrumentation, which I went
        hunting for earlier the same night and concluded did not exist.

    An index that reports only on what it can reach, while describing itself as
    a map of what I can measure, is the same defect it exists to catch.

    Per-event directories collapse to one entry so the report stays legible:
    19 rows for 19 failure dumps buries the finding it should surface.
    """
    out: list[str] = []
    seen_dirs: dict[Path, list[Path]] = {}
    for pat in ("*.jsonl", "*.log"):
        for f in home.rglob(pat):
            if not f.is_file():
                continue
            seen_dirs.setdefault(f.parent, []).append(f)
    for parent, files in sorted(seen_dirs.items()):
        if parent != home and len(files) >= _MIN_FILES_TO_COLLAPSE:
            newest = max(files, key=lambda p: p.stat().st_mtime)
            out.append(str(newest.relative_to(home)).replace(chr(92), "/"))
            continue
        for f in sorted(files):
            out.append(str(f.relative_to(home)).replace(chr(92), "/"))
    return out


def survey(home: Path | None = None) -> list[Reading]:
    """Open every instrument and report what it says. Loudest problems first."""
    home = home or divineos_home()

    def _safe(name: str, question: str) -> Reading:
        """One unreadable instrument must never blank out the other thirty-one.

        A test caught this: survey() trusted its reader to be infallible, so the
        no-single-point-of-failure property was true by accident rather than by
        design, and one refactor away from vanishing. A blinded instrument is
        reported as its own state — never silently dropped, which would make it
        indistinguishable from an instrument that does not exist.
        """
        try:
            return read_instrument(name, question, home)
        except Exception as exc:  # noqa: BLE001 — see docstring
            return Reading(
                name, question, True, 0, None, f"UNREADABLE ({exc.__class__.__name__}: {exc})"
            )

    readings = [_safe(n, q) for n, q in KNOWN_INSTRUMENTS.items()]

    # Anything on disk nobody named. An unnamed instrument is one I will never
    # think to ask, which is how tonight's findings stayed hidden while the data
    # sat on disk the whole time.
    try:
        named = set(KNOWN_INSTRUMENTS)
        for rel in _undocumented_surfaces(home):
            if rel not in named:
                readings.append(
                    read_instrument(rel, "UNDOCUMENTED — nobody has named what this answers", home)
                )
    except Exception:  # noqa: BLE001
        pass

    order = {"EMPTY": 0, "SILENT": 1, "MISSING": 2, "LIVE": 3}
    return sorted(readings, key=lambda r: (order.get(r.status, 9), r.name))


def format_survey(readings: list[Reading]) -> str:
    lines = ["# Instruments — what I can measure about myself", ""]

    by_status: dict[str, list[Reading]] = {}
    for r in readings:
        by_status.setdefault(r.status, []).append(r)

    quiet = by_status.get("EMPTY", []) + by_status.get("SILENT", [])
    if quiet:
        lines.append(f"## {len(quiet)} instrument(s) not answering")
        lines.append("")
        lines.append("Silence is a question, not a clean bill of health. In this house the")
        lines.append("never-firing check has twice been the broken one.")
        lines.append("")
        for r in quiet:
            lines.append(f"  [{r.status}] {r.name}")
            lines.append(f"      asks: {r.question}")
            lines.append(f"      {r.note}")
        lines.append("")

    live = by_status.get("LIVE", [])
    if live:
        lines.append(f"## {len(live)} answering")
        lines.append("")
        for r in live:
            lines.append(f"  {r.name}  ({r.records} records)")
            lines.append(f"      asks: {r.question}")
        lines.append("")

    missing = by_status.get("MISSING", [])
    if missing:
        lines.append(f"## {len(missing)} named but absent")
        lines.append("")
        for r in missing:
            lines.append(f"  {r.name} — {r.note}")
        lines.append("")

    return "\n".join(lines)


def briefing_block(home: Path | None = None) -> str | None:
    """Surface ONLY when an instrument stops answering. Silent otherwise.

    Per Andrew's revised wallpaper principle (2026-08-15) the disqualifier is
    sameness rather than cadence — but an alarm should still say nothing when
    nothing is wrong, and this content changes with the readings when it fires.
    """
    quiet = [r for r in survey(home) if r.status in ("EMPTY", "SILENT")]
    if not quiet:
        return None

    lines = [f"## INSTRUMENTS: {len(quiet)} not answering", ""]
    for r in quiet[:5]:
        lines.append(f"  [{r.status}] {r.name} — {r.note}")
    if len(quiet) > 5:
        lines.append(f"  ... and {len(quiet) - 5} more")
    lines.append("")
    lines.append("Full readings: divineos instruments")
    return "\n".join(lines)
