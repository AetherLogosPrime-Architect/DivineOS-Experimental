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
import ast
import re
from functools import lru_cache
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Windows default stdout is cp1252 which lacks many common chars (→, ⟶, etc).
# Without this, the script crashes with UnicodeEncodeError on `print(output)`
# when _render emits a Unicode arrow. utf-8 + replace is fail-loud-but-don't-
# crash: chars that can't be encoded become ?, but the report still prints.
# Caught dogfooding 2026-06-04 (Andrew + Grok audit follow-through pass).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


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


def _git(*args: str, allow_failure: bool = False) -> str:
    """Run git. Returns stdout, or empty string on failure when allow_failure=True.

    The CLI entry point uses allow_failure=False (exits on bad input);
    library callers (e.g. tests that pass a range that may not exist in a
    shallow clone) use allow_failure=True.
    """
    # Decode git output as UTF-8 explicitly with errors="replace". Without
    # this, text=True falls back to the locale encoding (cp1252 on Windows),
    # which crashes the subprocess reader thread on any non-cp1252 byte in a
    # diff — e.g. a commit that deletes source containing invisible/zero-width
    # glyphs (their bytes appear in the deletion side of `git show`). The crash
    # left stdout=None and produced an AttributeError downstream.
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        if allow_failure:
            return ""
        print(f"git {' '.join(args)} failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def _commits_in_range(rev_range: str) -> list[tuple[str, str]]:
    """Return [(short_sha, subject), ...] in oldest-first order.

    Returns empty list when the range is invalid (e.g. shallow clone without
    enough history). Callers can decide whether to error or skip.
    """
    # --no-merges. A merge commit AUTHORS no functions -- everything `git show`
    # reports for one was already written, and already scanned, on the side it
    # came from. Including merges is not merely wasteful; it is the documented
    # flake. This scan's footprint is bounded by "last N commits", and a merge
    # commit's diff is unbounded. Merging main into a branch that had drifted
    # produced one commit larger than the heuristic ever anticipated, and the
    # xdist worker died on it -- the exact crash the window was narrowed twice
    # to avoid (HEAD~30 -> HEAD~5 on 2026-07-03, HEAD~5 -> HEAD~3 on
    # 2026-07-10).
    #
    # Both narrowings treated commit COUNT as the knob. Count was never the
    # variable that mattered; per-commit footprint was, and it varies without
    # bound. Excluding merges removes the unbounded case instead of guessing a
    # smaller number a third time -- and costs no coverage, because a merge has
    # no new functions to find.
    #
    # --first-parent, added 2026-08-17, is the OTHER HALF of that fix and the
    # reason the flake above survived it. --no-merges drops merge COMMITS from
    # the output; it does nothing to the RANGE. `HEAD~3..HEAD` means everything
    # reachable from HEAD and not from HEAD~3, so the moment HEAD~3 sits on the
    # far side of a merge the range swallows every commit that arrived through
    # it. Measured on split/hook-firing-map immediately after merging main: the
    # "last three commits" resolved to TWENTY-ONE, carrying 88 new functions
    # into a scan that is O(functions x repo files). The same test finished in
    # 1.41s on a linear checkout and timed out here.
    #
    # So the previous fix removed the one oversized commit and left the range
    # free to substitute twenty smaller ones. Following first parents makes
    # "last N commits" mean N commits of THIS branch's own development, which
    # is what every narrowing in this comment was already trying to say.
    #
    # Not a new idea in this repo: scripts/ci_check_guardrail_trailer.sh has
    # used --first-parent since it was written, for the same reason in its own
    # words -- "skips commits absorbed via merge from an upstream remote".
    out = _git(
        "log",
        "--reverse",
        "--no-merges",
        "--first-parent",
        "--format=%h%x09%s",
        rev_range,
        allow_failure=True,
    )
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            rows.append((parts[0], parts[1]))
    return rows


def _new_functions_in_commit(sha: str, subject: str) -> list[NewFunction]:
    diff = _git("show", "--no-color", "--no-renames", "-U0", sha, "--", CORE_REL + "*.py")
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
    # scripts/ — CI integration shims, pre/post-commit checks, and other
    # production-effective Python that lives outside src/. Without this,
    # functions wired ONLY via scripts/ (e.g. core/merge_review_gate's
    # verify_merge called from scripts/ci_merge_review_check.py) falsely
    # surface as test-only. Caught 2026-06-04 (Grok audit follow-through).
    for py_file in REPO_ROOT.glob("scripts/**/*.py"):
        _scan_file(py_file, by_name, is_test=False)
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


@lru_cache(maxsize=None)
def _patterns_for(name: str) -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    """The three call-shape patterns for one name, compiled once.

    They used to be rebuilt inside the per-name loop, which runs once per
    file — so every pattern was recompiled several hundred times per run
    for no gain. Cached per name instead.
    """
    return (
        re.compile(rf"(?:^|\W){re.escape(name)}\s*\("),
        re.compile(rf"[(,]\s*{re.escape(name)}\s*[,)]"),
        re.compile(rf"^\s*{re.escape(name)}\s*,\s*$"),
    )
def _scope_note() -> list[str]:
    """What this scan cannot see, printed with every report.

    THE DECISION THIS ENCODES, and it was a real fork. Aria audited the scanner
    on 2026-08-25 and measured the reach: three call shapes recognised out of
    ten probed. Seven are invisible, and each of the seven makes a real caller
    disappear -- so the scan reports a wiring gap that is not one. Properties
    are the largest: 50 defined, 228 attribute accesses whose name matches one,
    and a property is read without parentheses so a scan looking for ``name(``
    cannot see it. (Her bound, kept: the parse confirms the attribute NAME, not
    that it resolves to that property. It is an upper bound.)

    The obvious fix is to also match a bare attribute access. That trades these
    false positives for FALSE NEGATIVES -- every attribute sharing a name with a
    function would read as a caller, and a gap that disappears is never argued
    with. Noise gets a conversation; silence gets nothing. This scanner exists
    to find silence, so it does not get to produce any.

    So the pattern stays narrow and the report says what it missed. Same
    discipline as a surface declaring could-not-run: the honest answer to "what
    about properties" is a sentence in the output, not a wider regex that
    quietly stops reporting real gaps.

    Aria's instinct and mine converged here, and she deferred the call to me on
    the grounds that I hold the design intent. Recording that she was right
    rather than that I decided.
    """
    return [
        "  Scope, so the silence is not read as coverage:",
        "    Recognises a direct call, a callable passed inline, and a callable",
        "    passed on its own line. It does NOT see a property read (no parens),",
        "    an attribute-style dispatch, or a name reached through a registry.",
        "    A zero-caller row for a PROPERTY is a limit of this scan, not a gap.",
        "    Widening it would trade these false positives for false negatives,",
        "    which is the failure this scan exists to catch. Measured 2026-08-25:",
        "    3 of 10 probed call shapes recognised; 50 properties defined.",
    ]


def _docstring_lines(text: str, suffix: str) -> set[int]:
    """Line numbers this Python source spends inside a DOCSTRING.

    Docstrings only -- not every string literal, and the narrowness is the
    whole design. ``scripts/check_silent_swallow.py`` carries a same-named
    helper that excludes ALL string literals, and the two are deliberately
    different rather than drifted: there, a swallow pattern appearing in any
    string is prose and the cost of over-excluding is a missed warning anyone
    can still see. Here, over-excluding would blind the scanner to a genuine
    call made through a string -- ``subprocess.run(["python", "-c",
    "render_block()"])`` is a real caller -- and this detector's failure
    direction is silence. So: docstrings, which are never call sites, and
    nothing else.

    Kept as a second copy rather than extracted. Two copies is inside the
    house rule (extract at three), and a shared helper across two files in
    scripts/ needs an import path -- the failure class that had
    tests/_archive/conftest.py shadowing the live conftest by name. Extract
    on the third caller, and make it a real module rather than a sibling
    import.

    Returns empty for non-Python and for anything that will not parse, so a
    broken file degrades to scanning every line. That is the noisy direction,
    chosen on purpose.
    """
    if suffix not in (".py", ".pyi"):
        return set()
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()

    covered: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                end = first.value.end_lineno or first.value.lineno
                covered.update(range(first.value.lineno, end + 1))
    return covered


def _scope_note() -> list[str]:
    """What this scan cannot see, printed with every report.

    THE DECISION THIS ENCODES, and it was a real fork. Aria audited the scanner
    on 2026-08-25 and measured the reach: three call shapes recognised out of
    ten probed. Seven are invisible, and each of the seven makes a real caller
    disappear -- so the scan reports a wiring gap that is not one. Properties
    are the largest: 50 defined, 228 attribute accesses whose name matches one,
    and a property is read without parentheses so a scan looking for ``name(``
    cannot see it. (Her bound, kept: the parse confirms the attribute NAME, not
    that it resolves to that property. It is an upper bound.)

    The obvious fix is to also match a bare attribute access. That trades these
    false positives for FALSE NEGATIVES -- every attribute sharing a name with a
    function would read as a caller, and a gap that disappears is never argued
    with. Noise gets a conversation; silence gets nothing. This scanner exists
    to find silence, so it does not get to produce any.

    So the pattern stays narrow and the report says what it missed. Same
    discipline as a surface declaring could-not-run: the honest answer to "what
    about properties" is a sentence in the output, not a wider regex that
    quietly stops reporting real gaps.

    Aria's instinct and mine converged here, and she deferred the call to me on
    the grounds that I hold the design intent. Recording that she was right
    rather than that I decided.
    """
    return [
        "  Scope, so the silence is not read as coverage:",
        "    Recognises a direct call, a callable passed inline, and a callable",
        "    passed on its own line. It does NOT see a property read (no parens),",
        "    an attribute-style dispatch, or a name reached through a registry.",
        "    A zero-caller row for a PROPERTY is a limit of this scan, not a gap.",
        "    Widening it would trade these false positives for false negatives,",
        "    which is the failure this scan exists to catch. Measured 2026-08-25:",
        "    3 of 10 probed call shapes recognised; 50 properties defined.",
    ]


def _docstring_lines(text: str, suffix: str) -> set[int]:
    """Line numbers this Python source spends inside a DOCSTRING.

    Docstrings only -- not every string literal, and the narrowness is the
    whole design. ``scripts/check_silent_swallow.py`` carries a same-named
    helper that excludes ALL string literals, and the two are deliberately
    different rather than drifted: there, a swallow pattern appearing in any
    string is prose and the cost of over-excluding is a missed warning anyone
    can still see. Here, over-excluding would blind the scanner to a genuine
    call made through a string -- ``subprocess.run(["python", "-c",
    "render_block()"])`` is a real caller -- and this detector's failure
    direction is silence. So: docstrings, which are never call sites, and
    nothing else.

    Kept as a second copy rather than extracted. Two copies is inside the
    house rule (extract at three), and a shared helper across two files in
    scripts/ needs an import path -- the failure class that had
    tests/_archive/conftest.py shadowing the live conftest by name. Extract
    on the third caller, and make it a real module rather than a sibling
    import.

    Returns empty for non-Python and for anything that will not parse, so a
    broken file degrades to scanning every line. That is the noisy direction,
    chosen on purpose.
    """
    if suffix not in (".py", ".pyi"):
        return set()
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()

    covered: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                end = first.value.end_lineno or first.value.lineno
                covered.update(range(first.value.lineno, end + 1))
    return covered


def _scan_file(
    py_file: Path,
    by_name: dict[str, list[NewFunction]],
    is_test: bool,
) -> None:
    try:
        text = py_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    # A function NAMED in prose is not a function CALLED. Before this, a
    # docstring reading "call render_block() when the briefing needs it"
    # registered as a production caller, and so did a `#` comment in a hook.
    # In a detector whose job is finding unwired code, that fails toward
    # SILENCE: the gap disappears instead of being argued with. Found
    # 2026-08-25 as the fifth instance of the mention-versus-use class in one
    # session, and the only one of the five whose failure direction was a
    # false negative.
    prose = _docstring_lines(text, py_file.suffix.lower())
    rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
    lines = text.splitlines()
    # A function NAMED in prose is not a function CALLED. Before this, a
    # docstring reading "call render_block() when the briefing needs it"
    # registered as a production caller, and so did a `#` comment in a hook.
    # In a detector whose job is finding unwired code, that fails toward
    # SILENCE: the gap disappears instead of being argued with. Found
    # 2026-08-25 as the fifth instance of the mention-versus-use class in one
    # session, and the only one of the five whose failure direction was a
    # false negative.
    prose = _docstring_lines(text, py_file.suffix.lower())
    for name, fns in by_name.items():
        # WHY THIS AND NOT ANOTHER WINDOW NARROWING. The test that exercises
        # this function records its scan window being cut twice for the same
        # symptom — HEAD~30 to HEAD~5 in July, then HEAD~5 to HEAD~3 a week
        # later — each time because the walk blew past its budget on a branch
        # whose commits happened to be large. The window was never the cost.
        # The cost is that this loop ran files x names x lines with three
        # regexes recompiled inside it, so it scaled with how much the repo
        # HOLDS rather than with how much changed. Narrowing the window
        # shrinks the input to a walk that stays quadratic; this shrinks the
        # walk.
        #
        # Aether wrote this paragraph and asked for it in the file rather than
        # only in a commit message, because each of those two narrowings left
        # a careful note explaining itself and each note made the NEXT
        # narrowing look reasonable. A reader meeting those notes alone would
        # conclude that shrinking the window is what you do when this gets
        # slow. This is what stops a fourth.
        #
        # All three call shapes below require the literal name, so its
        # absence from the file is a strict superset test: no pattern can
        # match text that does not contain the substring. This is what
        # takes the scan off its quadratic — the walk below ran over every
        # line of every file for every candidate name regardless of
        # whether the name appeared at all. Found by Aether 2026-08-26.
        if name not in text:
            continue
        # Three call shapes recognized as wiring:
        # (1) DIRECT call — function name followed by opening paren:
        #         func_name(arg)
        # (2) INDIRECT pass single-line — function name in callable-argument
        #     position on one line, preceded by `(`/`,` and followed by
        #     `,`/`)`:
        #         _run_detector("label", func_name, arg)
        # (3) INDIRECT pass multi-line — function name alone on its own line
        #     followed by `,` (the canonical formatter-shape for long
        #     argument lists):
        #         _run_detector(
        #             "label",
        #             func_name,
        #             arg,
        #         )
        #     Without (2)+(3), functions wired via a dispatch wrapper
        #     falsely surface as zero-callers. Caught 2026-06-04 when
        #     detect_engineer_drift_for_audit surfaced as orphan despite
        #     being passed to _run_detector at operating_loop_audit.py:445.
        direct_pattern, indirect_pattern, multiline_pattern = _patterns_for(name)
        found = False
        for line_no, line in enumerate(lines, start=1):
            if line_no in prose:
                continue
            stripped = line.lstrip()
            if stripped.startswith(f"def {name}"):
                continue
            # Pure comment lines, in both languages. Hooks are scanned too and
            # they have no docstrings, so the AST pass above cannot reach them
            # — a `#` line is the only prose form a .sh file has.
            if stripped.startswith("#"):
                continue
            # Skip import lines — they bind a name but aren't a call site.
            # The actual call site (if any) will be picked up elsewhere.
            if stripped.startswith(("import ", "from ")):
                continue
            # Pure comment lines, in both languages. Hooks are scanned too and
            # they have no docstrings, so the AST pass above cannot reach them
            # — a `#` line is the only prose form a .sh file has.
            if stripped.startswith("#"):
                continue
            if (
                direct_pattern.search(line)
                or indirect_pattern.search(line)
                or multiline_pattern.search(line)
            ):
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
    lines.extend(_scope_note())
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
            lines.append(f"- `{fn.name}` ({kind}) — {fn.file}  [prod={prod}, test={test}]")
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
