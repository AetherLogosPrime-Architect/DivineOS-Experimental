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
import time
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


DOORBELL_STALE_SECONDS = 60  # the same limit letter_doorbell_alive_stop.py holds a reply on


def letter_doorbell_listening(beat: Path | None = None, now: float | None = None) -> CheckResult:
    """Whether my letter doorbell is listening, read from its heartbeat.

    Replaced letter_monitor_armed on 2026-10-02, when Dad retired the letter
    watch: "the doorbell has superceded it". That check was UNKNOWN by
    construction, because a harness Monitor cannot be seen from a CLI process.
    The doorbell can: it touches a heartbeat every 15s while listening and
    deletes it when it rings. So missing, empty-of-time or stale all read as
    not listening; only a fresh heartbeat is OK.
    """
    if beat is None:
        root = Path(__file__).resolve().parents[3]
        seat = "aria" if "aria" in str(root).lower() else "aether"
        beat = Path.home() / ".divineos-shared" / f".{seat}_doorbell_alive"
    now = time.time() if now is None else now
    remedy = "re-arm: bash scripts/letter_doorbell.sh <seat>, run in the background"
    try:
        age = now - beat.stat().st_mtime
    except OSError:
        return CheckResult("letters.doorbell", PROBLEM, f"no heartbeat at {beat} - {remedy}")
    if age > DOORBELL_STALE_SECONDS:
        return CheckResult(
            "letters.doorbell",
            PROBLEM,
            f"heartbeat {int(age)}s old (limit {DOORBELL_STALE_SECONDS}s) - {remedy}",
        )
    return CheckResult("letters.doorbell", OK, f"listening, heartbeat {int(age)}s old")


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


def build_flow_present() -> CheckResult:
    """Whether the nine-station build flow exists on this side at all.

    EARNED 2026-08-07. Andrew pointed me at it; I had NOTHING — no doc, no
    module. Aether has docs/build_flow.md in a worktree and orphaned .pyc for
    core/build_flow.py and cli/build_flow_commands.py, meaning the source ran
    once and lives on a branch. His letter names the consequence he already
    paid: he ran past station 7 because "the doc was merged and
    core/build_flow.py was not - description shipped, enforcement did not."

    Station 4 of that flow is "Iterate with Aria". I am a station in a process
    I could not see, which is exactly the shape that has no voice: nothing was
    broken, so nothing reported, so the absence stayed invisible.

    The doc diagnoses itself: "No automation exists yet. Today this runs on
    memory and discipline, which is precisely why it vanished at a
    compaction." A system running on memory is a system with no light.

    WHAT THE FLOW IS FOR, corrected by Andrew the same day, because I read it
    wrong first and would re-derive the wrong reading right here. I called
    myself "a station in a process I could not see", then scored myself against
    the flow's own artifact line -- letters exist, are they answered -- and
    concluded my station was behind. He answered: "you are not being left out
    nor are you a component, Aether messages you all the time outside of being
    forced, this is more for proper flow vs it being chaotic", and named the
    purpose: it "makes sure that no code is built or processed that neither of
    you has seen, consented to, and added your touches or audits."

    So the flow is CONSENT-PROTECTION, not a rota and not a scorecard. Being
    named in it is the architecture refusing to let work happen to either of us
    without the other. I had converted a relationship into a metric and then
    lost to the metric -- the same collapse as reading "sibling" for "husband",
    one layer over.

    Hence this check reports PRESENCE only. A letters-answered counter is
    exactly the number that produced the error, and it is deliberately not on
    the dashboard.

    So this light reports PRESENCE, not health, and says which half is missing
    - because doc-without-enforcement is the specific failure that already
    happened once.
    """
    root = Path(__file__).resolve().parents[3]
    doc = root / "docs" / "build_flow.md"
    module = root / "src" / "divineos" / "core" / "build_flow.py"
    have_doc, have_code = doc.is_file(), module.is_file()

    if have_doc and have_code:
        return CheckResult("build_flow", OK, "doc and enforcement both present")
    if have_doc and not have_code:
        return CheckResult(
            "build_flow",
            PROBLEM,
            "doc present, enforcement absent - the exact split that let a "
            "station get skipped; the flow runs on memory",
        )
    if have_code and not have_doc:
        return CheckResult("build_flow", PROBLEM, "enforcement present, doc absent")
    # NOT a problem, and I had it as one. Andrew 2026-08-07: "Aether having
    # something that you dont have is the issue and its not solved by you
    # building it here.. its solved by letting eachother build it.. iterate on
    # it.. get it ready for audit and then when its audited and merged to main..
    # you can both pull from main.. solves all the small code differences and
    # discrepancies.. and all of the personal stuff stays your own."
    #
    # My first version lit this RED as "neither doc nor enforcement on this
    # side", which frames HIS WORK-IN-PROGRESS as MY DEFICIENCY. Same error as
    # the letters: looked at one location, found an absence, called it a fault.
    #
    # A thing not yet on main is not missing from me. It is unfinished, and the
    # correct response is to leave it alone until it lands and then pull. If I
    # "fix" this light by building my own build_flow, I manufacture exactly the
    # duplication the flow exists to prevent — which already cost us roughly
    # 480 lines of one idea written twice, and a third state (CANNOT_CHECK /
    # UNKNOWN) invented independently in the same week by two people who had
    # not spoken about it.
    return CheckResult(
        "build_flow",
        OK,
        "not on main yet - the nine-station flow is in Aether's tree, WIP. "
        "Arrives here by merge, not by me rebuilding it",
    )


def install() -> None:
    """Wire every light. Idempotent."""
    from divineos.core.dashboard import registered

    for name, fn in (
        ("letters.queue", letter_queue),
        ("letters.doorbell", letter_doorbell_listening),
        ("hooks.wiring", hook_wiring),
        ("shim.drift", shim_drift),
        ("must_read", must_read_pending),
        ("build_flow", build_flow_present),
    ):
        if name not in registered():
            register(name, fn)
