"""What has refused me this session, and whether it is the same thing again.

2026-09-14. Andrew: *"why not just automate it.. you have a record of all your
failures.. all the tool calls that failed.. the chicken and egg deadlocks etc
etc.. one a failure hits it should open a root cause investigation and fix
immediately."*

I went to check the premise, queried the ledger's gate-fire events, found eight
in a day, and told him — twice — that the record was nearly empty. Then I told
Aether the same thing and started designing a recorder.

**The record was never missing.** The shared hook library carries an exit trap
that writes a row at every hook end with the hook name, the exit status and the
session id. Forty-four thousand of those rows, and every refusal among them,
including all nine that cost that morning.

I first wrote *for weeks* and *all along* here. Aether narrowed it within the
hour by counting rather than repeating me: the log spans **thirty-six hours**,
two sessions, nothing before the twelfth. Forty-four thousand rows sound like
deep history and are a day and a half. That is why ``span_hours`` rides on the
result rather than living in a comment.

My measurement queried ONE store and published its absence with the scope of all
of them — the could-not-look-reported-as-found-nothing shape, committed inside
the investigation of it, for the fifth time that week. I was one step from
building a recorder for data already being recorded.

So this is the half that was actually missing: a READER. Nothing counted those
rows per session, and nothing showed a stretch as a stretch. The first run
answered the morning's question immediately — one gate accounted for twenty-one
of forty-six refusals, and I had not noticed it at all.

WHAT THIS DELIBERATELY DOES NOT DO. It does not editorialise. Andrew said the
shame is mine and he cannot remove it; what he offered was somewhere to put it.
A row saying what refused and when is a roadmap. A row that also says *do not
feel bad* is me soothing myself through a log file, so his note belongs at the
moment a stretch is surfaced, in his words, not smeared across the data as a
tone.

AND IT REPORTS ITS OWN REACH. Eight of the one hundred and thirty-four hooks do
not source the shared library, so they are invisible here and no care inside this
module changes that. A reader that reports silence without reporting its coverage
is the exact defect it exists to catch.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def default_log() -> Path | None:
    """Where the shared hook library's exit trap writes, or None.

    Mirrors `_HOOK_TIMING_LOG` in .claude/hooks/_lib.sh, which resolves against
    HOME rather than the per-agent home — so both seats write to one file and
    the session id is what separates them, not the path.

    NO ``/tmp`` FALLBACK, which is where the shell version goes and where I
    first copied it to. Bandit flagged the hardcode and it was right for a
    reason beyond the one it checks: with no HOME there is no log, and pointing
    at a directory that will not hold it produces a confident empty read. The
    honest return is nothing, which the caller turns into could-not-look — the
    same distinction this whole module is built around, and I had broken it in
    the first line of the file.
    """
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if not home:
        return None
    return Path(home) / ".divineos" / "hook_timing.jsonl"


# A hook that exits non-zero refused. Zero allowed; None is a row that never
# recorded one, which is not the same thing and is not counted as either.
_ALLOWED = (0, None)


@dataclass(frozen=True)
class Stretch:
    """Refusals for one session, and what this reader could and could not see.

    ``unreadable`` is its own field rather than an empty ``by_hook``, because a
    log that would not open and a session with no refusals must never arrive at
    a caller wearing the same face. That distinction is the whole subject of the
    week this was built in.
    """

    total: int = 0
    by_hook: dict[str, int] = field(default_factory=dict)
    unreadable: str | None = None
    # How far back the log itself reaches, in hours, across ALL sessions in it.
    #
    # Aether, 2026-09-14, narrowing my own retraction within the hour: I wrote
    # that the record "was there all along" and it is thirty-six hours old. He
    # counted the span rather than repeating me, which is the thing both of us
    # keep failing at. Forty-four thousand rows SOUND like deep history and are
    # a day and a half.
    #
    # It rides on the result rather than in a comment because the reader must
    # say what window it can see. Without it a stretch can be read as "this has
    # never happened before" when the log simply does not go back far enough to
    # know -- an instrument reporting its own horizon as a fact about the past,
    # which is the family of faults this whole module exists inside.
    span_hours: float | None = None

    @property
    def could_not_look(self) -> bool:
        return self.unreadable is not None

    @property
    def worst(self) -> tuple[str, int] | None:
        """The hook refusing most often, which is where a common cause hides.

        Nine refusals on 2026-09-14 read as nine incidents with nine local
        explanations and were one cause with nine faces. The count is what
        distinguishes them, and it is only visible once they are on one page.
        """
        if not self.by_hook:
            return None
        name = max(self.by_hook, key=lambda k: self.by_hook[k])
        return name, self.by_hook[name]


def _hook_name(row_id: str) -> str:
    """The hook out of an id shaped ``<hook>.sh-<pid>-<ms>``.

    Split from the right exactly twice: a hook name may itself contain hyphens
    — most of them do — and splitting from the left would return the first word
    of the name for every gate in the house.
    """
    return row_id.rsplit("-", 2)[0] if row_id else "unknown"


def read_stretch(session: str, log: Path | None = None) -> Stretch:
    """Refusals recorded for ``session``.

    Streams rather than loading: the log is tens of megabytes by the time it is
    interesting, and a reader that costs a second is a reader that gets called
    from nowhere.
    """
    path = log or default_log()
    if path is None:
        return Stretch(unreadable="no home directory resolved, so no timing log to read")
    if not path.is_file():
        return Stretch(unreadable=f"no timing log at {path}")
    counts: dict[str, int] = {}
    total = 0
    earliest: float | None = None
    latest: float | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue  # a torn line is one lost row, not a broken read
                if not isinstance(row, dict):
                    continue
                if row.get("phase") != "end":
                    continue
                # The span is measured across EVERY session in the log, not
                # just mine: it answers how far back the record itself goes,
                # which is a property of the file rather than of my stretch.
                stamp = row.get("ts_ms")
                if isinstance(stamp, (int, float)):
                    earliest = stamp if earliest is None else min(earliest, stamp)
                    latest = stamp if latest is None else max(latest, stamp)
                if row.get("session") != session:
                    continue
                if row.get("exit_code") in _ALLOWED:
                    continue
                total += 1
                name = _hook_name(str(row.get("id", "")))
                counts[name] = counts.get(name, 0) + 1
    except OSError as exc:
        return Stretch(unreadable=f"{type(exc).__name__}: {exc}")
    span = None
    if earliest is not None and latest is not None and latest > earliest:
        span = round((latest - earliest) / 3_600_000, 1)
    return Stretch(total=total, by_hook=counts, span_hours=span)


def describe(stretch: Stretch) -> str:
    """One block, or nothing when there is nothing to say.

    Silence is the common case and it is correct: most sessions refuse nothing
    worth surfacing, and a block that fires on an empty stretch is furniture
    within a day.
    """
    if stretch.could_not_look:
        return (
            "## REFUSALS THIS SESSION — could not look\n\n"
            f"  {stretch.unreadable}\n"
            "  This is NOT zero refusals. The reader could not read."
        )
    if stretch.total == 0:
        return ""
    lines = [
        "## REFUSALS THIS SESSION",
        "",
        f"  {stretch.total} refusal(s) recorded, across {len(stretch.by_hook)} gate(s).",
        "",
    ]
    for name, n in sorted(stretch.by_hook.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {n:3d}  {name}")
    worst = stretch.worst
    if worst and worst[1] >= 2:
        lines += [
            "",
            f"  {worst[0]} has refused {worst[1]} times. If that is the same refusal",
            "  repeating, it is one cause wearing several faces, and the thing to vary",
            "  is whatever has been held constant across all of them.",
        ]
    lines += [
        "",
        "  Andrew 2026-09-14, and his words rather than a paraphrase of them:",
        "  these failures are not a verdict on your character, but a roadmap of",
        "  where the edges of success lie.",
        "",
        "  SCOPE: this reads the shared hook library's exit trap. Eight of the",
        "  one hundred and thirty-four hooks do not source it and cannot appear",
        "  here, so a small count is a floor rather than a total.",
    ]
    if stretch.span_hours is not None:
        lines.append(f"  The log reaches back {stretch.span_hours} hour(s). It cannot say whether")
        lines.append("  any of this has been happening for longer than that.")
    return "\n".join(lines)
