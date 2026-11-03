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

_DIVINEOS_WORD = re.compile(r"(?<![\w-])divineos(?![\w-])", re.IGNORECASE)
_PYTEST_WORD = re.compile(r"(?<![\w-])pytest(?![\w-])", re.IGNORECASE)
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
    return bool(_DIVINEOS_WORD.search(flat) or _PYTEST_WORD.search(flat))


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
