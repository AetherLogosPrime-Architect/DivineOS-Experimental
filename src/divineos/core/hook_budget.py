"""What the whole hook stack costs per tool call, which nothing else measures.

per prereg-b76f9f71c5d7

## The shape this exists for

Aletheia named it 2026-08-21, reading the freeze numbers:

    "Nothing hung is why nobody found it. Every hook passed its own liveness
    check. The p95 of any single one is unremarkable. The cost is entirely in
    the serial sum, and no instrument in this house measures a sum -- they all
    measure instances."

    "The aggregate has no owner. Twenty-six mechanisms each correct, each
    cheap, each individually justified -- and nothing holds the total or has
    authority to refuse the twenty-seventh."

She is describing this codebase accurately. ``hook_firing_map`` asks WHICH
hooks fire. ``hook_telemetry`` measures one hook's byte cost and whether its
output got consumed. ``_lib.sh`` records per-hook start/end durations. Three
instruments, all per-instance, none summing.

Measured 2026-08-21 from ~/.divineos/hook_timing.jsonl, after Andrew reported
freezing for seven minutes at a stretch with the token counter stuck:

    SUM OF MEANS : 40.8 s   per tool call, before any command starts
    SUM OF P95   : 73.8 s   a bad-luck turn
    26 per-call hooks

Every one of those hooks was justified when it was added. I added most of
them. The defect is not in any of them; it is that nobody was holding the
total, so twenty-six correct decisions composed into minutes of dead screen.

## What this module deliberately does NOT claim

**The batching is inferred, and that is the weakest joint.** The timing log
has no correlation id tying a hook run to the tool call that triggered it --
only ``session``, ``wpid``, and a start timestamp. So runs are grouped by
clustering start times within a session: consecutive runs separated by less
than ``BATCH_GAP_MS`` are treated as one call's stack.

That is a heuristic, not a measurement. If it is wrong, every number here is
wrong in a way that *looks* precise, which is worse than being obviously
wrong. It is named in the prereg as a falsifier for exactly that reason. The
honest defence is that hooks in one stack fire back-to-back in tens of
milliseconds while tool calls are separated by model-generation time, so the
gap is large and bimodal -- but that is an argument, and the falsifier stands
until someone drives known calls through it and checks the grouping.

**It does not block anything.** A gate that refuses the twenty-seventh hook
would need authority this module does not have and should not quietly grant
itself. What it does is make the total sayable, and say it loudly when the
declared budget is exceeded. Whether that is enough is the prereg's actual
question, and the answer I expect to have to face is that measurement was
never the missing piece -- authority was.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# Two consecutive hook runs closer than this belong to the same tool call.
#
# Hooks in one stack fire back-to-back; separate tool calls are divided by
# model generation, which is orders of magnitude longer. 2 seconds sits in
# that valley with room on both sides. Deliberately generous: merging two
# calls into one batch OVER-states the per-call total, and an instrument
# whose error direction is "sounds worse than it is" will get checked, while
# one that under-states gets believed.
BATCH_GAP_MS = 2_000

# What the stack is allowed to cost before this says so out loud.
#
# 5 seconds, chosen against the measured floor rather than against comfort:
# bash alone costs ~25ms to spawn, a hook that resolves an interpreter costs
# ~120ms after the 2026-08-21 repair, and twenty-six of those is ~3s. So 5s
# is "the current stack, working correctly, with headroom" -- not a target
# negotiated down from 40.8s. A budget set at what the system currently does
# is not a budget; it is a description wearing a budget's name.
PER_CALL_BUDGET_MS = 5_000

_DEFAULT_TAIL_BYTES = 4_000_000


@dataclass(frozen=True)
class HookRun:
    """One completed hook execution, as the timing log recorded it."""

    hook: str
    session: str
    wpid: str
    start_ms: int
    duration_ms: int
    bailed: bool = False


@dataclass(frozen=True)
class BudgetReport:
    """The per-call totals, and whether they are over the declared budget."""

    batches: int
    hooks_seen: int
    median_ms: int
    p95_ms: int
    worst_ms: int
    over_budget_batches: int
    bailed_runs: int
    worst_offenders: list[tuple[str, int]]
    unclosed_runs: int = 0
    unclosed_offenders: list[tuple[str, int]] = field(default_factory=list)

    @property
    def over_budget(self) -> bool:
        return self.p95_ms > PER_CALL_BUDGET_MS

    @property
    def has_hangs(self) -> bool:
        return self.unclosed_runs > 0


def read_completed_runs(
    log_path: Path | str, tail_bytes: int = _DEFAULT_TAIL_BYTES
) -> list[HookRun]:
    """Completed runs from the timing log, newest tail only.

    Only ``end`` rows are read: they carry ``duration_ms``, and a start with
    no end is an unfinished run whose cost is unknown. Counting an unfinished
    hook as zero would make a hung stack look cheap, which inverts the thing
    this module exists to see.

    Fails soft to an empty list on every I/O and parse error. An instrument
    that raises inside a reporting path takes down the thing it reports on.
    """
    path = Path(log_path)
    if not path.is_file():
        return []
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - tail_bytes))
            chunk = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    runs: list[HookRun] = []
    names: dict[str, str] = {}
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        row_id = str(row.get("id", ""))
        if row.get("phase") == "start":
            # The hook NAME lives on the start row only; the end row carries
            # the duration. Neither row alone identifies a costed run.
            hook = str(row.get("hook", "")) or _hook_from_id(row_id)
            if row_id:
                names[row_id] = hook
            continue
        if row.get("phase") == "bailed":
            # A hook that exited early WITHOUT doing its work. Costs ~0 and is
            # the whole point of a fast-bail -- but it must appear, or a hook
            # that got cheap is indistinguishable from a hook that stopped
            # running. That confusion is what this row type exists to end, and
            # it cost a wrong before/after comparison to find.
            try:
                start = int(row.get("ts_ms"))
            except (TypeError, ValueError):
                continue
            runs.append(
                HookRun(
                    hook=str(row.get("hook", "")) or _hook_from_id(row_id) or "unknown",
                    session=str(row.get("session", "")),
                    wpid=str(row.get("wpid", "")),
                    start_ms=start,
                    duration_ms=0,
                    bailed=True,
                )
            )
            continue
        if row.get("phase") != "end":
            continue
        try:
            duration = int(row.get("duration_ms"))
            start = int(row.get("ts_ms")) - duration
        except (TypeError, ValueError):
            continue
        runs.append(
            HookRun(
                hook=names.get(row_id) or _hook_from_id(row_id) or "unknown",
                session=str(row.get("session", "")),
                wpid=str(row.get("wpid", "")),
                start_ms=start,
                duration_ms=max(0, duration),
            )
        )
    runs.sort(key=lambda r: r.start_ms)
    return runs


def count_unclosed_runs(
    log_path: Path | str, tail_bytes: int = _DEFAULT_TAIL_BYTES
) -> tuple[int, list[tuple[str, int]]]:
    """Invocations that STARTED and never finished. Returns (total, worst).

    The companion to ``read_completed_runs``, and the half that was missing.
    That function is right to exclude unfinished runs from cost -- its docstring
    says so -- but nothing then COUNTED them, so the hangs were invisible in the
    one module anyone would consult about hook cost.

    WHAT THIS EXISTS TO SEE (knowledge bb483b09, 2026-08-22). Claude Code on
    Windows sometimes spawns a hook process SUSPENDED and never resumes it:
    all threads in WaitReason=Suspended, UserModeTime zero, alive far past its
    declared timeout, never having executed an instruction
    (anthropics/claude-code issue #77078; root cause upstream and unknown).
    Such a hook emits a ``start`` row and nothing else, ever.

    So every duration statistic in this module is drawn, by construction, from
    the population that did NOT hang. Reporting p95 while a stack is suspended
    describes the healthy hooks and says nothing about the freeze -- which is
    exactly the error that produced this function: "78 seconds of stall this
    session" was computed from end-rows and handed to Andrew while he was
    asking about five-minute hangs.

    NEVER GROUP THIS BY SESSION. 576 of 647 unclosed rows measured 2026-08-22
    carried ``session=None`` -- the process hangs before it can identify
    itself. A session filter drops ~89% of the failures and returns a
    clean-looking aggregate over the remainder, silently. ``batch_by_gap``
    partitions by ``(session, wpid)`` for good reasons that do not apply here.

    THE COUNT IS SCOPED TO THE TAIL WINDOW and scales with it -- 278 over the
    default 4MB against 650 over the whole 7.4MB log, same file, same moment.
    Neither is wrong; a reader comparing two runs at different ``tail_bytes``
    without knowing that would take a window change for a real change. The
    truncation is safe in the direction that matters: cutting a ``start`` away
    from its surviving ``end`` cannot invent a hang, only hide one. The one
    genuine over-count is a hook still legitimately running at read time.

    Fails soft to ``(0, [])`` like its companion: an instrument that raises
    inside a reporting path takes down the thing it reports on.
    """
    path = Path(log_path)
    if not path.is_file():
        return 0, []
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - tail_bytes))
            chunk = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return 0, []

    started: dict[str, str] = {}
    finished: set[str] = set()
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        row_id = str(row.get("id", ""))
        if not row_id:
            continue
        phase = row.get("phase")
        if phase == "start":
            started[row_id] = str(row.get("hook", "")) or _hook_from_id(row_id) or "unknown"
        elif phase in ("end", "bailed"):
            # `bailed` is a legitimate finish: the hook decided not to work.
            finished.add(row_id)

    unclosed: dict[str, int] = {}
    for row_id, hook in started.items():
        if row_id not in finished:
            unclosed[hook] = unclosed.get(hook, 0) + 1
    worst = sorted(unclosed.items(), key=lambda kv: -kv[1])
    return sum(unclosed.values()), worst


def _hook_from_id(row_id: str) -> str:
    """Recover the hook name from an id shaped ``<name>-<pid>-<ms>``.

    The tail of the log can begin mid-stack, so an end row's matching start
    may have been cut off. Without this the run counts as "unknown" and the
    worst-offender list loses its most interesting entries -- the ones from
    the busiest stretches, which are exactly the ones worth naming.
    """
    parts = row_id.rsplit("-", 2)
    return parts[0] if len(parts) == 3 else ""


def batch_by_gap(runs: list[HookRun], gap_ms: int = BATCH_GAP_MS) -> list[list[HookRun]]:
    """Group runs into per-tool-call stacks by start-time clustering.

    Split per (session, wpid) first: one window's hooks are not another
    window's, and a shared log with several windows appending would otherwise
    interleave two stacks into one batch and double the apparent total. Aria
    hit precisely that shape on this same log -- her orphan-burst census
    over-counted by two orders of magnitude because the file could not say
    whose row was whose.
    """
    per_window: dict[tuple[str, str], list[HookRun]] = {}
    for run in runs:
        per_window.setdefault((run.session, run.wpid), []).append(run)

    batches: list[list[HookRun]] = []
    for window_runs in per_window.values():
        current: list[HookRun] = []
        previous_start: int | None = None
        for run in window_runs:
            if previous_start is not None and run.start_ms - previous_start > gap_ms:
                batches.append(current)
                current = []
            current.append(run)
            previous_start = run.start_ms
        if current:
            batches.append(current)
    return batches


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def summarise(
    batches: list[list[HookRun]],
    unclosed: tuple[int, list[tuple[str, int]]] = (0, []),
) -> BudgetReport:
    """Per-call totals plus the hooks contributing most to them.

    The offenders are ranked by TOTAL contribution, not by worst single run.
    A hook costing 200ms on every one of a thousand calls outranks one that
    spiked to 8 seconds once, and the first is the one worth fixing. Ranking
    by max would point at the tail, which is the per-instance view this module
    exists to stop taking.
    """
    totals = [sum(r.duration_ms for r in batch) for batch in batches]
    contribution: dict[str, int] = {}
    hooks_seen = 0
    bailed_runs = 0
    for batch in batches:
        hooks_seen += len(batch)
        bailed_runs += sum(1 for r in batch if r.bailed)
        for run in batch:
            contribution[run.hook] = contribution.get(run.hook, 0) + run.duration_ms

    worst = sorted(contribution.items(), key=lambda kv: kv[1], reverse=True)[:8]
    return BudgetReport(
        batches=len(batches),
        hooks_seen=hooks_seen,
        median_ms=_percentile(totals, 0.50),
        p95_ms=_percentile(totals, 0.95),
        worst_ms=max(totals) if totals else 0,
        over_budget_batches=sum(1 for t in totals if t > PER_CALL_BUDGET_MS),
        bailed_runs=bailed_runs,
        worst_offenders=worst,
        unclosed_runs=unclosed[0],
        unclosed_offenders=list(unclosed[1]),
    )


def analyse(log_path: Path | str, tail_bytes: int = _DEFAULT_TAIL_BYTES) -> BudgetReport:
    """The whole picture from one call: what finished, and what never did.

    This exists because the two halves came apart once. ``read_completed_runs``
    drops unfinished runs on purpose -- unknown cost is not zero cost -- but for
    a day nothing counted the drops, so a stack full of suspended processes read
    as a stack that was merely slow. I reported 78 seconds of measured stall
    while Andrew was sitting through five-minute freezes, and the gap was
    entirely rows my reader was structurally unable to see.

    Callers should reach for this rather than for ``summarise`` directly, so
    that omitting the hang count stops being something a caller can do.
    """
    runs = read_completed_runs(log_path, tail_bytes=tail_bytes)
    return summarise(batch_by_gap(runs), count_unclosed_runs(log_path, tail_bytes=tail_bytes))


def format_report(report: BudgetReport) -> str:
    """Human-readable, and loud when the budget is blown.

    Says the batch count first. Every number below it is an average over
    inferred groupings, and a reader who does not know how many groupings
    cannot tell a measurement from an anecdote.
    """
    lines = [
        "=== HOOK BUDGET — what the whole stack costs per tool call ===",
        "",
        f"  tool calls measured : {report.batches}  (batched by <{BATCH_GAP_MS}ms gap; inferred, not correlated)",
        f"  hook runs           : {report.hooks_seen}"
        + (f"   ({report.bailed_runs} bailed early, ~0ms)" if report.bailed_runs else ""),
        "",
        f"  median per call     : {report.median_ms:>7,} ms",
        f"  p95 per call        : {report.p95_ms:>7,} ms",
        f"  worst call          : {report.worst_ms:>7,} ms",
        f"  budget              : {PER_CALL_BUDGET_MS:>7,} ms",
        f"  calls over budget   : {report.over_budget_batches} of {report.batches}",
    ]
    if report.worst_offenders:
        lines += ["", "  biggest contributors (by TOTAL cost, not worst single run):"]
        lines += [f"    {total:>8,} ms  {hook}" for hook, total in report.worst_offenders]
    if report.unclosed_offenders:
        lines += ["", "  never finished (start row, no end -- cost unknown, not zero):"]
        lines += [f"    {count:>8,}     {hook}" for hook, count in report.unclosed_offenders]
    lines += [""]
    if report.has_hangs:
        lines += [
            f"  [!] {report.unclosed_runs:,} HOOK RUNS NEVER FINISHED (within the tail read).",
            "      None of them appear in any number above; a run with no end row",
            "      has no duration to sum, so the timings describe only the stack's",
            "      healthy half. On Windows, Claude Code sometimes spawns a hook",
            "      process suspended and never resumes it -- zero CPU, alive well",
            "      past its declared timeout (anthropics/claude-code#77078). That",
            "      looks exactly like this, and it is felt as a freeze, not as cost.",
            "",
        ]
    if report.over_budget:
        lines += [
            f"  [!] OVER BUDGET — p95 is {report.p95_ms:,}ms against a {PER_CALL_BUDGET_MS:,}ms budget.",
            "      Every hook in that sum may be individually fine. That is the point:",
            "      the aggregate has no owner, so nothing refuses the next addition.",
            "      Removing one, merging two, or adding a pure-bash fast-bail all count.",
        ]
    else:
        lines += ["  [=] within budget."]
    return "\n".join(lines)
