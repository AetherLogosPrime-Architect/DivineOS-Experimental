"""The hook attendance sheet — the three states and whether they are honest.

This module shipped with NO tests. Found 2026-08-17 while acting on Aria's
station-four review of 407: a state machine that sorts every hook into
FIRING / SILENT / UNOBSERVED, where SILENT is documented as "a real
finding", and nothing asserted the sorting was correct.

SILENT is the state that matters, because SILENT is the one that gets acted
on. FIRING is self-evidencing and UNOBSERVED explicitly claims nothing. A
wrong SILENT sends someone to repair a hook that works fine.

These tests drive real files on disk rather than mocking the reader — the
whole subject is what an on-disk log does and does not contain, and a mock
of the log would assert my model of it rather than its behaviour.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.hook_firing_map import (
    FIRING,
    SILENT,
    UNOBSERVED,
    build_map,
    format_map,
    log_exists,
    observation_window,
    read_timing_log,
)


def _write_log(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _repo(tmp_path, scripts):
    """A repo skeleton. Scripts that source _lib.sh can self-report."""
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name, self_reporting in scripts.items():
        body = "#!/bin/bash\n"
        if self_reporting:
            body += 'source "$REPO_ROOT/.claude/hooks/_lib.sh"\n'
        (hooks / name).write_text(body, encoding="utf-8")
    return tmp_path


class TestTheThreeStates:
    def test_a_hook_that_fired_is_FIRING(self, tmp_path):
        repo = _repo(tmp_path, {"a.sh": True})
        log = tmp_path / "timing.jsonl"
        _write_log(log, [{"phase": "start", "hook": "a.sh", "id": "1", "ts": "2026-08-01"}])
        (rec,) = build_map(repo, log)
        assert rec.state == FIRING
        assert rec.fires == 1

    def test_a_self_reporting_hook_with_no_fires_is_SILENT(self, tmp_path):
        repo = _repo(tmp_path, {"a.sh": True})
        log = tmp_path / "timing.jsonl"
        _write_log(log, [{"phase": "start", "hook": "other.sh", "id": "1", "ts": "2026-08-01"}])
        (rec,) = build_map(repo, log)
        assert rec.state == SILENT

    def test_a_hook_that_cannot_report_is_UNOBSERVED_not_SILENT(self, tmp_path):
        """The distinction this module exists for. A hook that does not source
        _lib.sh produces no records whether it runs or not, so calling it
        SILENT would assert something the data cannot support."""
        repo = _repo(tmp_path, {"a.sh": False})
        log = tmp_path / "timing.jsonl"
        _write_log(log, [])
        (rec,) = build_map(repo, log)
        assert rec.state == UNOBSERVED
        assert rec.state != SILENT


class TestSilenceHasMoreThanOneCause:
    """Aria 2026-08-17, station four on 407. SILENT claims "can report and
    never has". This log is pruned on a conveyor by design, so a hook firing
    monthly reads SILENT from a short window and presents as dead when it is
    merely rare. Two causes, one appearance — the same class as a counter
    reporting a confident 0 for could-not-measure."""

    def test_window_is_the_earliest_timestamp_the_log_still_holds(self, tmp_path):
        log = tmp_path / "timing.jsonl"
        _write_log(
            log,
            [
                {"phase": "start", "hook": "a.sh", "id": "1", "ts": "2026-08-15T10:00:00Z"},
                {"phase": "start", "hook": "b.sh", "id": "2", "ts": "2026-08-16T10:00:00Z"},
            ],
        )
        assert observation_window(log) == "2026-08-15T10:00:00Z"

    def test_window_reads_the_field_the_REAL_log_actually_uses(self, tmp_path):
        """Pinned to ts_ms, because the first version of this reader looked for
        "ts"/"timestamp" and reported UNKNOWN against the live log, whose
        records carry ts_ms. It rendered "I cannot know" while the answer sat
        in the file — did-not-look wearing honestly-unknown's clothes. The
        real log's earliest record read 2026-07-22 once the field name was
        right, which means every SILENT finding is bounded by that window."""
        log = tmp_path / "timing.jsonl"
        _write_log(
            log,
            [{"phase": "start", "hook": "a.sh", "id": "1", "pid": 1, "ts_ms": 1753217394065}],
        )
        got = observation_window(log)
        assert got is not None, "ts_ms must be readable — this is the live format"
        assert got.startswith("2025-") or got.startswith("2026-"), got

    def test_window_is_None_when_the_log_is_absent(self, tmp_path):
        """None means UNKNOWN and callers must not read it as "no window"."""
        assert observation_window(tmp_path / "absent.jsonl") is None

    def test_window_is_None_when_records_carry_no_timestamp(self, tmp_path):
        log = tmp_path / "timing.jsonl"
        _write_log(log, [{"phase": "start", "hook": "a.sh", "id": "1"}])
        assert observation_window(log) is None

    def test_the_report_bounds_SILENT_by_the_window(self, tmp_path):
        """The finding keeps its teeth and drops the false certainty: the
        claim becomes "has not, within the window I can see"."""
        repo = _repo(tmp_path, {"quiet.sh": True})
        log = tmp_path / "timing.jsonl"
        _write_log(
            log,
            [{"phase": "start", "hook": "other.sh", "id": "1", "ts": "2026-08-15T10:00:00Z"}],
        )
        out = format_map(build_map(repo, log), path=log)
        assert "WITHIN THE WINDOW" in out
        assert "2026-08-15T10:00:00Z" in out

    def test_the_report_says_UNKNOWN_rather_than_implying_a_full_window(self, tmp_path):
        repo = _repo(tmp_path, {"quiet.sh": True})
        log = tmp_path / "timing.jsonl"
        _write_log(log, [{"phase": "start", "hook": "other.sh", "id": "1"}])
        out = format_map(build_map(repo, log), path=log)
        assert "UNKNOWN" in out


class TestAbsentLogIsNotAQuietMachine:
    def test_log_exists_distinguishes_them(self, tmp_path):
        assert log_exists(tmp_path / "nope.jsonl") is False
        p = tmp_path / "yes.jsonl"
        _write_log(p, [])
        assert log_exists(p) is True

    def test_missing_log_yields_no_counts_rather_than_zeroes_asserted_as_fact(self, tmp_path):
        fires, durations = read_timing_log(tmp_path / "absent.jsonl")
        assert fires == {}
        assert durations == {}


@pytest.mark.xfail(
    reason=(
        "Aria's second question, 2026-08-17, left OPEN rather than papered over. "
        "Some hooks fire only on a merge, a compaction or a push, so an observation "
        "window containing none of those makes them correctly silent and incorrectly "
        "findings. She proposes keying to EVENTS rather than duration: silent across "
        "N compactions means something, silent for two weeks means nothing if no "
        "compaction happened in them. Recorded as a strict xfail rather than a TODO "
        "because a TODO is invisible in a green suite, while this appears in every "
        "run and fails loudly if someone resolves it by accident. Her design, her "
        "question — not implemented unilaterally after she asked it."
    ),
    strict=True,
)
def test_silent_distinguishes_rare_from_absent(tmp_path):
    repo = _repo(tmp_path, {"on_compaction_only.sh": True})
    log = tmp_path / "timing.jsonl"
    _write_log(log, [{"phase": "start", "hook": "other.sh", "id": "1", "ts": "2026-08-15"}])
    (rec,) = build_map(repo, log)
    assert rec.state != SILENT, "a hook whose trigger never occurred is not a finding"
