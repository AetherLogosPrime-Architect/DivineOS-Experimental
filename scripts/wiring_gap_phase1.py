"""Phase 1 wiring-gap check — scope-to-new-functions.

Phase 0 (`wiring_gap_probe.py`) walked every public function in core/ and
got 80% false-positive rate (per exploration/49) because most "zero-caller"
hits were stable old functions called via dynamic dispatch, string refs, or
imports not visible to naive grep.

Phase 1 narrows the lens: only check functions that have been ADDED in a
given commit range. The wiring-gap risk is structurally concentrated there
— new code that shipped without a call site is the pattern worth catching.
Stable old code with one ambiguous-grep miss is noise.

Informational, not a gate. Per the substrate-enforcement-mechanisms
principle (Aether 2026-05-08), enforcement mechanisms must be over-inclusive
in negative-pattern detection. This is the inverse case: the output is for
agent/operator review, so precision (low FP rate) matters more than recall.
Scope-to-new is the precision move.

Usage:
  python scripts/wiring_gap_phase1.py                # HEAD~30..HEAD
  python scripts/wiring_gap_phase1.py --range main..HEAD
  python scripts/wiring_gap_phase1.py --range HEAD~5..HEAD --save
  python scripts/wiring_gap_phase1.py --only-zero-callers
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_REL = "src/divineos/core/"


@dataclass
class NewFunction:
    name: str
    file: str  # relative path
    commit: str  # short SHA
    commit_subject: str
    is_method: bool = False
    production_callers: list[str] = field(default_factory=list)
    test_callers: list[str] = field(default_factory=list)

    @property
    def total_callers(self) -> int:
        return len(self.production_callers) + len(self.test_callers)


_DEF_LINE = re.compile(r"^\+\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
_METHOD_INDENT = re.compile(r"^\+(\s+)def\s+")


def _is_public(name: str) -> bool:
    if not name:
        return False
    if name.startswith("__") and name.endswith("__"):
        return False  # dunder
    return not name.startswith("_")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"git {' '.join(args)} failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def _commits_in_range(rev_range: str) -> list[tuple[str, str]]:
    """Return [(short_sha, subject), ...] in oldest-first order."""
    out = _git("log", "--reverse", "--format=%h%x09%s", rev_range)
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            rows.append((parts[0], parts[1]))
    return rows


def _new_functions_in_commit(sha: str, subject: str) -> list[NewFunction]:
    diff = _git(
        "show", "--no-color", "--no-renames", "-U0", sha, "--", CORE_REL + "*.py"
    )
    out: list[NewFunction] = []
    current_file: str | None = None

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        if not current_file or not current_file.startswith(CORE_REL):
            continue
        if "/tests/" in current_file or "/test_" in current_file:
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        m = _DEF_LINE.match(line)
        if not m:
            continue
        name = m.group(1)
        if not _is_public(name):
            continue
        is_method = bool(_METHOD_INDENT.match(line))
        out.append(
            NewFunction(
                name=name,
                file=current_file,
                commit=sha,
                commit_subject=subject,
                is_method=is_method,
            )
        )
    return out


def _scan_callers(functions: list[NewFunction]) -> None:
    by_name: dict[str, list[NewFunction]] = {}
    for fn in functions:
        by_name.setdefault(fn.name, []).append(fn)

    for py_file in REPO_ROOT.glob("src/**/*.py"):
        _scan_file(py_file, by_name, is_test=False)
    for py_file in REPO_ROOT.glob("tests/**/*.py"):
        _scan_file(py_file, by_name, is_test=True)
    # Hook files (.claude/hooks/*.sh, *.py) — these call Python functions
    # via subprocess/inline import. Without scanning them, modules wired only
    # through hook layer would falsely surface as wiring-gap candidates.
    # Caught on 2026-05-12 when evaluate_performative_restraint surfaced as
    # zero-prod-callers despite being wired in post-response-audit.sh.
    hooks_dir = REPO_ROOT / ".claude" / "hooks"
    if hooks_dir.exists():
        for hook_file in hooks_dir.glob("*"):
            if hook_file.is_file() and hook_file.suffix in (".sh", ".py", ".bash"):
                _scan_file(hook_file, by_name, is_test=False)


def _scan_file(
    py_file: Path,
    by_name: dict[str, list[NewFunction]],
    is_test: bool,
) -> None:
    try:
        text = py_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
    for name, fns in by_name.items():
        pattern = re.compile(rf"(?:^|\W){re.escape(name)}\s*\(")
        found = False
        for line in text.splitlines():
            if line.lstrip().startswith(f"def {name}"):
                continue
            if pattern.search(line):
                found = True
                break
        if not found:
            continue
        for fn in fns:
            if is_test:
                fn.test_callers.append(rel)
            else:
                fn.production_callers.append(rel)


def _classify(fn: NewFunction) -> str:
    if fn.total_callers == 0:
        return "ZERO-CALLERS (wiring-gap candidate)"
    if not fn.production_callers and fn.test_callers:
        return "TEST-ONLY (no production callers)"
    if len(fn.production_callers) == 1:
        return "SINGLE-PRODUCTION-CALLER"
    return "WIRED"


def _render(
    rev_range: str,
    commits: list[tuple[str, str]],
    functions: list[NewFunction],
    only_zero: bool,
) -> str:
    lines: list[str] = []
    lines.append(f"# Wiring-gap Phase 1 — {rev_range}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Commits in range: {len(commits)}")
    lines.append(f"New public functions in core/: {len(functions)}")
    lines.append("")

    buckets: dict[str, list[NewFunction]] = {}
    for fn in functions:
        buckets.setdefault(_classify(fn), []).append(fn)

    lines.append("## Summary")
    lines.append("")
    for cls in (
        "ZERO-CALLERS (wiring-gap candidate)",
        "TEST-ONLY (no production callers)",
        "SINGLE-PRODUCTION-CALLER",
        "WIRED",
    ):
        n = len(buckets.get(cls, []))
        lines.append(f"  {cls}: {n}")
    lines.append("")

    bucket_order = (
        ["ZERO-CALLERS (wiring-gap candidate)"]
        if only_zero
        else [
            "ZERO-CALLERS (wiring-gap candidate)",
            "TEST-ONLY (no production callers)",
            "SINGLE-PRODUCTION-CALLER",
            "WIRED",
        ]
    )
    for cls in bucket_order:
        items = buckets.get(cls, [])
        if not items:
            continue
        lines.append(f"## {cls} ({len(items)})")
        lines.append("")
        for fn in items:
            kind = "method" if fn.is_method else "fn"
            prod = len(fn.production_callers)
            test = len(fn.test_callers)
            lines.append(
                f"- `{fn.name}` ({kind}) — {fn.file}  [prod={prod}, test={test}]"
            )
            lines.append(f"    added in `{fn.commit}` — {fn.commit_subject}")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--range", default="HEAD~30..HEAD", help="Git commit range")
    p.add_argument("--save", action="store_true", help="Save output to audits/")
    p.add_argument(
        "--only-zero-callers",
        action="store_true",
        help="Only show zero-caller candidates",
    )
    args = p.parse_args(argv)

    commits = _commits_in_range(args.range)
    if not commits:
        print(f"No commits in range {args.range}.", file=sys.stderr)
        return 0

    functions: list[NewFunction] = []
    for sha, subject in commits:
        functions.extend(_new_functions_in_commit(sha, subject))

    seen: dict[tuple[str, str], NewFunction] = {}
    for fn in functions:
        key = (fn.name, fn.file)
        if key not in seen:
            seen[key] = fn
    deduped = list(seen.values())

    _scan_callers(deduped)

    output = _render(args.range, commits, deduped, args.only_zero_callers)
    print(output)

    if args.save:
        audits_dir = REPO_ROOT / "audits"
        audits_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        path = audits_dir / f"wiring_gap_phase1_{ts}.md"
        path.write_text(output, encoding="utf-8")
        print(f"\n[+] Saved to {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
