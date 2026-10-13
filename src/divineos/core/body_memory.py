"""Memory sense: the body feels memory held by no program, and remembers the climb.

WHY (2026-10-11). The push queue stalled on "needs 4.5 GB free" while ``divineos body``
said "36% used" the whole time. About 14 GB sat in kernel pool, owned by no program (the
integrated AMD driver opened a file on every process exit and never closed it; Aria traced
it with a pool trace). The body read total used and free through one call, so a leak that
belongs to nobody read as normal, and nothing kept yesterday's number to compare with.

This module adds the missing sense in its cheap half, which needs no admin:

* a reading: total, available, the sum of every program's working set, the **gap**
  (used minus programs: memory held by no program), and kernel pool totals;
* a history, one short line per reading, so a climb has a past;
* verdicts with Aria's controls built in. A reading near boot says "boot scan may inflate
  this" and never warns; a stale reading says stale, never fine; a pool-tag file from an
  admin helper warns on growth only when its idle window was clean.

Spec and every threshold: Aria's ``the_body_feels_the_hidden_memory_measurement_spec_2026-10-11``.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Aria's starting guesses, 2026-10-11, from one machine and one night. Her spec carries
# their falsifiers: if the body warns twice and the cause is a boot scan or a cache, the
# controls failed; if the gap stays under the floor for a week of real work, the floor is
# too tight. They are hypotheses with an owner, not laws.
GAP_WARN_GB = 3.0
NONPAGED_WARN_GB = 2.0
RISING_READINGS = 3
# Aria's cold read of 624 (2026-10-11): "rising across three readings" needs a span and a size,
# or three body runs a minute apart with a hundredth of wobble would trip it.
RISING_MIN_SPAN_SECONDS = 30 * 60
RISING_MIN_RISE_GB = 0.3
BOOT_QUIET_SECONDS = 15 * 60
STALE_SECONDS = 60 * 60
TAGS_STALE_SECONDS = 60 * 60
TAG_GROWTH_MIN = 500
MAX_KEPT_READINGS = 500

_GB = 1024**3
_DIVINEOS_HOME = Path.home() / ".divineos"
READINGS_PATH = _DIVINEOS_HOME / "body_memory_readings.jsonl"
TAGS_PATH = _DIVINEOS_HOME / "body_pool_tags.json"


@dataclass(frozen=True)
class Reading:
    ts: float
    boot_ts: float
    total_gb: float
    available_gb: float
    programs_gb: float
    gap_gb: float
    nonpaged_gb: float
    paged_gb: float
    # Programs whose memory could not be read (access denied). They make the gap look
    # larger, so the report says how many. Default keeps older history lines loadable.
    unreadable: int = 0


@dataclass(frozen=True)
class Note:
    level: str  # ok | warn | stale | note
    text: str


def _pool_totals_gb() -> tuple[float, float] | None:
    """Kernel nonpaged and paged pool in GB, from GetPerformanceInfo (no admin needed)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class _PerformanceInfo(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "CommitTotal",
                "CommitLimit",
                "CommitPeak",
                "PhysicalTotal",
                "PhysicalAvailable",
                "SystemCache",
                "KernelTotal",
                "KernelPaged",
                "KernelNonpaged",
                "PageSize",
                "HandleCount",
                "ProcessCount",
                "ThreadCount",
            )
        ]

    info = _PerformanceInfo()
    info.cb = ctypes.sizeof(info)
    if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
        return None
    page = info.PageSize
    return info.KernelNonpaged * page / _GB, info.KernelPaged * page / _GB


def take_reading(now: float | None = None) -> Reading | None:
    """One reading of memory now, or None when this system cannot be read."""
    try:
        import psutil  # type: ignore[import-untyped]
    except ImportError:
        return None
    pool = _pool_totals_gb()
    if pool is None:
        return None
    vm = psutil.virtual_memory()
    programs = 0
    unreadable = 0
    for proc in psutil.process_iter(["memory_info"]):
        info = proc.info.get("memory_info")
        if info is None:
            unreadable += 1
        else:
            programs += info.rss
    used = vm.total - vm.available
    return Reading(
        ts=time.time() if now is None else now,
        boot_ts=psutil.boot_time(),
        total_gb=vm.total / _GB,
        available_gb=vm.available / _GB,
        programs_gb=programs / _GB,
        gap_gb=(used - programs) / _GB,
        nonpaged_gb=pool[0],
        paged_gb=pool[1],
        unreadable=unreadable,
    )


def load_readings(path: Path | None = None, limit: int = MAX_KEPT_READINGS) -> list[Reading]:
    """The most recent readings, oldest first. A torn line is skipped, not fatal."""
    target = path or READINGS_PATH
    if not target.exists():
        return []
    readings: list[Reading] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        try:
            readings.append(Reading(**json.loads(line)))
        except (ValueError, TypeError):
            continue
    return readings[-limit:]


def append_reading(reading: Reading, path: Path | None = None) -> None:
    """Add one line; trim the file to the most recent MAX_KEPT_READINGS."""
    target = path or READINGS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(reading)) + "\n")
    lines = target.read_text(encoding="utf-8").splitlines()
    if len(lines) > MAX_KEPT_READINGS:
        target.write_text("\n".join(lines[-MAX_KEPT_READINGS:]) + "\n", encoding="utf-8")


def _assess_tags(tags: dict, now: float) -> list[Note]:
    age = now - float(tags.get("ts", 0))
    if age > TAGS_STALE_SECONDS:
        return [
            Note("stale", f"Pool tag counts are {age / 3600:.1f} hours old; no verdict from them.")
        ]
    grew = {
        name: count - tags.get("previous", {}).get(name, count)
        for name, count in tags.get("tags", {}).items()
    }
    grew = {name: by for name, by in grew.items() if by >= TAG_GROWTH_MIN}
    if not grew:
        return []
    names = ", ".join(f"{name} (+{by})" for name, by in sorted(grew.items()))
    if not tags.get("idle_clean"):
        return [
            Note(
                "note",
                f"Pool tag counts grew ({names}), but the idle window was not clean, "
                "so this is not a finding yet.",
            )
        ]
    return [Note("warn", f"Pool tag counts grew while the machine sat idle: {names}.")]


def assess(readings: list[Reading], now: float, tags: dict | None = None) -> list[Note]:
    """Verdicts on the history. Controls come first, so a control can never be skipped."""
    if not readings:
        return [Note("stale", "No memory readings yet; there is nothing to compare with.")]
    latest = readings[-1]
    if now - latest.ts > STALE_SECONDS:
        age = (now - latest.ts) / 3600
        return [Note("stale", f"The last memory reading is {age:.1f} hours old; no verdict.")]
    if latest.ts - latest.boot_ts < BOOT_QUIET_SECONDS:
        return [
            Note(
                "note",
                "This reading was taken soon after the machine started: "
                "boot scan may inflate this, so there is no verdict yet.",
            )
        ]
    notes: list[Note] = []
    series = [r for r in readings if r.boot_ts == latest.boot_ts][-RISING_READINGS:]
    gaps = [r.gap_gb for r in series]
    if (
        len(gaps) == RISING_READINGS
        and all(g > GAP_WARN_GB for g in gaps)
        and all(a < b for a, b in zip(gaps, gaps[1:]))
        and series[-1].ts - series[0].ts >= RISING_MIN_SPAN_SECONDS
        and gaps[-1] - gaps[0] >= RISING_MIN_RISE_GB
    ):
        trail = " -> ".join(f"{g:.1f}" for g in gaps)
        notes.append(
            Note(
                "warn",
                f"{gaps[-1]:.1f} GB of memory is held by no program and it has risen "
                f"across the last {RISING_READINGS} readings ({trail} GB). "
                "Something is borrowing memory and not giving it back.",
            )
        )
    if latest.nonpaged_gb > NONPAGED_WARN_GB:
        notes.append(
            Note(
                "warn",
                f"Memory the system keeps for drivers is {latest.nonpaged_gb:.1f} GB "
                "(a clean machine here sat near 0.8 GB). A driver may be keeping things open.",
            )
        )
    if tags is not None:
        notes.extend(_assess_tags(tags, now))
    if not any(n.level == "warn" for n in notes):
        notes.insert(
            0,
            Note(
                "ok",
                f"Memory held by no program is {latest.gap_gb:.1f} GB and driver memory is "
                f"{latest.nonpaged_gb:.1f} GB: nothing climbing.",
            ),
        )
    return notes


def _load_tags(path: Path | None) -> dict | None:
    target = path or TAGS_PATH
    if not target.exists():
        return None
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None


def memory_sense_report(path: Path | None = None, tags_path: Path | None = None) -> str:
    """Take a reading, remember it, and say what the history shows."""
    from divineos.core.system_load_check import pytest_parallel_flag

    lines = ["", "  MEMORY SENSE (what the plain memory number cannot show)"]
    reading = take_reading()
    if reading is None:
        lines.append("    unavailable: this system cannot give the kernel memory numbers.")
        return "\n".join(lines)
    append_reading(reading, path)
    lines.append(
        f"    Memory held by no program: {reading.gap_gb:.1f} GB "
        f"(programs {reading.programs_gb:.1f} GB of {reading.total_gb:.1f} GB)"
    )
    lines.append(
        f"    Driver memory (kernel pool): {reading.nonpaged_gb:.1f} GB held, "
        f"{reading.paged_gb:.1f} GB swappable"
    )
    if reading.unreadable:
        lines.append(
            f"    {reading.unreadable} programs could not be read, which makes the gap look larger."
        )
    lines.append(f"    The push gate says: {pytest_parallel_flag('the pre-push suite')[1]}")
    for note in assess(load_readings(path), reading.ts, _load_tags(tags_path)):
        lines.append(f"    [{note.level}] {note.text}")
    return "\n".join(lines)
