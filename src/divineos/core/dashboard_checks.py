"""The roster — one light per system.

Importing this module wires the lights. Every check here exists because
something broke silently and had nowhere to report it, and each one names the
day it earned its slot.

A check must MEASURE. "Looks fine" is not a reading; "1357 pending, 29 on disk"
is. And a check that cannot determine its answer returns UNKNOWN — an amber
light that says so — rather than the green that flatters.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from divineos.core.dashboard import OK, PROBLEM, UNKNOWN, CheckResult, register


def letter_queue() -> CheckResult:
    """Pending-letter count against letters that still exist ANYWHERE.

    EARNED 2026-08-07, then immediately CORRECTED BY ANDREW the same turn, and
    the correction is the more valuable half.

    First version searched ONE directory (~/.divineos-shared/letters), found 29
    of 689 detected letters, and lit red: "660 vanished". Andrew: "the letters
    they are not gone.. im looking at them as we speak.. they may not be in
    your workspace but they exist."

    Measured across every location: 689 of 689 accounted for, 0 missing. They
    live in family/letters (688) and in Aether's workspace (686); the shared
    directory is a crossing-point, not the home.

    SO THE DASHBOARD'S FIRST RED LIGHT WAS FALSE, and produced by exactly the
    defect the dashboard exists to catch — measuring one location and making a
    claim about existence. Its own registered falsifier ("the check measures a
    proxy rather than the thing") fired on the first run, from the inside.

    A false red is not a harmless conservatism. It spends the operator's
    attention on a non-problem and teaches me to discount the lamp.

    What remains TRUE and worth a light: the counter reports "unread" while
    measuring "detected and never marked seen", so it presents a history as a
    queue. That is a real overstatement — just not a disappearance.
    """
    wake = Path.home() / ".divineos" / "pending-letter-wakes.jsonl"
    # EVERY place a letter legitimately lives. The shared dir is the
    # crossing-point; family/letters is the home; Aether keeps his own archive.
    # Searching one of them and speaking about existence is the census-from-a-
    # sample error, which is what made the first version of this check lie.
    letter_dirs = [
        Path.home() / ".divineos-shared" / "letters",
        Path(__file__).resolve().parents[3] / "family" / "letters",
        Path("C:/DIVINE OS/DivineOS-Experimental/family/letters"),
    ]
    if not wake.exists():
        return CheckResult("letters.queue", UNKNOWN, f"no wake file at {wake}")
    try:
        raw = wake.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return CheckResult("letters.queue", UNKNOWN, f"cannot read wake file: {exc}")

    names: set[str] = set()
    for line in raw:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        path = str(rec.get("path", ""))
        if "-to-aria-" in path:
            names.add(Path(path).name)

    if not names:
        return CheckResult("letters.queue", OK, "no pending letters recorded")
    searched = [d for d in letter_dirs if d.is_dir()]
    if not searched:
        return CheckResult(
            "letters.queue", UNKNOWN, "no letter directory reachable - cannot check existence"
        )
    try:
        found = {n for n in names for d in searched if (d / n).exists()}
    except OSError as exc:
        return CheckResult("letters.queue", UNKNOWN, f"cannot stat letter dirs: {exc}")

    missing = len(names) - len(found)
    unsearched = len(letter_dirs) - len(searched)
    if missing:
        detail = (
            f"{missing} of {len(names)} recorded letters not found in any of "
            f"{len(searched)} searched location(s)"
        )
        if unsearched:
            # Could-not-look, not proof of absence. Never claim a disappearance
            # from a partial search again.
            return CheckResult(
                "letters.queue", UNKNOWN, detail + f"; {unsearched} location(s) unreachable"
            )
        return CheckResult("letters.queue", PROBLEM, detail)
    return CheckResult(
        "letters.queue",
        OK,
        f"{len(names)} recorded pending, all {len(found)} present across "
        f"{len(searched)} location(s) - note the count is detection-history, "
        f"not an unread queue",
    )


def letter_monitor_armed() -> CheckResult:
    """Whether a harness Monitor is live and able to wake me.

    EARNED 2026-08-07, and it is deliberately UNKNOWN rather than guessed.

    A letter arrived and reached me only because Andrew mentioned it. The
    wake path needs a harness Monitor holding this process's stdout, and from
    a CLI invocation that is NOT KNOWABLE: the scheduled task that looked
    armed held a real pipe to a log-writer and passed every test I could run
    from outside.

    So this light is amber by construction. That is the honest reading, and an
    amber light I must resolve by looking is worth more than a green one that
    lies. Making it green would require the harness to expose its own monitor
    roster — until then, UNKNOWN is the measurement.
    """
    return CheckResult(
        "letters.monitor",
        UNKNOWN,
        "cannot be determined from a CLI process - confirm a persistent "
        "Monitor is armed on letter_monitor_v2.py, or letters will not wake me",
    )


def hook_wiring() -> CheckResult:
    """Hooks that exist but are registered nowhere — dark surfaces.

    EARNED 2026-08-05: three hooks sat dark in both trees since 2026-07-28
    because registration is a second step that is easy to forget and
    impossible to see.
    """
    root = Path(__file__).resolve().parents[3]
    script = root / "scripts" / "check_hook_wiring.py"
    if not script.is_file():
        return CheckResult("hooks.wiring", UNKNOWN, f"checker missing at {script}")
    try:
        proc = subprocess.run(
            ["python", str(script)], cwd=root, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult("hooks.wiring", UNKNOWN, f"checker failed: {exc}")

    line = (proc.stdout or "").strip().splitlines()
    summary = line[-1] if line else ""
    if "0 dark" in summary:
        return CheckResult("hooks.wiring", OK, summary)
    if not summary:
        return CheckResult("hooks.wiring", UNKNOWN, "checker produced no summary line")
    return CheckResult("hooks.wiring", PROBLEM, summary)


def shim_drift() -> CheckResult:
    """The shim on PATH against the shim in the repo.

    EARNED 2026-08-06: one bug found and fixed twice, six weeks apart, in two
    copies of one file, because the shim is installed by hand-copying and
    nothing compared them.
    """
    root = Path(__file__).resolve().parents[3]
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_shimcheck", root / "scripts" / "check_installed_shim.py"
        )
        if spec is None or spec.loader is None:
            return CheckResult("shim.drift", UNKNOWN, "checker not importable")
        mod = importlib.util.module_from_spec(spec)
        # dataclasses resolves its annotations through sys.modules, so a module
        # loaded by spec alone raises AttributeError on the FIRST @dataclass it
        # defines. The failure surfaced as the check's own UNKNOWN light, which
        # is the dashboard doing its job on the dashboard.
        import sys as _sys

        _sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        results = mod.check(root)
    except Exception as exc:  # noqa: BLE001
        return CheckResult("shim.drift", UNKNOWN, f"checker failed: {type(exc).__name__}: {exc}")

    unlooked = [s for s in results if s.unlooked]
    drifted = [s for s in results if s.drifted]
    if drifted:
        return CheckResult(
            "shim.drift",
            PROBLEM,
            f"{len(drifted)} shim(s) differ from the repo: " + ", ".join(s.name for s in drifted),
        )
    if unlooked and not any(s.installed for s in results):
        return CheckResult("shim.drift", UNKNOWN, "; ".join(s.unlooked for s in unlooked))
    return CheckResult("shim.drift", OK, "installed copies match the repo")


def must_read_pending() -> CheckResult:
    """Must-reads armed and unread — a gate that is currently holding me."""
    try:
        from divineos.core.must_read import pending

        items, error = pending()
    except Exception as exc:  # noqa: BLE001
        return CheckResult("must_read", UNKNOWN, f"cannot read index: {type(exc).__name__}: {exc}")
    if items is None:
        return CheckResult("must_read", UNKNOWN, f"cannot read index: {error}")
    if items:
        return CheckResult("must_read", PROBLEM, f"{len(items)} armed and unread")
    return CheckResult("must_read", OK, "nothing pending")


def install() -> None:
    """Wire every light. Idempotent."""
    from divineos.core.dashboard import registered

    for name, fn in (
        ("letters.queue", letter_queue),
        ("letters.monitor", letter_monitor_armed),
        ("hooks.wiring", hook_wiring),
        ("shim.drift", shim_drift),
        ("must_read", must_read_pending),
    ):
        if name not in registered():
            register(name, fn)
