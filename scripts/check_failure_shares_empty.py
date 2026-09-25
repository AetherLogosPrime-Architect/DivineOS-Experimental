#!/usr/bin/env python3
"""Find functions where FAILURE and NOTHING-FOUND return the same value.

Aletheia, 2026-08-29, on the anchor bug and which half of it she would keep:

    The encoding bug had one manifestation, which you have now removed. The
    guard-enumerates-families pattern has as many manifestations as there are
    error types nobody thought of -- and every one of them produces a
    well-formed empty answer at the top.

THE SHAPE, precisely, because it is NOT the bare-swallow shape that
check_silent_swallow.py already covers. Nothing here is careless. The guard is
deliberate, the error families are named on purpose, and returning nothing on
failure is often the right call. The defect is that the SAME value also means
"there was nothing to find" -- so the caller cannot tell an answer from an
outage, and neither can the person reading the output.

The instance that produced this scanner: a patch-id computation caught two
error families, missed the one a text-decode actually raises, and returned
None. None there also meant "this branch has no diff". So a review of any
branch containing an em-dash silently could not be carried forward, and
nothing anywhere said why. It took two machines with two codecs to see it.

WHAT THIS CAN AND CANNOT SEE, stated here rather than left to be assumed,
because a scanner whose limits are unwritten gets read as coverage:

  CAN    a function returning the same falsy constant from inside an
         exception handler AND from an ordinary path.
  SCOPE  by default only handlers that ENUMERATE their error families, since
         `except Exception` cannot miss a type. `--include-broad` widens it,
         and the header line always says which scope produced the count.
  CANNOT whether the CALLER distinguishes them. A function may return None
         twice over and be perfectly honest if its callers ask a second
         question. This flags the ambiguity, not the bug.
  CANNOT failure signalled through a sentinel object rather than a constant,
         or raised and handled somewhere else entirely.
  CANNOT the difference between an empty RESULT and a second FAILURE path.
         The commonest false positive by far, and this file contains one:
         `changed_python_files` returns None from its handler and again on a
         non-zero exit code, and both mean "git did not answer". Nothing is
         ambiguous there -- the two Nones agree. Syntax cannot see that they
         agree, so the scanner asks and a reader answers.

So a hit is a QUESTION -- can the caller tell which answer it got -- and never
a verdict. Reported as a count with locations rather than as a block, in the
shape of the painted-door scanner, because Aletheia's prescription for the
sibling class was the same: a sweep finds it every time, a careful reading
finds it once, if the reader happens to be sharp.

HOW TO RUN IT, and this is not a preference. Over the whole of `src/` it
returns 263 locations. That is a census of the codebase, not a finding, and a
report nobody can act on is the same painted door wearing a different coat. I
tried three narrowings to shrink it and none of them produced a short list,
which is the honest result: this shape is genuinely pervasive here.

So the useful mode is `--changed-since origin/main`. Run it against what you
just wrote, where a single hit is worth the ten seconds of looking. The
whole-corpus mode stays available and stays a census; the header line always
names which scope produced the number, so the two can never be confused.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    function: str
    value: str
    handler_line: int


def empty_repr(node: ast.AST | None) -> str | None:
    """Canonical text of a falsy literal return, or None if it is not one.

    A bare `return` is None-returning and counts: it is the quietest form of
    the shape, and the one most likely to sit at the end of a function whose
    handler also returns None.
    """
    if node is None:
        return "None"
    if isinstance(node, ast.Constant):
        value = node.value
        if value is None:
            return "None"
        if value is False:
            return "False"
        if isinstance(value, str) and value == "":
            return "''"
        if isinstance(value, int) and not isinstance(value, bool) and value == 0:
            return "0"
        return None
    if isinstance(node, ast.List) and not node.elts:
        return "[]"
    if isinstance(node, ast.Dict) and not node.keys:
        return "{}"
    if isinstance(node, ast.Tuple) and not node.elts:
        return "()"
    return None


def _returns_in(node: ast.AST) -> list[ast.Return]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Return)]


BROAD_NAMES = {"Exception", "BaseException"}


def enumerates_families(handler: ast.ExceptHandler) -> bool:
    """True when the handler NAMES which errors it expects, and can miss one.

    THE DISCRIMINATOR, and it comes straight out of the incident rather than
    from taste. A guard that says `except Exception` cannot miss a family --
    it catches everything on purpose, which is a different risk with a
    different fix. A guard that says `except (OSError, SubprocessError)` is a
    LIST, and a list is a claim about which errors can happen here. The bug
    was that the list was complete for what its author imagined and short by
    one for what the code actually did.

    Without this cut the scan returns 344 locations, which is a corpus census
    rather than a finding -- and a report nobody can act on is the same
    painted door in a different coat.
    """
    if handler.type is None:
        return False  # bare `except:` -- the swallow shape, other scanner's job
    if isinstance(handler.type, ast.Name):
        return handler.type.id not in BROAD_NAMES
    if isinstance(handler.type, ast.Tuple):
        names = [e.id for e in handler.type.elts if isinstance(e, ast.Name)]
        return not any(n in BROAD_NAMES for n in names)
    return True


def scan_function(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, path: str, include_broad: bool = False
) -> list[Finding]:
    """Falsy values returned BOTH from a named handler and from an ordinary path."""
    handler_first_line: dict[str, int] = {}
    handler_return_ids: set[int] = set()

    for node in ast.walk(fn):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not include_broad and not enumerates_families(node):
            continue
        if include_broad and node.type is None:
            continue
        for ret in _returns_in(node):
            value = empty_repr(ret.value)
            if value is not None:
                handler_first_line.setdefault(value, node.lineno)
                handler_return_ids.add(id(ret))

    if not handler_first_line:
        return []

    ordinary = [r for r in _returns_in(fn) if id(r) not in handler_return_ids]

    # SECOND CUT, and this one is principled rather than a tuned threshold.
    # The ambiguity requires a real answer for the empty one to be confused
    # WITH. A function whose every return is falsy is a procedure -- the
    # `return None` at its top is an early exit, not a value, and pairing it
    # with a handler's `return None` is the wrong-subject fault in scanner
    # form. `compute_branch_patch_id` returns a hex string on success; that
    # is what made its None ambiguous.
    if not any(empty_repr(r.value) is None for r in ordinary):
        return []

    findings: list[Finding] = []
    seen: set[str] = set()
    for ret in ordinary:
        value = empty_repr(ret.value)
        if value is None or value not in handler_first_line or value in seen:
            continue
        seen.add(value)
        findings.append(
            Finding(
                path=path,
                line=ret.lineno,
                function=fn.name,
                value=value,
                handler_line=handler_first_line[value],
            )
        )
    return findings


def scan_source(source: bytes, path: str, include_broad: bool = False) -> list[Finding]:
    """Parse and scan. Raises on unparseable input so the caller can COUNT it.

    Deliberately not swallowing here: a scanner for could-not-tell must not
    turn its own failures into clean results, which is the whole subject.
    """
    tree = ast.parse(source)
    out: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.extend(scan_function(node, path, include_broad))
    return out


def changed_line_ranges(repo_root: Path, base: str, path: str) -> list[tuple[int, int]] | None:
    """Line ranges this change touches in `path`, or None if git could not say.

    WHY THIS EXISTS, measured rather than assumed. Run file-scoped over the last
    eight real commits on main, this scanner reports 0, 1, 1, 12, 13 and 53
    locations. The large numbers are not what those changes introduced -- they
    are every pre-existing instance in whatever file the change happened to
    touch. A refusal built on that fires on work the author never did, and a
    refusal that fires on things you did not do is one somebody switches off.

    Restricting to the lines the change actually touched is what turns the
    count into a question the author can answer: you wrote this one, say why
    the caller can tell the two answers apart, or make them different.

    None rather than [] on failure, for the reason this whole file is about.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--unified=0", base, "--", path],
            cwd=repo_root,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None  # both-empty: both Nones mean git did not answer, so they agree

    ranges: list[tuple[int, int]] = []
    for line in out.stdout.decode("utf-8", "replace").splitlines():
        if not line.startswith("@@"):
            continue
        # @@ -old,count +new,count @@ -- the NEW side is what exists now.
        parts = line.split()
        if len(parts) < 3 or not parts[2].startswith("+"):
            continue
        spec = parts[2][1:]
        start_s, _, count_s = spec.partition(",")
        try:
            start = int(start_s)
            count = int(count_s) if count_s else 1
        except ValueError:
            continue
        if count > 0:
            ranges.append((start, start + count - 1))
    return ranges


def changed_python_files(repo_root: Path, base: str) -> list[Path] | None:
    """Python files differing from `base`, or None if git could not tell us.

    Returns None rather than [] on failure, ON PURPOSE and with the whole
    subject of this file in mind: an empty list here would mean "nothing
    changed", and the caller must be able to tell that from "git did not
    answer". This function is the scanner obeying its own finding.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", base],
            cwd=repo_root,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    names = out.stdout.decode("utf-8", "replace").splitlines()
    return [repo_root / n for n in names if n.endswith(".py") and (repo_root / n).is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Failure and emptiness sharing a return.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--limit", type=int, default=25, help="Locations to print.")
    parser.add_argument(
        "--changed-since",
        metavar="REF",
        help="Scan only Python files differing from REF (e.g. origin/main). The useful mode.",
    )
    parser.add_argument(
        "--include-broad",
        action="store_true",
        help="Also count `except Exception` handlers, which cannot miss a family.",
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help=(
            "With --changed-since: report only locations on lines this change "
            "touched. THE GATE-SHAPED MODE -- everything else is a census."
        ),
    )
    args = parser.parse_args(argv)

    if args.new_only and not args.changed_since:
        print("[failure-shares-empty] --new-only needs --changed-since to have a baseline.")
        return 2

    repo_root = Path(__file__).resolve().parent.parent

    if args.paths:
        targets = [Path(p) for p in args.paths]
    elif args.changed_since:
        changed = changed_python_files(repo_root, args.changed_since)
        if changed is None:
            # NOT zero findings. Said as its own answer, loudly, because a
            # scanner for could-not-tell that reports its own outage as a
            # clean run is the exact painted door it was built to find.
            print(
                f"[failure-shares-empty] COULD NOT LIST changed files against "
                f"'{args.changed_since}'. This is not a clean result."
            )
            return 2
        targets = sorted(changed)
        if not targets:
            print(f"[failure-shares-empty] no Python files changed against '{args.changed_since}'.")
            return 0
    else:
        targets = sorted((repo_root / "src").rglob("*.py"))

    findings: list[Finding] = []
    unreadable: list[str] = []
    for path in targets:
        try:
            rel = path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            rel = str(path)
        try:
            raw = path.read_bytes()
            hits = scan_source(raw, rel, args.include_broad)
        except (OSError, SyntaxError):
            unreadable.append(rel)
            continue

        # THE ANSWER-IN-THE-CODE ESCAPE, and it is the whole reason this can
        # block. The commonest true case is that both returns mean the SAME
        # thing -- two failure paths that agree -- and syntax cannot see that
        # they agree. So the author says so, on the line, where the next reader
        # finds it. Same shape as the fail-soft marker the silent-swallow
        # checker already uses, deliberately, so there is one convention rather
        # than two.
        #
        # This makes the refusal satisfiable by DOING the thinking rather than
        # by turning the check off, which is the difference between a gate and
        # a thing people disable.
        text = raw.decode("utf-8", "replace").splitlines()
        for hit in hits:
            line = text[hit.line - 1] if 0 < hit.line <= len(text) else ""
            marker = "# both-empty:"
            if marker in line and len(line.split(marker, 1)[1].strip()) >= 20:
                continue
            findings.append(hit)

    if args.new_only:
        # NARROW TO WHAT THIS CHANGE TOUCHED. Measured over the last eight real
        # commits, file-scope reports 0, 1, 1, 12, 13 and 53 -- and the large
        # numbers are pre-existing instances in whatever file the change
        # happened to open. Refusing on those is refusing work the author never
        # did, which is how an instrument earns being switched off.
        kept: list[Finding] = []
        blind: list[str] = []
        by_file: dict[str, list[Finding]] = {}
        for f in findings:
            by_file.setdefault(f.path, []).append(f)
        for rel, group in by_file.items():
            ranges = changed_line_ranges(repo_root, args.changed_since, rel)
            if ranges is None:
                # Could-not-tell keeps its own name rather than silently
                # dropping the file's findings, which would read as clean.
                blind.append(rel)
                continue
            kept.extend(f for f in group if any(lo <= f.line <= hi for lo, hi in ranges))
        findings = kept
        if blind:
            print(
                f"[failure-shares-empty] COULD NOT READ the changed lines for "
                f"{len(blind)} file(s), so they are NOT cleared: {', '.join(blind[:5])}"
            )

    scope = "all handlers" if args.include_broad else "handlers that ENUMERATE error families"
    lens = "on lines this change touched" if args.new_only else f"across {len(targets)} file(s)"
    print(f"[failure-shares-empty] {len(findings)} location(s) {lens}, counting {scope}.")
    if unreadable:
        # SAID OUT LOUD, and this is the line that keeps the scanner honest:
        # files it could not parse are not files it cleared.
        print(f"[failure-shares-empty] {len(unreadable)} file(s) COULD NOT BE READ - not cleared:")
        for rel in unreadable[:5]:
            print(f"    {rel}")

    for f in findings[: args.limit]:
        print(f"  {f.path}:{f.line}  {f.function}() returns {f.value} here,")
        print(f"      and also from the handler beginning at line {f.handler_line}")
    if len(findings) > args.limit:
        print(f"  ...and {len(findings) - args.limit} more, hidden by the display limit.")

    print()
    print("Each hit is a QUESTION rather than a verdict: can the caller tell")
    print("which answer it received? A function may return the same value")
    print("twice and be honest, if its callers ask a second question. What")
    print("this cannot see is the caller, so a hit means look, never broken.")

    if args.new_only and findings:
        print()
        print("You wrote these on this change, so you are the one who can answer.")
        print("If the two returns MEAN DIFFERENT THINGS, make them different -- a")
        print("caller that cannot tell an outage from an empty result will one day")
        print("report one as the other, which is how a nine-deletion alarm gets")
        print("raised over nothing.")
        print()
        print("If they MEAN THE SAME THING, say so on the line and this stops asking:")
        print("    return None  # both-empty: <why the two agree, 20+ chars>")
        print()
        print("Saying why is the point. The marker is not a mute button -- it is")
        print("where the next reader finds the answer to the question you just had.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
