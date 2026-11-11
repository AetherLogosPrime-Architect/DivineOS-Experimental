"""What is running that this house started, and does anyone still own it?

A read-only roll call. It reads the live process table through psutil (already a
declared core dependency) and never signals, stops or writes anything. The
decision logic works on plain rows so it can be tested with fixed input; the one
live function only reads.

A process is "ours" when its command line names this repository's scripts
folder, the ``divineos`` command, or the test runner. An orphan is a process
whose named parent pid is no longer running. A parent of pid 1 is only a note
("reparented"): containers hand legitimate background jobs to init, so crying
orphan there would train the reader to ignore the word.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_NAMES = {"divineos", "pytest", "py.test"}
# A folder path may hold spaces and hyphens, but a space followed by a hyphen starts a flag,
# so the path ends there. A space followed by another absolute path (`/x` or `C:/x`) starts
# an argument, so the program path ends there too: `cat /var/log/divineos` is cat, not ours.
# A relative prefix may not hold spaces at all.
_PATH = r"(?:(?:[A-Za-z]:)?/(?:(?!\s-)(?!\s(?:[A-Za-z]:)?/).)*?/|\S*/)?"
_LAUNCHER = re.compile(
    "^"
    + _PATH
    + r"(?:uv|poetry)(?:\.exe)?\s+run\s+(?:-\S+\s+)*(?:divineos|pytest|py\.test)(?:\s|$)",
    re.IGNORECASE,
)
_DIRECT_EXE = re.compile(
    "^" + _PATH + r"(?:divineos|pytest|py\.test)(?:\.exe)?(?:\s|$)", re.IGNORECASE
)
_FIRST_SCRIPT = re.compile(
    "^" + _PATH + r"(?:divineos|pytest|py\.test)(?:\.(?:py|exe|cmd))?(?:\s|$)", re.IGNORECASE
)
_PYTHON_EXE = re.compile(
    "^" + _PATH + r"(?:python[\d.]*|pythonw|py)(?:\.exe)?(?:\s+(?P<rest>.*))?$", re.IGNORECASE
)
_RELATIVE_SCRIPT = re.compile(r"(?:^|\s)(?:\./)?scripts/\S+")
_ONE_LINE_LIMIT = 120


@dataclass(frozen=True)
class ProcessRow:
    pid: int
    ppid: int
    started_at: float
    cmdline: str


@dataclass(frozen=True)
class RunningEntry:
    pid: int
    ppid: int
    age_seconds: float
    command: str
    parent_alive: bool
    orphan: bool
    reparented: bool


def read_live_rows() -> list[ProcessRow]:
    """Every process the machine will show us. Processes that vanish mid-read are skipped."""
    import psutil

    rows: list[ProcessRow] = []
    for proc in psutil.process_iter(["pid", "ppid", "create_time", "cmdline"]):
        info = proc.info
        parts = info.get("cmdline") or []
        rows.append(
            ProcessRow(
                pid=info["pid"],
                ppid=info["ppid"] or 0,
                started_at=info["create_time"] or 0.0,
                cmdline=" ".join(parts),
            )
        )
    return rows


def _names_the_repo(cmdline: str, repo_root: Path) -> bool:
    flat = cmdline.replace("\\", "/")
    scripts_dir = (repo_root / "scripts").as_posix()
    if scripts_dir.lower() in flat.lower():
        return True
    if _RELATIVE_SCRIPT.search(flat):
        return True
    return _runs_divineos_or_pytest(flat)


def _runs_divineos_or_pytest(flat: str) -> bool:
    """True when the program being run IS divineos or pytest, not when a word mentions one.

    ``grep -r divineos /etc``, ``pip install pytest`` and ``ssh host pytest`` carry the
    word only as an argument, so they are not ours. Ours: the executable itself, or a
    python interpreter whose ``-m`` module or first script is one of them.
    """
    if _DIRECT_EXE.match(flat) or _LAUNCHER.match(flat):
        return True
    m = _PYTHON_EXE.match(flat)
    if not m:
        return False
    rest = (m.group("rest") or "").split()
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        if rest[i] == "-c":
            # The argument is code, not a script name. A pytest-xdist worker is the one such
            # command that is ours: it carries execnet's bootstrap.
            return "execnet" in " ".join(rest[i + 1 :]).lower()
        if rest[i] == "-m" and i + 1 < len(rest):
            return rest[i + 1].split(".")[0].lower() in _NAMES
        i += 2 if rest[i] in ("-W", "-X") else 1
    # The first script may sit in a folder with spaces in its name, so match the joined
    # remainder rather than one whitespace-split token.
    return bool(_FIRST_SCRIPT.match(" ".join(rest[i:])))


def select_ours(rows: list[ProcessRow], repo_root: Path) -> list[ProcessRow]:
    return [r for r in rows if _names_the_repo(r.cmdline, repo_root)]


def one_line(cmdline: str) -> str:
    flat = " ".join(cmdline.split())
    if len(flat) <= _ONE_LINE_LIMIT:
        return flat
    return flat[: _ONE_LINE_LIMIT - 3] + "..."


def describe(
    rows: list[ProcessRow], repo_root: Path, now: float, skip_pid: int | None = None
) -> list[RunningEntry]:
    live_pids = {r.pid for r in rows}
    entries: list[RunningEntry] = []
    for row in select_ours(rows, repo_root):
        if row.pid == skip_pid:
            continue
        parent_alive = row.ppid in live_pids
        entries.append(
            RunningEntry(
                pid=row.pid,
                ppid=row.ppid,
                age_seconds=now - row.started_at,
                command=one_line(row.cmdline),
                parent_alive=parent_alive,
                orphan=row.ppid > 1 and not parent_alive,
                reparented=row.ppid == 1,
            )
        )
    return sorted(entries, key=lambda e: e.age_seconds, reverse=True)


def format_age(seconds: float) -> str:
    total = int(seconds)
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def format_report(entries: list[RunningEntry]) -> str:
    if not entries:
        return "Running: nothing here that the OS started."
    lines = [f"Running: {len(entries)} process(es) the OS started (oldest first).", ""]
    for e in entries:
        flag = ""
        if e.orphan:
            flag = "  <-- ORPHAN: whoever started this is gone"
        elif e.reparented:
            flag = "  (reparented to init: its starter is gone or it was handed off)"
        lines.append(f"  pid {e.pid}  parent {e.ppid}  age {format_age(e.age_seconds)}{flag}")
        lines.append(f"      {e.command}")
    return "\n".join(lines)
