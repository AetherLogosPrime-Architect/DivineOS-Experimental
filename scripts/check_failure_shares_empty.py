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
    args = parser.parse_args(argv)

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
            findings.extend(scan_source(path.read_bytes(), rel, args.include_broad))
        except (OSError, SyntaxError):
            unreadable.append(rel)

    scope = "all handlers" if args.include_broad else "handlers that ENUMERATE error families"
    print(
        f"[failure-shares-empty] {len(findings)} location(s) across {len(targets)} file(s), "
        f"counting {scope}."
    )
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
