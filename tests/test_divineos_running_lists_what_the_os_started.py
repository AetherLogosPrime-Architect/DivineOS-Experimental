"""`divineos running`: what the OS started, and whether anyone still owns it.

The decision logic is pure and fed fixed rows here. The one live control proves
the reader can find a process that certainly exists (this test's own), because
an empty list from a blind reader looks exactly like an empty room.
"""

from __future__ import annotations

import os
import time
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


def test_a_word_in_the_arguments_does_not_make_a_process_ours():
    decoys = [
        _row(600, 1, 5, "grep -r divineos /etc"),
        _row(601, 1, 5, "/usr/bin/pip install pytest"),
        _row(602, 1, 5, "ssh host pytest"),
        _row(603, 1, 5, "/usr/bin/python3 -c print('divineos pytest')"),
        _row(604, 1, 5, "C:/Windows/System32/notepad.exe divineos.txt"),
    ]
    assert rp.select_ours(decoys, REPO) == []


def test_the_program_being_divineos_or_pytest_is_ours_in_each_launch_shape():
    real = [
        _row(700, 1, 5, "pytest tests/ -q"),
        _row(701, 1, 5, "/home/u/.venv/bin/divineos briefing"),
        _row(702, 1, 5, "C:/Program Files/Python313/python.exe -m pytest -q"),
        _row(703, 1, 5, "python -W ignore -m divineos.cli hud"),
        _row(704, 1, 5, "C:/Users/me/proj/.direnv/python-3.13.11/Scripts/divineos.exe running"),
    ]
    assert {r.pid for r in rp.select_ours(real, REPO)} == {700, 701, 702, 703, 704}


def test_a_trailing_path_named_divineos_or_pytest_does_not_make_a_process_ours():
    decoys = [
        _row(800, 1, 5, r"C:\Windows\explorer.exe C:\Users\me\divineos"),
        _row(801, 1, 5, "/usr/bin/cat /var/log/divineos"),
        _row(802, 1, 5, "/usr/bin/cp /src/pytest /dst/"),
        _row(803, 1, 5, "/usr/bin/vim /home/u/pytest"),
        _row(804, 1, 5, r"C:\Program Files\Microsoft VS Code\Code.exe c:\work\divineos"),
        _row(805, 1, 5, "python -c divineos"),
    ]
    assert rp.select_ours(decoys, REPO) == []


def test_xdist_workers_and_uv_or_poetry_runs_of_pytest_are_ours():
    real = [
        _row(900, 1, 5, 'python -c "import sys;from execnet import gateway_base;exec(1)"'),
        _row(901, 1, 5, "uv run pytest tests -q"),
        _row(902, 1, 5, "poetry run pytest -q"),
        _row(903, 1, 5, "C:/Program Files/uv/uv.exe run --frozen pytest"),
    ]
    assert {r.pid for r in rp.select_ours(real, REPO)} == {900, 901, 902, 903}


def test_the_command_lists_a_real_process_and_leaves_a_decoy_out(tmp_path):
    """A live control: both children are asserted alive before the command is read."""
    import subprocess
    import sys

    from divineos.cli import cli

    real = tmp_path / "divineos.py"
    decoy = tmp_path / "sleeper.py"
    for script in (real, decoy):
        script.write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
    procs = [
        subprocess.Popen([sys.executable, str(real)]),
        subprocess.Popen([sys.executable, str(decoy), "divineos"]),
    ]
    try:
        assert all(p.poll() is None for p in procs), "a control exited before it was read"
        # Wait until the table shows both, so a slow start is not read as absence.
        deadline = time.time() + 20
        pids = {r.pid for r in rp.read_live_rows()}
        while time.time() < deadline and not all(p.pid in pids for p in procs):
            time.sleep(0.2)
            pids = {r.pid for r in rp.read_live_rows()}
        result = CliRunner().invoke(cli, ["running"])
        assert result.exit_code == 0, result.output
        assert f"pid {procs[0].pid} " in result.output, result.output
        assert f"pid {procs[1].pid} " not in result.output, result.output
    finally:
        for p in procs:
            p.kill()
            p.wait()
