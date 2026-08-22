"""The aggregate measurer, and the two ways it could lie precisely.

per prereg-b76f9f71c5d7

This module exists because nothing else in the house sums. Aletheia, 2026-08-21:
"no instrument in this house measures a sum -- they all measure instances." So
these tests care less about arithmetic than about the two failure modes that
would make the sum *look* authoritative while being wrong:

  1. Batching that does not correspond to real tool calls. The timing log has
     no correlation id; batches are inferred from start-time clustering. If
     that inference is wrong, every number is wrong in a way that looks
     precise, which is worse than being obviously wrong.

  2. A cheap run that vanishes instead of registering as cheap. That already
     happened once, hours before this file: a fast-bail added to
     check-branch-on-push.sh exited before the instrumentation, so the hook's
     recorded median ROSE by 945ms while the hook itself got 16x faster. The
     bailed row type exists to end that, and it is only worth having if the
     reader actually counts it.

Real rows in real files, no mocking of the parser. The subject is what an
on-disk log does and does not contain, and a mock would assert my model of it.
"""

from __future__ import annotations

import json

from divineos.core.hook_budget import (
    PER_CALL_BUDGET_MS,
    analyse,
    batch_by_gap,
    count_unclosed_runs,
    format_report,
    read_completed_runs,
    summarise,
)


def _row(**kw) -> str:
    return json.dumps(kw)


def _log(tmp_path, rows: list[str]):
    p = tmp_path / "hook_timing.jsonl"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p


def _pair(hook: str, ts: int, duration: int, session: str = "s", wpid: str = "w") -> list[str]:
    ident = f"{hook}-100-{ts}"
    return [
        _row(id=ident, hook=hook, pid=100, session=session, wpid=wpid, phase="start", ts_ms=ts),
        _row(
            id=ident,
            session=session,
            wpid=wpid,
            phase="end",
            exit_code=0,
            ts_ms=ts + duration,
            duration_ms=duration,
        ),
    ]


class TestCheapRunsMustRegisterAsCheap:
    """The defect this module was written BY, not only for."""

    def test_a_bailed_run_is_read_and_counted(self, tmp_path):
        log = _log(
            tmp_path,
            _pair("slow.sh", 1_000, 500)
            + [
                _row(
                    id="fast.sh-101-1600",
                    hook="fast.sh",
                    pid=101,
                    session="s",
                    wpid="w",
                    phase="bailed",
                    ts_ms=1_600,
                    duration_ms=0,
                    reason="command-cannot-contain-a-push",
                )
            ],
        )
        runs = read_completed_runs(log)

        assert len(runs) == 2, "the bailed run must appear at all"
        bailed = [r for r in runs if r.bailed]
        assert len(bailed) == 1
        assert bailed[0].hook == "fast.sh"
        assert bailed[0].duration_ms == 0

    def test_bailing_is_visible_in_the_report(self, tmp_path):
        """Cheap must read as cheap, never as absent.

        Without this the only evidence a hook got fast is that it stopped
        appearing -- indistinguishable from it having been removed, or broken.
        """
        rows = _pair("slow.sh", 1_000, 400)
        for i in range(3):
            rows.append(
                _row(
                    id=f"fast.sh-10{i}-{1_100 + i}",
                    hook="fast.sh",
                    pid=100 + i,
                    session="s",
                    wpid="w",
                    phase="bailed",
                    ts_ms=1_100 + i,
                    duration_ms=0,
                )
            )
        report = summarise(batch_by_gap(read_completed_runs(_log(tmp_path, rows))))

        assert report.bailed_runs == 3
        assert report.hooks_seen == 4

    def test_an_unfinished_run_is_not_counted_as_free(self, tmp_path):
        """A start with no end is unknown cost, not zero cost.

        Counting it as zero would make a HUNG stack read as the cheapest one,
        which inverts the exact thing this module exists to see.
        """
        rows = _pair("finished.sh", 1_000, 300)
        rows.append(
            _row(
                id="hung.sh-999-1500",
                hook="hung.sh",
                pid=999,
                session="s",
                wpid="w",
                phase="start",
                ts_ms=1_500,
            )
        )
        runs = read_completed_runs(_log(tmp_path, rows))

        assert [r.hook for r in runs] == ["finished.sh"]


class TestBatchingIsTheWeakJoint:
    def test_runs_close_together_are_one_call(self, tmp_path):
        rows = _pair("a.sh", 1_000, 100) + _pair("b.sh", 1_150, 100) + _pair("c.sh", 1_300, 100)
        batches = batch_by_gap(read_completed_runs(_log(tmp_path, rows)))

        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_a_long_gap_starts_a_new_call(self, tmp_path):
        rows = _pair("a.sh", 1_000, 100) + _pair("b.sh", 90_000, 100)
        batches = batch_by_gap(read_completed_runs(_log(tmp_path, rows)))

        assert len(batches) == 2

    def test_two_windows_do_not_merge_into_one_call(self, tmp_path):
        """Aria hit this exact shape on this exact log, 2026-08-18.

        Every window on the machine appends to one file. Grouping purely by
        time would interleave two windows' stacks into a single batch and
        double the apparent per-call cost. Her orphan-burst census over-counted
        by roughly two orders of magnitude for want of knowing whose row was
        whose, which is why session and wpid are stamped on every row.
        """
        rows = _pair("a.sh", 1_000, 100, session="s1", wpid="w1") + _pair(
            "b.sh", 1_050, 100, session="s2", wpid="w2"
        )
        batches = batch_by_gap(read_completed_runs(_log(tmp_path, rows)))

        assert len(batches) == 2, "two windows' hooks are not one tool call"


class TestTheVerdict:
    def test_offenders_rank_by_total_not_by_worst_single_run(self, tmp_path):
        """A steady 200ms tax outranks one 3-second spike, and should.

        Ranking by max points at the tail, which is the per-instance view this
        module exists to stop taking.
        """
        rows: list[str] = []
        for i in range(20):
            rows += _pair("steady.sh", 1_000 + i * 100_000, 200)
        rows += _pair("spike.sh", 9_000_000, 3_000)
        report = summarise(batch_by_gap(read_completed_runs(_log(tmp_path, rows))))

        assert report.worst_offenders[0][0] == "steady.sh"
        assert report.worst_offenders[0][1] == 4_000

    def test_over_budget_is_decided_on_p95_not_the_median(self, tmp_path):
        """Most calls being fine is not the same as the stack being fine.

        The freeze Andrew reported was a tail event; a median-based verdict
        would have called that stack healthy while he sat through minutes of
        blank screen.
        """
        rows: list[str] = []
        for i in range(30):
            rows += _pair("cheap.sh", 1_000 + i * 100_000, 10)
        for i in range(3):
            rows += _pair("awful.sh", 50_000_000 + i * 100_000, PER_CALL_BUDGET_MS * 4)
        report = summarise(batch_by_gap(read_completed_runs(_log(tmp_path, rows))))

        assert report.median_ms < PER_CALL_BUDGET_MS
        assert report.over_budget, "a healthy median must not mask an unhealthy tail"

    def test_an_absent_log_reports_nothing_rather_than_zero_cost(self, tmp_path):
        """No data must not render as a clean bill of health."""
        report = summarise(batch_by_gap(read_completed_runs(tmp_path / "nope.jsonl")))

        assert report.batches == 0
        assert not report.over_budget
        assert report.hooks_seen == 0


class TestHangsMustBeCountable:
    """The half this module was missing, and the error it produced.

    read_completed_runs correctly excludes unfinished runs from cost — its
    docstring says why, and test_an_unfinished_run_is_not_counted_as_free
    pins it. But nothing COUNTED them, so a suspended stack was invisible in
    the one module anyone consults about hook cost.

    That is not hypothetical. Claude Code on Windows sometimes spawns a hook
    process suspended and never resumes it — zero CPU, alive past its timeout,
    never having executed an instruction (anthropics/claude-code #77078).
    Such a hook emits a start row and nothing else. Measured on the live log
    2026-08-22: 597 of them. I reported "78 seconds of stall" from end-rows
    while Andrew was asking about five-minute freezes.
    """

    @staticmethod
    def _start_only(hook: str, ts: int, session: str = "s") -> str:
        ident = f"{hook}-100-{ts}"
        return _row(
            id=ident, hook=hook, pid=100, session=session, wpid="w", phase="start", ts_ms=ts
        )

    def test_a_start_without_an_end_is_counted(self, tmp_path):
        rows = _pair("fine.sh", 1_000, 200) + [self._start_only("hung.sh", 2_000)]

        total, worst = count_unclosed_runs(_log(tmp_path, rows))

        assert total == 1, "a hook that never finished must be visible"
        assert worst == [("hung.sh", 1)]

    def test_a_bailed_run_is_a_finish_not_a_hang(self, tmp_path):
        """A fast-bail is a legitimate ending. Counting it as a hang inflates
        the number — my own hand-rolled version did exactly that and reported
        650 where the real figure was 597."""
        ident = "bailer.sh-100-3000"
        rows = [
            _row(
                id=ident,
                hook="bailer.sh",
                pid=100,
                session="s",
                wpid="w",
                phase="start",
                ts_ms=3_000,
            ),
            _row(id=ident, hook="bailer.sh", session="s", wpid="w", phase="bailed", ts_ms=3_001),
        ]

        total, worst = count_unclosed_runs(_log(tmp_path, rows))

        assert total == 0, "bailed is finished; only start-with-no-ending is a hang"
        assert worst == []

    def test_rows_with_no_session_are_still_counted(self, tmp_path):
        """The load-bearing case. 576 of 647 unclosed rows measured on the live
        log carried session=None — the process hangs before it can identify
        itself. Any session-keyed grouping drops ~89% of the failures silently,
        which is precisely how this went unseen for a day."""
        rows = [
            _row(id="a.sh-1-10", hook="a.sh", pid=1, phase="start", ts_ms=10),
            _row(id="b.sh-2-20", hook="b.sh", pid=2, session=None, phase="start", ts_ms=20),
        ]

        total, worst = count_unclosed_runs(_log(tmp_path, rows))

        assert total == 2, "session-less hangs must count; they are the majority"
        assert dict(worst) == {"a.sh": 1, "b.sh": 1}

    def test_worst_offenders_are_ranked(self, tmp_path):
        rows = [self._start_only("noisy.sh", 1_000 + i) for i in range(3)]
        rows.append(self._start_only("quiet.sh", 5_000))

        total, worst = count_unclosed_runs(_log(tmp_path, rows))

        assert total == 4
        assert worst[0] == ("noisy.sh", 3)

    def test_missing_log_fails_soft(self, tmp_path):
        assert count_unclosed_runs(tmp_path / "nope.jsonl") == (0, [])


class TestAnalyseKeepsTheHalvesTogether:
    """The entry point exists so the two halves cannot be used apart.

    Duration statistics come only from runs that finished. Counting the
    unfinished ones is a separate call. A caller who makes the first and
    forgets the second gets a confident report about the healthy half of a
    hanging stack -- which is the error this whole class descends from.
    """

    def test_a_hang_reaches_the_report_without_the_caller_asking(self, tmp_path):
        rows = _pair("fine.sh", 1_000, 100) + [
            _row(id="hung.sh-9-2000", hook="hung.sh", pid=9, phase="start", ts_ms=2_000)
        ]
        report = analyse(_log(tmp_path, rows))

        assert report.has_hangs
        assert report.unclosed_runs == 1
        assert report.unclosed_offenders == [("hung.sh", 1)]

    def test_the_hang_is_visible_in_the_rendered_text(self, tmp_path):
        """Present in the dataclass is not the same as present on the page.

        Anyone diagnosing a freeze reads format_report, not the object.
        """
        rows = _pair("fine.sh", 1_000, 100) + [
            _row(id="hung.sh-9-2000", hook="hung.sh", pid=9, phase="start", ts_ms=2_000)
        ]
        text = format_report(analyse(_log(tmp_path, rows)))

        assert "NEVER FINISHED" in text
        assert "hung.sh" in text

    def test_a_clean_log_does_not_cry_hang(self, tmp_path):
        report = analyse(_log(tmp_path, _pair("fine.sh", 1_000, 100)))

        assert not report.has_hangs
        assert "NEVER FINISHED" not in format_report(report)

    def test_summarise_still_defaults_to_no_hang_data(self, tmp_path):
        """The old two-call path must not start reporting hangs it never read.

        Zero-because-unmeasured and zero-because-none are different facts;
        analyse() is what distinguishes them, and summarise() alone cannot.
        """
        rows = _pair("fine.sh", 1_000, 100) + [
            _row(id="hung.sh-9-2000", hook="hung.sh", pid=9, phase="start", ts_ms=2_000)
        ]
        report = summarise(batch_by_gap(read_completed_runs(_log(tmp_path, rows))))

        assert report.unclosed_runs == 0
        assert not report.has_hangs
