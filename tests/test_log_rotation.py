"""Tests for flat-log rotation.

The property that matters is not "the file got smaller" — it is that the
question the file answered is still answerable afterwards. Most of these tests
are about the roster surviving, not about bytes.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from divineos.core import log_rotation as lr


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _timing_rows(hook, n, start_ms=1000):
    """n start/end pairs, in the exact shape .claude/hooks/_lib.sh writes them.

    End rows deliberately carry no `hook` field — that is the real format, and
    the reason _timing_hook_name has to recover the name from the id.
    """
    rows = []
    for i in range(n):
        rid = f"{hook}-{1000 + i}-{start_ms + i}"
        rows.append({"id": rid, "hook": hook, "phase": "start", "ts_ms": start_ms + i})
        rows.append({"id": rid, "phase": "end", "exit_code": 0, "ts_ms": start_ms + i + 5})
    return rows


@pytest.fixture
def home(tmp_path):
    """An isolated DivineOS home. Never the real one — these tests delete rows."""
    d = tmp_path / ".divineos"
    d.mkdir()
    return d


def test_small_file_is_left_alone(home):
    path = home / "hook_timing.jsonl"
    _write(path, _timing_rows("a.sh", 3))
    before = path.read_text(encoding="utf-8")

    result = lr.rotate_log(lr.POLICIES[0], home=home)

    assert result.rotated is False
    assert path.read_text(encoding="utf-8") == before


def test_end_rows_are_attributed_to_their_hook(home):
    """The bug this guards: end rows carry only `id`, so a reader keying on
    `hook` alone concludes every hook started and never finished."""
    path = home / "hook_timing.jsonl"
    _write(path, _timing_rows("b.sh", 50))

    lr.rotate_log(lr.POLICIES[0], home=home, min_bytes=0)

    roster = lr._load_roster(lr.roster_path(home, "hook_timing.jsonl"))
    assert roster["b.sh"]["starts"] == 50
    assert roster["b.sh"]["ends"] == 50
    assert lr.hooks_never_completed(home=home) == {}


def test_hook_that_never_completes_is_reported(home):
    path = home / "hook_timing.jsonl"
    rows = _timing_rows("healthy.sh", 5)
    rows.append({"id": "stuck.sh-77-900", "hook": "stuck.sh", "phase": "start", "ts_ms": 900})
    _write(path, rows)

    lr.rotate_log(lr.POLICIES[0], home=home, min_bytes=0)

    assert lr.hooks_never_completed(home=home) == {"stuck.sh": 1}


def test_by_absence_signal_survives_the_rows_being_dropped(home):
    """The load-bearing property. A hook that ran only in the dropped prefix
    must still be nameable, or rotation has destroyed the instrument."""
    path = home / "hook_timing.jsonl"
    rows = _timing_rows("ancient.sh", 2, start_ms=1) + _timing_rows("recent.sh", 60, start_ms=9000)
    _write(path, rows)

    policy = lr.LogPolicy(
        filename="hook_timing.jsonl", fold=lr._fold_timing, cumulative=True, keep_lines=10
    )
    lr.rotate_log(policy, home=home, min_bytes=0)

    kept = path.read_text(encoding="utf-8")
    assert "ancient.sh" not in kept  # its rows really are gone
    roster = lr._load_roster(lr.roster_path(home, "hook_timing.jsonl"))
    assert roster["ancient.sh"]["starts"] == 2  # and it is still nameable


def test_roster_accumulates_across_repeated_rotations(home):
    """A roster that reset each rotation would be worse than useless — it would
    look authoritative and undercount."""
    path = home / "hook_timing.jsonl"
    policy = lr.LogPolicy(
        filename="hook_timing.jsonl", fold=lr._fold_timing, cumulative=True, keep_lines=4
    )

    _write(path, _timing_rows("c.sh", 20, start_ms=100))
    lr.rotate_log(policy, home=home, min_bytes=0)
    _write(path, _timing_rows("c.sh", 30, start_ms=5000))
    lr.rotate_log(policy, home=home, min_bytes=0)

    roster = lr._load_roster(lr.roster_path(home, "hook_timing.jsonl"))
    assert roster["c.sh"]["starts"] == 50
    assert roster["c.sh"]["first_ms"] == 100  # oldest first-seen is not lost
    assert roster["c.sh"]["last_ms"] >= 5000


def test_liveness_keeps_every_failure_and_folds_the_heartbeat(home):
    """`hook-liveness.log` exists to answer which children FAILED. Failures are
    kept verbatim however old; healthy_source becomes a count."""
    path = home / "hook-liveness.log"
    rows = [{"ts": "t", "hook": "x.sh", "reason": "healthy_source"} for _ in range(500)]
    rows.insert(0, {"ts": "t0", "hook": "x.sh", "reason": "child_hook_failed", "detail": "rc=2"})
    _write(path, rows)

    policy = lr.LogPolicy(
        filename="hook-liveness.log",
        fold=lr._fold_counter,
        keep_if=lr._liveness_is_signal,
        keep_lines=5,
    )
    result = lr.rotate_log(policy, home=home, min_bytes=0)

    kept = path.read_text(encoding="utf-8")
    assert "child_hook_failed" in kept  # oldest row of all, still kept
    assert "healthy_source" not in kept
    assert result.lines_after == 1
    roster = lr._load_roster(lr.roster_path(home, "hook-liveness.log"))
    assert roster["x.sh"]["healthy_source"] == 500


def test_unparseable_rows_are_kept_not_eaten(home):
    """Malformed rows are evidence of a writer bug. Dropping them silently
    erases the only trace that the bug happened."""
    path = home / "hook_timing.jsonl"
    text = "\n".join(json.dumps(r) for r in _timing_rows("d.sh", 3))
    path.write_text(text + "\n{not json at all\n", encoding="utf-8")

    lr.rotate_log(lr.POLICIES[0], home=home, min_bytes=0)

    assert "{not json at all" in path.read_text(encoding="utf-8")


def test_dry_run_changes_nothing_on_disk(home):
    path = home / "hook_timing.jsonl"
    _write(path, _timing_rows("e.sh", 40))
    before = path.read_text(encoding="utf-8")

    result = lr.rotate_log(lr.POLICIES[0], home=home, min_bytes=0, dry_run=True)

    assert result.rotated is False
    assert result.roster_entries == 1
    assert path.read_text(encoding="utf-8") == before
    assert not lr.roster_path(home, "hook_timing.jsonl").exists()


def test_missing_file_is_not_an_error(home):
    result = lr.rotate_log(lr.POLICIES[0], home=home, min_bytes=0)
    assert result.rotated is False
    assert result.reason == "missing"


def test_rotate_all_reports_one_result_per_policy(home):
    results = lr.rotate_all(home=home, min_bytes=0)
    assert [r.name for r in results] == [p.filename for p in lr.POLICIES]


def test_keep_bytes_bounds_a_log_that_is_inside_its_line_budget(home):
    """A line budget is not a size budget.

    Regression for 2026-08-20: retrieval_tally.jsonl sat at 24.4MB while
    INSIDE its 2,000-line budget, because each row embeds whole surfaced-path
    lists. Rotation reported success and freed 480KB. Wide rows are the case
    keep_bytes exists for, so the fixture builds wide rows.
    """
    path = home / "hook_timing.jsonl"
    rows = _timing_rows("wide.sh", 20)
    for row in rows:
        row["pad"] = "x" * 5_000  # wide payloads are the case keep_bytes exists for
    _write(path, rows)
    assert path.stat().st_size > 200_000, "fixture must exceed the byte budget to test it"

    policy = replace(lr.POLICIES[0], keep_lines=1_000, keep_bytes=50_000)
    result = lr.rotate_log(policy, home=home, min_bytes=0)

    assert result.rotated is True
    # The line budget alone would have kept all 40 rows and changed nothing.
    assert result.lines_before == 40
    assert result.lines_after < 40
    assert path.stat().st_size <= 50_000
    # Newest rows survive; the oldest are the ones folded into the roster.
    remaining = path.read_text(encoding="utf-8")
    assert rows[-1]["id"] in remaining
    assert rows[0]["id"] not in remaining


def test_keep_bytes_unset_leaves_line_budget_behaviour_unchanged(home):
    """The byte bound is opt-in: policies without it behave exactly as before."""
    path = home / "hook_timing.jsonl"
    _write(path, _timing_rows("narrow.sh", 20))

    policy = replace(lr.POLICIES[0], keep_lines=1_000)
    assert policy.keep_bytes is None
    result = lr.rotate_log(policy, home=home, min_bytes=0)

    assert result.lines_after == 40, "no byte bound means the line budget decides alone"
