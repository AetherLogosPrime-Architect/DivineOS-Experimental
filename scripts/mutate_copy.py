#!/usr/bin/env python3
"""Plant small deliberate faults in a module, on a disposable COPY, and see which tests notice.

Dad, 2026-10-20: a passing test proves nothing until a fault was forced and
the test caught it (Break, Fix, Break Again). `run_mutmut.py --quick` could
not do this for the ledger: it only knows comparisons against a bare number and
a line that is exactly `return True`/`return False`, and the ledger has neither
shape, so it would have printed "no mutation candidates", which reads exactly
like a pass. `--full` mutmut refuses to run on Windows. This is the replacement.

What it does differently, each on purpose:
  * It never touches the live tree. Source and tests are copied to a temporary
    folder and every fault is planted there.
  * It runs the tests UNTOUCHED first. If they are not green, every fault would
    look "caught", so it stops.
  * It proves the module imported in the copy is the copy's, not the live one.
  * It reads the code's structure (ast), so it finds comparisons against
    variables, `and`/`or`, conditions, return values, constants and +/-.
  * It records WHICH test caught each fault, which is what says which tests
    are solid.

What it does NOT do: judge. A fault that survives may be a weak test, an
equivalent change (the code behaves the same), or dead code. The readout is a
list to READ.

Usage:
    python scripts/mutate_copy.py src/divineos/core/ledger.py --tests tests/test_ledger.py
    python scripts/mutate_copy.py PATH --tests T1 T2 --limit 80 --seed 1 --out DIR
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_INCLUDE = ("pyproject.toml", "src", "tests", "scripts")
SKIP_MARK = "pragma: no mutate"

_CMP_TOKEN = {
    ast.Eq: ("==", r"==", ["!="]),
    ast.NotEq: ("!=", r"!=", ["=="]),
    ast.Lt: ("<", r"<", ["<=", ">"]),
    ast.LtE: ("<=", r"<=", ["<", ">"]),
    ast.Gt: (">", r">", [">=", "<"]),
    ast.GtE: (">=", r">=", [">", "<"]),
    ast.Is: ("is", r"\bis\b", ["is not"]),
    ast.IsNot: ("is not", r"\bis\s+not\b", ["is"]),
    ast.In: ("in", r"\bin\b", ["not in"]),
    ast.NotIn: ("not in", r"\bnot\s+in\b", ["in"]),
}


@dataclass(frozen=True)
class Mutant:
    start: int
    end: int
    replacement: str
    kind: str
    line: int
    original: str
    line_text: str


class MutateRefused(Exception):
    """The run cannot be trusted or is unsafe; stop and say why."""


def _line_starts(data: bytes) -> list[int]:
    starts = [0]
    for m in re.finditer(b"\n", data):
        starts.append(m.end())
    return starts


def _span(starts: list[int], node: ast.AST) -> tuple[int, int]:
    return (
        starts[node.lineno - 1] + node.col_offset,
        starts[node.end_lineno - 1] + node.end_col_offset,
    )


def find_mutants(source: bytes) -> list[Mutant]:
    """Every fault this tool knows how to plant, found from the code's structure."""
    tree = ast.parse(source.decode("utf-8"))
    starts = _line_starts(source)
    lines = source.decode("utf-8").splitlines()
    found: dict[tuple[int, int, str], Mutant] = {}

    def add(start: int, end: int, repl: str, kind: str, line: int) -> None:
        text = lines[line - 1] if 0 < line <= len(lines) else ""
        if SKIP_MARK in text:
            return
        original = source[start:end].decode("utf-8", errors="replace")
        found[(start, end, repl)] = Mutant(start, end, repl, kind, line, original, text.strip())

    def token_in(region: bytes, pattern: str) -> tuple[int, int] | None:
        hits = list(re.finditer(pattern.encode(), region))
        return (hits[0].start(), hits[0].end()) if len(hits) == 1 else None

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            prev = node.left
            for op, comp in zip(node.ops, node.comparators):
                spec = _CMP_TOKEN.get(type(op))
                if spec:
                    lo, hi = _span(starts, prev)[1], _span(starts, comp)[0]
                    hit = token_in(source[lo:hi], spec[1])
                    if hit:
                        for repl in spec[2]:
                            add(lo + hit[0], lo + hit[1], repl, "compare", node.lineno)
                prev = comp
        elif isinstance(node, ast.BoolOp):
            word, flip = (r"\band\b", "or") if isinstance(node.op, ast.And) else (r"\bor\b", "and")
            for left, right in zip(node.values, node.values[1:]):
                lo, hi = _span(starts, left)[1], _span(starts, right)[0]
                hit = token_in(source[lo:hi], word)
                if hit:
                    add(lo + hit[0], lo + hit[1], flip, "and-or", node.lineno)
        elif isinstance(node, ast.Constant):
            s, e = _span(starts, node)
            if node.value is True or node.value is False:
                add(s, e, str(not node.value), "bool", node.lineno)
            elif type(node.value) is int:
                add(s, e, str(node.value + 1), "number", node.lineno)
        elif isinstance(node, (ast.If, ast.While, ast.IfExp)):
            s, e = _span(starts, node.test)
            text = source[s:e].decode("utf-8")
            if not text.startswith("not "):
                add(s, e, f"not ({text})", "negate-condition", node.lineno)
        elif isinstance(node, ast.Return):
            v = node.value
            if v is not None and not (isinstance(v, ast.Constant) and v.value is None):
                s, e = _span(starts, v)
                add(s, e, "None", "return-none", node.lineno)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            lo, hi = _span(starts, node.left)[1], _span(starts, node.right)[0]
            region = source[lo:hi]
            sym, flip = (b"+", "-") if isinstance(node.op, ast.Add) else (b"-", "+")
            if region.strip(b" \t\r\n()\\") == sym and region.count(sym) == 1:
                at = lo + region.index(sym)
                add(at, at + 1, flip, "plus-minus", node.lineno)

    valid: list[Mutant] = []
    for m in found.values():
        mutated = source[: m.start] + m.replacement.encode() + source[m.end :]
        try:
            compile(mutated.decode("utf-8"), "<mutant>", "exec")
        except (SyntaxError, ValueError):
            continue
        valid.append(m)
    return sorted(valid, key=lambda m: (m.line, m.start, m.replacement))


def module_name_of(rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def make_copy(repo: Path, include: tuple[str, ...], dest: Path) -> None:
    resolved_repo, resolved_dest = repo.resolve(), dest.resolve()
    if resolved_dest == resolved_repo or resolved_repo in resolved_dest.parents:
        raise MutateRefused(f"the copy would sit inside the live tree ({dest})")
    for name in include:
        src = repo / name
        if not src.exists():
            raise MutateRefused(f"cannot copy {name}: it does not exist in {repo}")
        target = dest / name
        if src.is_dir():
            shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, target)


def _env(copy: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(copy / "src"), str(copy)])
    env["DIVINEOS_HOME"] = str(copy / ".home")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def prove_copy_is_imported(copy: Path, module: str) -> None:
    """The module under test must come from the copy, or every fault lands where nothing reads it."""
    code = "import importlib,sys;print(importlib.import_module(sys.argv[1]).__file__)"
    proc = subprocess.run(
        [sys.executable, "-c", code, module],
        cwd=copy,
        env=_env(copy),
        capture_output=True,
        text=True,
        timeout=120,
    )
    got = Path(proc.stdout.strip().splitlines()[-1]).resolve() if proc.stdout.strip() else None
    if proc.returncode != 0 or got is None or copy.resolve() not in got.parents:
        raise MutateRefused(
            f"{module} did not import from the copy (got {got}); "
            f"a fault planted in the copy would never be read. stderr: {proc.stderr[-300:]}"
        )


def run_tests(
    copy: Path, tests: list[str], timeout: float
) -> tuple[str, int | None, str | None, float]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-x",
        "-q",
        "--tb=no",
        "-p",
        "no:cacheprovider",
        "-rf",
        *tests,
    ]
    began = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=copy, env=_env(copy), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return "timeout", None, None, time.time() - began
    took = time.time() - began
    if proc.returncode == 0:
        return "survived", 0, None, took
    if proc.returncode == 1:
        m = re.search(r"^FAILED (\S+)", proc.stdout, re.MULTILINE)
        return "killed", 1, m.group(1) if m else None, took
    return "errored", proc.returncode, None, took


def run(
    repo: Path,
    module_rel: str,
    tests: list[str],
    *,
    include=DEFAULT_INCLUDE,
    limit: int | None = None,
    seed: int = 0,
    out: Path | None = None,
    keep: bool = False,
    lines: tuple[int, int] | None = None,
    progress=print,
) -> dict:
    module_path = Path(module_rel)
    live_file = repo / module_path
    if not live_file.is_file():
        raise MutateRefused(f"{module_rel} is not a file under {repo}")
    live_bytes = live_file.read_bytes()
    mutants = find_mutants(live_bytes)
    if not mutants:
        raise MutateRefused(
            f"no faults could be planted in {module_rel}. That is NOT a pass: "
            "the tool found nothing it knows how to break."
        )
    if lines is not None:
        mutants = [m for m in mutants if lines[0] <= m.line <= lines[1]]
        if not mutants:
            raise MutateRefused(
                f"no faults could be planted between lines {lines[0]} and {lines[1]}"
            )
    total_found = len(mutants)
    if limit is not None and limit < len(mutants):
        mutants = sorted(
            random.Random(seed).sample(mutants, limit), key=lambda m: (m.line, m.start)
        )

    work = Path(tempfile.mkdtemp(prefix="mutate-copy-"))
    out = out or Path(tempfile.gettempdir()) / "mutate-readouts"
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    jsonl = out / f"{module_path.stem}-{stamp}.jsonl"
    results: list[dict] = []
    try:
        make_copy(repo, include, work)
        copy_file = work / module_path
        prove_copy_is_imported(work, module_name_of(module_path))
        outcome, code, _, base_secs = run_tests(work, tests, timeout=1800)
        if outcome != "survived":
            raise MutateRefused(
                f"the tests are not green before any fault is planted ({outcome}, exit {code}); "
                "every fault would look caught. Fix that, or pass --include for files the tests need."
            )
        per_mutant_timeout = base_secs * 5 + 30
        progress(
            f"untouched tests green in {base_secs:.1f}s; {len(mutants)} of {total_found} faults to plant"
        )
        for n, m in enumerate(mutants, 1):
            # Every fault is written fresh from the untouched original, so nothing carries over.
            copy_file.write_bytes(
                live_bytes[: m.start] + m.replacement.encode() + live_bytes[m.end :]
            )
            outcome, code, killer, secs = run_tests(work, tests, per_mutant_timeout)
            row = {**asdict(m), "outcome": outcome, "killer": killer, "seconds": round(secs, 2)}
            results.append(row)
            with jsonl.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
            progress(
                f"[{n}/{len(mutants)}] {outcome:8} L{m.line} {m.kind}: {m.original!r} -> {m.replacement!r}"
            )
    finally:
        if keep:
            progress(f"copy kept at {work}")
        else:
            shutil.rmtree(work)
    if live_file.read_bytes() != live_bytes:
        raise MutateRefused("the live file changed during the run; this should be impossible")
    return {
        "module": module_rel,
        "found": total_found,
        "planted": len(mutants),
        "results": results,
        "readout": str(jsonl),
        "copy": str(work),
        "unrun_importers": test_files_that_import(repo, module_name_of(module_path), tests),
    }


def test_files_that_import(repo: Path, module: str, given: list[str]) -> list[str]:
    """Test files that use the module but were not run. A fault they would catch looks missed here.

    The first ledger readout called a search-order fault a gap; a test that pins it lived in a
    file whose name did not mention the ledger, so it was never handed over.
    """
    parent, _, leaf = module.rpartition(".")
    direct = re.compile(re.escape(module) + r"(?!\w)")
    from_parent = re.compile(rf"from {re.escape(parent)} import [^\n]*\b{re.escape(leaf)}\b")
    given_set = {Path(g).as_posix().split("::")[0] for g in given}
    found = []
    for path in sorted((repo / "tests").rglob("test_*.py")):
        rel = path.relative_to(repo).as_posix()
        if rel in given_set:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if direct.search(text) or from_parent.search(text):
            found.append(rel)
    return found


def summarize(report: dict) -> str:
    rows = report["results"]
    by = lambda o: [r for r in rows if r["outcome"] == o]  # noqa: E731
    killed, survived = by("killed"), by("survived")
    judged = len(killed) + len(survived)
    lines = [
        f"{report['module']}: {report['planted']} of {report['found']} possible faults planted",
        f"  caught {len(killed)}, missed {len(survived)}, timed out {len(by('timeout'))}, "
        f"errored {len(by('errored'))} (timeouts and errors are not counted as caught)",
    ]
    if judged:
        lines.append(f"  caught {len(killed) / judged:.0%} of the faults that gave a clear answer")
    if survived:
        lines.append("  MISSED (read each: weak test, same-behaviour change, or dead code):")
        lines += [
            f"    L{r['line']} {r['kind']}: {r['line_text'][:90]}   [{r['original']!r} -> {r['replacement']!r}]"
            for r in survived
        ]
    tally: dict[str, int] = {}
    for r in killed:
        tally[r["killer"] or "(unnamed)"] = tally.get(r["killer"] or "(unnamed)", 0) + 1
    if tally:
        lines.append("  Tests that were first to catch a fault:")
        lines += [f"    {c:3}  {t}" for t, c in sorted(tally.items(), key=lambda kv: -kv[1])[:15]]
    unrun = report.get("unrun_importers") or []
    if unrun:
        lines.append(
            f"  NOTE: {len(unrun)} other test file(s) use this module and were NOT run, so a 'missed' "
            f"above may be caught there. First few: {', '.join(unrun[:5])}"
        )
    lines.append(f"  full readout: {report['readout']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "module", help="repo-relative path of the file to fault, e.g. src/divineos/core/ledger.py"
    )
    ap.add_argument(
        "--tests", nargs="+", required=True, help="test files or ids that exercise the module"
    )
    ap.add_argument("--limit", type=int, help="plant only a random sample of this many faults")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--lines",
        help="plant only faults between these source lines, e.g. 1190-1220 "
        "(to re-break a spot after a fix)",
    )
    ap.add_argument("--out", type=Path)
    ap.add_argument("--include", nargs="*", default=[], help="extra repo paths the tests need")
    ap.add_argument("--keep", action="store_true", help="leave the copy in place to inspect")
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parent.parent
    span = tuple(int(n) for n in args.lines.split("-")) if args.lines else None
    try:
        report = run(
            repo,
            args.module,
            args.tests,
            include=DEFAULT_INCLUDE + tuple(args.include),
            limit=args.limit,
            seed=args.seed,
            out=args.out,
            keep=args.keep,
            lines=span,
        )
    except MutateRefused as e:
        print(f"REFUSED: {e}")
        return 2
    print()
    print(summarize(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
