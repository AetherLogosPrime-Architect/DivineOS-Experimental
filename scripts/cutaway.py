#!/usr/bin/env python3
"""Cut the code away from under each test and see whether the test notices.

    python scripts/cutaway.py --staged --check          # the staged test files (commit time)
    python scripts/cutaway.py --files tests/test_x.py   # named files
    python scripts/cutaway.py --all --workers 4         # every test file (about half an hour)
    python scripts/cutaway.py --all --update-baseline   # record today's counts as the floor

WHAT IT ASKS. For each test: with the code it imports left alone, does it pass? With that
code swapped for a stub that crashes (only while the test body runs), does it still pass?
A test that passes both ways does not depend on the code it names. See cutaway_plugin.py for
how the cut is made and what it cannot see.

THE RATCHET. About a thousand tests in this repo read as cut off today, and many are honest
(a scan of repo files, a check that a name exists). Failing the commit for those would be
noise, so the counts per file are recorded in cutaway_baseline.json, and --check fails only
when a file's DISCONNECTED or SWALLOWED count RISES above its recorded floor, which a new weak
test always does. Same shape as the orphan and retired-rule baselines. The floor may fall
freely. Raising it needs --allow-rise "<why>", and the reason is stored beside the count.

THREE KINDS OF RESULT, KEPT APART. A verdict is one of: measured, out of process (the product
runs in a child process this cannot reach: not fake, not measured), or COULD NOT MEASURE (the
file collected nothing, or the baseline run was red). Could-not-measure exits 2: failing to
look is not a pass. DISCONNECTED means "a person should read this", never "fake".

Every child process passes the no-window flag. The first version of this tool did not, was
started from a console-less launcher, and put hundreds of console windows over Dad's screen
(2026-10-07).
"""

from __future__ import annotations

import argparse
import ast
import collections
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASELINE = HERE / "cutaway_baseline.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BAD = ("DISCONNECTED", "SWALLOWED")


@dataclass(frozen=True)
class Project:
    """Where the product lives, so the tool can be pointed at a tiny project in its own tests."""

    repo: Path
    src_paths: tuple[Path, ...]
    product_prefix: str
    extra_roots: tuple[str, ...] = ()
    cli_module: str = ""


DIVINEOS = Project(
    repo=REPO,
    src_paths=(REPO / "src",),
    product_prefix="divineos",
    extra_roots=("scripts", ".claude/hooks", "family"),
    cli_module="divineos.cli",
)


# ----------------------------------------------------------------------------- reading a test


def imported_names(test_file: Path, project: Project) -> list[str]:
    """Dotted names a test file imports from the product, for the plugin to cut.

    Resolution (a module, or a function re-exported by a package) happens inside the test's
    own process, where the product is importable; this only reads the syntax tree.
    """
    tree = ast.parse(test_file.read_text(encoding="utf-8", errors="replace"))
    found: set[str] = set()
    prefix = project.product_prefix
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top == prefix:
                found.add(node.module)
                found.update(f"{node.module}.{a.name}" for a in node.names)
            for root in project.extra_roots:
                folder = project.repo / root
                package = Path(root).name
                if node.module == package:
                    for a in node.names:
                        if (folder / f"{a.name}.py").exists():
                            found.add(f"{package}.{a.name}")
                            found.add(a.name)
                elif (folder / f"{top}.py").exists():
                    found.add(top)
                    found.add(f"{package}.{top}")
        elif isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                if top == prefix:
                    found.add(a.name)
                for root in project.extra_roots:
                    if (project.repo / root / f"{top}.py").exists():
                        found.add(top)
                        found.add(f"{Path(root).name}.{top}")
    return sorted(found)


# ----------------------------------------------------------------------------- running pytest


def run_pytest(test_file: Path, names: list[str], arm: bool, project: Project) -> dict:
    """One pytest process over one file, with the plugin loaded. 'error' if it did not report."""
    out_dir = Path(tempfile.mkdtemp(prefix="cutaway_"))
    base_tmp = (
        out_dir / "base"
    )  # its OWN scratch root: pytest deletes other runs' folders otherwise
    out = out_dir / "report.json"
    env = dict(os.environ)
    paths = [str(p) for p in project.src_paths] + [str(HERE)]
    if arm:
        paths += [str(project.repo / r) for r in project.extra_roots]
        env["CUTAWAY_ARM"] = "1"
    env.update(
        PYTHONPATH=os.pathsep.join(paths),
        CUTAWAY_NAMES=",".join(names),
        CUTAWAY_OUT=str(out),
        CUTAWAY_REPO=str(project.repo),
        CUTAWAY_PREFIX=project.product_prefix,
        CUTAWAY_CLI_MODULE=project.cli_module,
        CUTAWAY_EXTRA_ROOTS=",".join(project.extra_roots),
    )
    cmd = [
        sys.executable, "-m", "pytest", "-p", "cutaway_plugin", "-p", "no:cacheprovider",
        "-p", "no:randomly", "-q", "--tb=no", f"--basetemp={base_tmp}", str(test_file),
    ]  # fmt: skip
    report: dict = {"error": "never ran", "results": {}}
    try:
        # A child that dies before writing its report (seen once in 70 files under four
        # workers, 2026-10-08, and clean when rerun alone) is tried a second time; a second
        # silence is reported as it is.
        for _attempt in range(2):
            try:
                subprocess.run(
                    cmd, cwd=str(project.repo), env=env, capture_output=True, text=True,
                    timeout=900, creationflags=NO_WINDOW,
                )  # fmt: skip
                report = json.loads(out.read_text(encoding="utf-8"))
                break
            except subprocess.TimeoutExpired:
                report = {"error": "timeout", "results": {}}
                break
            except (OSError, ValueError) as exc:
                report = {"error": f"no report: {type(exc).__name__}", "results": {}}
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
    return report


# ----------------------------------------------------------------------------- the verdicts


def classify(base: dict, cut: dict) -> dict[str, str]:
    """A verdict per test. Pure: the unit tests drive it with hand-built reports."""
    verdicts: dict[str, str] = {}
    for nodeid, b in base.get("results", {}).items():
        if b["outcome"] in ("skipped", "setup-skipped"):
            # a test its own file chose not to run is unmeasured, not broken: 102 of the 131
            # "not green" in the first full sweep were skips (a library absent, a platform)
            verdicts[nodeid] = "SKIPPED"
            continue
        if b["outcome"] != "passed":
            verdicts[nodeid] = "BASELINE-NOT-GREEN"
            continue
        c = cut.get("results", {}).get(nodeid)
        if c is None:
            verdicts[nodeid] = "NOT-RUN-UNDER-CUT"
        elif c["outcome"].startswith("setup-"):
            verdicts[nodeid] = "FIXTURE-BROKE"
        elif c["outcome"] == "passed":
            verdicts[nodeid] = "SWALLOWED" if c["hits"] > 0 else "DISCONNECTED"
        else:
            verdicts[nodeid] = "CONNECTED" if c["hits"] > 0 else "OTHER-RED"
    return verdicts


def analyze_file(test_file: Path, project: Project = DIVINEOS) -> dict:
    """Run a test file untouched and cut; return counts and verdicts, or why it could not."""
    names = imported_names(test_file, project)
    base = run_pytest(test_file, [], False, project)
    if not base.get("results"):
        why = base.get("error", "collected no tests")
        return {"status": "could-not-measure", "why": why, "counts": {}, "verdicts": {}}
    cut = run_pytest(test_file, names, True, project)
    if not cut.get("results"):
        why = cut.get("error", "the cut run reported nothing")
        return {"status": "could-not-measure", "why": why, "counts": {}, "verdicts": {}}
    verdicts = classify(base, cut)
    text = test_file.read_text(encoding="utf-8", errors="replace")
    if "subprocess" in text or "bash" in text.lower():
        # the product runs in a child process this cannot reach: say so, do not call it fake
        verdicts = {
            k: ("OUT-OF-PROCESS?" if v == "DISCONNECTED" else v) for k, v in verdicts.items()
        }
    return {
        "status": "ok",
        "collected": len(base["results"]),
        "counts": dict(collections.Counter(verdicts.values())),
        "verdicts": verdicts,
        "cut_functions": cut.get("report", {}).get("functions", 0),
    }


# ----------------------------------------------------------------------------- the ratchet


def load_baseline(path: Path = BASELINE) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("files", {})


def ratchet(results: dict[str, dict], floor: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """(violations, could_not_measure). A file's bad counts may fall, never rise past the floor."""
    violations: list[dict] = []
    unmeasured: list[str] = []
    for rel, res in sorted(results.items()):
        if res["status"] != "ok":
            unmeasured.append(f"{rel}: {res.get('why', 'unknown')}")
            continue
        allowed = floor.get(rel, {})
        for verdict in BAD:
            now = res["counts"].get(verdict, 0)
            if now > allowed.get(verdict, 0):
                violations.append(
                    {
                        "file": rel,
                        "verdict": verdict,
                        "now": now,
                        "allowed": allowed.get(verdict, 0),
                    }
                )
    return violations, unmeasured


def updated_floor(
    results: dict[str, dict], floor: dict[str, dict], reason: str | None
) -> dict[str, dict]:
    """The floor after a sweep. A rise needs a stated reason, stored with the count."""
    new = {k: dict(v) for k, v in floor.items()}
    for rel, res in results.items():
        if res["status"] != "ok":
            continue
        entry = new.get(rel, {})
        rose = [v for v in BAD if res["counts"].get(v, 0) > entry.get(v, 0)]
        if rose and not reason:
            raise ValueError(
                f"{rel}: {', '.join(rose)} would rise above the recorded floor. "
                "Pass --allow-rise '<why>' to record it, or fix the test."
            )
        counts: dict = {v: res["counts"].get(v, 0) for v in BAD if res["counts"].get(v, 0)}
        if counts:
            reasons = list(entry.get("reasons", [])) + ([reason] if rose and reason else [])
            if reasons:
                counts["reasons"] = reasons
            new[rel] = counts
        else:
            new.pop(rel, None)  # a file with nothing bad left leaves the floor
    return new


# ----------------------------------------------------------------------------- selecting files


def all_test_files(project: Project = DIVINEOS) -> list[Path]:
    return sorted(
        p for p in (project.repo / "tests").rglob("test_*.py") if "_archive" not in p.parts
    )


def staged_test_files(project: Project = DIVINEOS) -> list[Path]:
    done = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=str(project.repo), capture_output=True, text=True, creationflags=NO_WINDOW,
    )  # fmt: skip
    names = [n for n in done.stdout.splitlines() if n.startswith("tests/") and n.endswith(".py")]
    return sorted(
        project.repo / n
        for n in names
        if Path(n).name.startswith("test_") and "_archive" not in Path(n).parts
    )


def sweep(files: list[Path], workers: int, project: Project = DIVINEOS) -> dict[str, dict]:
    def one(path: Path) -> tuple[str, dict]:
        return path.relative_to(project.repo).as_posix(), analyze_file(path, project)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = dict(pool.map(one, files))

    # Some files fight over a shared on-disk resource when run beside each other: their first
    # pass fails outright and leaves no report (four of 70 on 2026-10-08, every one clean when
    # run alone). A file that could not be measured in the crowd gets one run on its own before
    # it is reported as unmeasurable.
    if workers > 1:
        for path in files:
            rel = path.relative_to(project.repo).as_posix()
            if results[rel].get("status") == "could-not-measure" and "no report" in str(
                results[rel].get("why", "")
            ):
                results[rel] = analyze_file(path, project)
    return results


# ----------------------------------------------------------------------------- the command line


def _print_summary(results: dict[str, dict]) -> None:
    total: collections.Counter[str] = collections.Counter()
    for rel, res in sorted(results.items()):
        if res["status"] != "ok":
            print(f"  COULD NOT MEASURE  {rel}: {res.get('why')}")
            continue
        total.update(res["counts"])
        shown = {v: n for v, n in res["counts"].items() if v in BAD or v == "OUT-OF-PROCESS?"}
        if shown:
            print(f"  {rel}: {shown}")
    print(f"\n[cutaway] {len(results)} file(s). Totals: {dict(total)}")
    print(
        "[cutaway] DISCONNECTED = a person should read it (candidate, not fake); "
        "SWALLOWED = reached the cut code and stayed green; "
        "OUT-OF-PROCESS? = the product runs in a child process: not measured."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    pick = parser.add_mutually_exclusive_group(required=True)
    pick.add_argument("--files", nargs="+", help="test files to measure")
    pick.add_argument("--staged", action="store_true", help="the staged test files")
    pick.add_argument("--all", action="store_true", help="every test file")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if any file rises above its floor"
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument(
        "--allow-rise", metavar="WHY", help="record a rise above the floor, with the reason"
    )
    parser.add_argument("--json", metavar="PATH", help="write the full results here")
    args = parser.parse_args(argv)

    if args.files:
        named = [Path(f) if Path(f).is_absolute() else (REPO / f).resolve() for f in args.files]
        # the same archive rule as --staged and --all: archived tests are not run, so there is
        # nothing to cut away from under them (a push over 70 files died on one, 2026-10-08)
        files = [p for p in named if "_archive" not in p.parts]
        if len(files) != len(named):
            print(
                f"[cutaway] skipped {len(named) - len(files)} archived file(s): not run, not measured."
            )
    elif args.staged:
        files = staged_test_files()
    else:
        files = all_test_files()
    if not files:
        print("[cutaway] no test files selected: nothing measured.")
        return 0

    results = sweep(files, args.workers)
    _print_summary(results)
    if args.json:
        Path(args.json).write_text(json.dumps(results), encoding="utf-8")

    floor = load_baseline()
    if args.update_baseline:
        try:
            new = updated_floor(results, floor, args.allow_rise)
        except ValueError as exc:
            print(f"[cutaway] REFUSED to update the baseline: {exc}")
            return 1
        about = "Per-file floor of DISCONNECTED and SWALLOWED tests; see scripts/cutaway.py."
        BASELINE.write_text(
            json.dumps({"about": about, "files": new}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"[cutaway] baseline written: {len(new)} file(s) carry a floor.")
        return 0

    if args.check:
        violations, unmeasured = ratchet(results, floor)
        for v in violations:
            print(
                f"[cutaway] RISE: {v['file']} has {v['now']} {v['verdict']} test(s); "
                f"the floor is {v['allowed']}. Give the test a real dependence on the code it "
                "names, or say why it is honest with --update-baseline --allow-rise."
            )
        for line in unmeasured:
            print(f"[cutaway] COULD NOT MEASURE {line}")
        if violations:
            return 1
        if unmeasured:
            return 2  # failing to look is not a pass
        print("[cutaway] no file rose above its floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
