"""Tell a crashed test worker from a failed test, and replay only what it held.

pytest-xdist marks the test a worker was running as FAILED when the worker dies
(``worker 'gw1' crashed while running '<node id>'``). The push gate read that as a
real failure and refused: 2026-10-05, 15,001 passed, one "failed", and that test
passed 8 of 8 alone. This reads the junit record, which carries the full node id
(the terminal line is cut short), and lets the push through only if EVERY failure
is such a crash victim and each one passes alone. Anything else blocks exactly as
before. Walk walk-3d234701aed3; draft
docs/drafts/a_dropped_worker_is_not_a_failed_test_draft_2026-10-05.md.

Usage: recover_crashed_workers.py JUNIT_XML REPO_DIR
Exit 0: only crashes, every victim passed alone -- the push may proceed.
Exit 1: anything else -- blocked, as today. A missing junit file blocks.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

# More than a few crash victims in one run is a fact about the machine, not
# noise to retry past (Kahneman, walk-3d234701aed3).
MAX_VICTIMS = 3
CRASH = re.compile(r"worker '(gw\d+)' crashed while running '([^']+)'")


def parse(junit: Path) -> tuple[list[str], list[str]]:
    """(real failures, crash-victim node ids) from a junit record."""
    real: list[str] = []
    victims: list[str] = []
    for case in ET.parse(junit).getroot().iter("testcase"):
        bad = case.find("failure")
        if bad is None:
            bad = case.find("error")
        if bad is None:
            continue
        text = f"{bad.get('message') or ''}\n{bad.text or ''}"
        found = CRASH.search(text)
        if found:
            victims.append(found.group(2))
        else:
            real.append(f"{case.get('classname')}::{case.get('name')}")
    return real, sorted(set(victims))


def rerun(victims: list[str], repo: Path) -> int:
    """Replay exactly these tests, alone and serially, against this tree's code."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    src = str(repo / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    cmd = [
        sys.executable, "-m", "pytest", *victims,
        "-q", "--tb=short", "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=",
    ]  # fmt: skip
    return subprocess.run(cmd, cwd=repo, env=env, timeout=900).returncode


def decide(
    junit: Path, repo: Path, rerun_fn: Callable[[list[str], Path], int] = rerun
) -> tuple[bool, str, list[str]]:
    """(allow, reason, victims). The verdict is one line of logic by design."""
    try:
        real, victims = parse(junit)
    except FileNotFoundError:
        return False, "no junit record, so a crash cannot be told from a failure", []
    except ET.ParseError as exc:
        return False, f"the junit record is unreadable ({exc})", []
    if real:
        return False, f"{len(real)} real failure(s), first {real[0]}: not a crash", victims
    if not victims:
        return False, "red, but no crashed worker is recorded: nothing here is a crash", victims
    if len(victims) > MAX_VICTIMS:
        return (
            False,
            (
                f"{len(victims)} crash victims is more than {MAX_VICTIMS}: "
                "a fact about the machine, not noise to retry past"
            ),
            victims,
        )
    if rerun_fn(victims, repo) != 0:
        return False, "a crash victim failed when run alone: " + ", ".join(victims), victims
    return (
        True,
        (
            f"worker crash only; {len(victims)} test(s) replayed alone and passed: "
            + ", ".join(victims)
        ),
        victims,
    )


def _free_gb() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().available / 2**30, 1)
    except Exception:  # noqa: BLE001 -- memory is a measurement for later, never a gate
        return None


def _record(allow: bool, reason: str, victims: list[str]) -> None:
    """One line per crash seen, so a rising rate is visible (Deming) and the cause
    can be measured later instead of believed (Feynman)."""
    home = Path(os.environ.get("DIVINEOS_HOME") or Path.home() / ".divineos")
    try:
        home.mkdir(parents=True, exist_ok=True)
        row = {"at": time.time(), "allowed": allow, "victims": victims, "free_gb": _free_gb()}
        with (home / "push_crash_recoveries.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass  # the verdict is already decided; a log that cannot be written is only a log


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: recover_crashed_workers.py JUNIT_XML REPO_DIR", file=sys.stderr)
        return 1
    allow, reason, victims = decide(Path(argv[1]), Path(argv[2]))
    head = "ALLOWED" if allow else "STILL BLOCKED"
    print(f"[push-readiness] crashed-worker check: {head} -- {reason}")
    if victims:
        _record(allow, reason, victims)
    return 0 if allow else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
