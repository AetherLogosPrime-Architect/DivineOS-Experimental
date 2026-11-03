"""`divineos running`: what the OS started, and whether anyone still owns it.

The decision logic is pure and fed fixed rows here. The one live control proves
the reader can find a process that certainly exists (this test's own), because
an empty list from a blind reader looks exactly like an empty room.
"""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from divineos.core import running_processes as rp

REPO = Path("/work/DivineOS-Experimental")
NOW = 10_000.0


def _row(pid: int, ppid: int, age_s: float, cmd: str) -> rp.ProcessRow:
    return rp.ProcessRow(pid=pid, ppid=ppid, started_at=NOW - age_s, cmdline=cmd)


FIXED = [
    _row(1, 0, 90000, "/sbin/init"),
    _row(100, 1, 5000, "bash /work/DivineOS-Experimental/scripts/letter_doorbell.sh aether"),
    _row(200, 100, 70, "python -m pytest tests/test_x.py -q"),
    _row(300, 9999, 4000, "/usr/bin/python3 /usr/local/bin/divineos briefing"),
    _row(400, 1, 30, "vim notes.txt"),
    _row(500, 1, 30, "tail -f /work/DivineOS-Experimental/README.md"),
]


def test_selection_keeps_scripts_divineos_and_pytest_and_drops_the_rest():
    picked = {r.pid for r in rp.select_ours(FIXED, REPO)}
    assert picked == {100, 200, 300}


def test_the_repo_folder_name_alone_does_not_make_a_process_ours():
    assert rp.select_ours([FIXED[5]], REPO) == []


def test_a_parent_that_is_gone_is_flagged_as_an_orphan():
    by_pid = {e.pid: e for e in rp.describe(FIXED, REPO, NOW)}
    assert by_pid[300].parent_alive is False
    assert by_pid[300].orphan is True
    assert by_pid[200].parent_alive is True
    assert by_pid[200].orphan is False


def test_a_child_of_init_is_a_soft_note_not_an_orphan():
    entry = {e.pid: e for e in rp.describe(FIXED, REPO, NOW)}[100]
    assert entry.parent_alive is True
    assert entry.orphan is False
    assert entry.reparented is True


def test_age_is_measured_from_the_start_time():
    by_pid = {e.pid: e for e in rp.describe(FIXED, REPO, NOW)}
    assert by_pid[200].age_seconds == 70
    assert rp.format_age(70) == "1m10s"
    assert rp.format_age(5000) == "1h23m"
    assert rp.format_age(90000) == "1d1h"
    assert rp.format_age(5) == "5s"


def test_the_report_names_each_process_and_flags_the_orphan():
    text = rp.format_report(rp.describe(FIXED, REPO, NOW))
    assert "300" in text and "ORPHAN" in text
    assert text.count("ORPHAN") == 1
    assert "vim" not in text


def test_the_report_says_so_when_nothing_is_running():
    assert "nothing" in rp.format_report([]).lower()


def test_a_long_command_is_cut_to_one_line():
    long_cmd = "python " + "x" * 400 + "\nsecond line"
    line = rp.one_line(long_cmd)
    assert "\n" not in line
    assert len(line) <= 120


def test_the_live_reader_finds_this_very_process_and_its_real_parent():
    rows = {r.pid: r for r in rp.read_live_rows()}
    assert os.getpid() in rows, "the reader cannot see itself: its list means nothing"
    assert rows[os.getpid()].ppid == os.getppid()
    assert rows[os.getpid()].cmdline


def test_the_module_has_no_way_to_kill_or_write():
    source = Path(rp.__file__).read_text(encoding="utf-8")
    for forbidden in (".kill(", ".terminate(", "os.kill", "open(", "write_text", "unlink"):
        assert forbidden not in source, forbidden


def test_the_command_runs_and_prints_a_header():
    from divineos.cli import cli

    result = CliRunner().invoke(cli, ["running"])
    assert result.exit_code == 0, result.output
    assert "running" in result.output.lower()
