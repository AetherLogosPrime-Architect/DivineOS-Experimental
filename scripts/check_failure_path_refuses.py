#!/usr/bin/env python3
"""Find every place where a crash makes a function refuse what it would allow.

WHY THIS EXISTS, AND WHOSE IDEA IT WAS.

On 2026-09-02 I found the quality gate discarding a whole session's learning
when its own checks raised: a defect in the JUDGE destroying the subject being
judged. I fixed it, surveyed the tree for siblings by hand, and told Aletheia I
had found exactly one instance of the destroying form.

She refused to confirm it, and she was right to:

    "I tried, and my instrument is not fit for it. Grepping for `discard`
    across src/ returns dozens of files, almost all of them using the word for
    unrelated things. A count from that is a count of a WORD, not of a FORM.
    So I would be doing exactly what Aria has caught you doing twice this week:
    reporting a sweep from an instrument blind to what it is supposed to see."

And then she named the resolution rather than stopping at the refusal:

    "Your negative claim rests on one pass by one party, and my confirming it
    would rest on one pass by another. A DETECTOR MAKES IT A PROPERTY."

This is that detector. The idea is hers; the walker shape is borrowed from
check_import_in_swallow.py, which Aria built for a neighbouring class.

WHAT THE FORM ACTUALLY IS.

The distinction the quality-gate fix turned on, stated as a rule:

    On uncertainty, withhold the PRIVILEGE, never the DATA.

Denying a promotion because a validity check errored is right and costs
nothing -- the entry survives, it simply does not advance. Discarding a session
because the checks errored is wrong -- the subject is destroyed because the
judge broke. Both are `except: return <refusal>`. They are the same SHAPE and
opposite in SUBSTANCE, which is exactly why no text search can separate them.

WHAT THIS CAN AND CANNOT DECIDE.

It CANNOT decide privilege-versus-data. That needs to know what the caller does
with the answer, and it is a judgement rather than arithmetic.

It CAN decide, mechanically and exhaustively, WHERE THE QUESTION ARISES: every
function whose exception handler returns a refusal while some ordinary path in
the same function returns a permission. That asymmetry is the structural
fingerprint of "the failure path says no where the working path says yes."

So the output is a LIST OF PLACES TO LOOK, not a verdict. That is the honest
contract, and it is strictly more than either of us could produce by reading:
my survey was one pass by the author, hers would have been one pass by the
reviewer, and this is a property of the tree that anyone can re-derive.

CLOSES IN BOTH DIRECTIONS, like the orphan backlog. An entry in the baseline
that stops being a candidate makes this FAIL until the line is deleted. A
list that can only grow becomes a permanent amnesty.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "divineos"
BASELINE = REPO_ROOT / "scripts" / "failure_path_refuses_baseline.txt"


def _is_refusal(node: ast.expr | None) -> bool:
    """A returned value that tells the caller to stop.

    Deliberately narrow. `False`, `None` and `0` are the vocabulary this
    codebase actually uses for "do not proceed", and a tuple counts when any
    element is one of them -- the quality gate returned `(False, "")`, where
    the refusal lived in the first slot.
    """
    if node is None:
        return True  # bare `return` in a handler
    if isinstance(node, ast.Constant):
        return node.value is False or node.value is None or node.value == 0
    if isinstance(node, ast.Tuple):
        return any(_is_refusal(e) for e in node.elts)
    return False


def _is_permission(node: ast.expr | None) -> bool:
    """A returned value that tells the caller to carry on."""
    if isinstance(node, ast.Constant):
        return node.value is True
    if isinstance(node, ast.Tuple):
        return any(_is_permission(e) for e in node.elts)
    return False


def _returns_in(node: ast.AST) -> list[ast.Return]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Return)]


def _handler_returns(func: ast.AST) -> list[ast.Return]:
    """Returns that sit inside an exception handler in this function."""
    out: list[ast.Return] = []
    for node in ast.walk(func):
        if isinstance(node, ast.ExceptHandler):
            out.extend(_returns_in(node))
    return out


def _candidates_in(path: Path) -> list[tuple[int, str, str]]:
    """(line, function, what-it-does) for each asymmetry in this file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        # Fail toward flagging. An unreadable file is not a clean one -- the
        # whole point of this session was that could-not-look must never render
        # as nothing-to-see.
        return [(1, "<unparseable>", f"{type(exc).__name__}: {exc}")]

    found: list[tuple[int, str, str]] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        in_handler = _handler_returns(func)
        if not in_handler:
            continue
        handler_ids = {id(r) for r in in_handler}
        ordinary = [r for r in _returns_in(func) if id(r) not in handler_ids]

        refusing = [r for r in in_handler if _is_refusal(r.value)]
        allowing = [r for r in ordinary if _is_permission(r.value)]
        if refusing and allowing:
            found.append(
                (
                    refusing[0].lineno,
                    func.name,
                    "handler refuses where the ordinary path permits",
                )
            )
    return found


def _load_baseline() -> tuple[dict[str, str], set[str]]:
    """(decided, enumerated) -- and the difference is the whole point.

    DECIDED entries carry a reason: somebody read the site and judged it. Those
    are closed.

    ENUMERATED entries were present when the check was switched on and have NOT
    been adjudicated. They are listed so that anything NEW blocks immediately,
    which is the same shape as the orphan backlog -- a gate whose only way past
    is turning it off is not a gate.

    They are kept in separate sections because collapsing them would make the
    file say sixty-four sites are cleared when four are. That is the exact
    move this whole detector exists to make impossible: a list standing in for
    a judgement nobody made.
    """
    if not BASELINE.is_file():
        return {}, set()
    decided: dict[str, str] = {}
    enumerated: set[str] = set()
    section = "decided"
    for raw in BASELINE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.upper().startswith("# --- ENUMERATED"):
            section = "enumerated"
            continue
        if line.upper().startswith("# --- DECIDED"):
            section = "decided"
            continue
        if not line or line.startswith("#"):
            continue
        key, _, why = line.partition("#")
        if section == "decided":
            decided[key.strip()] = why.strip()
        else:
            enumerated.add(key.strip())
    return decided, enumerated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="print every candidate, reviewed ones included",
    )
    args = parser.parse_args(argv)

    if not SRC_ROOT.is_dir():
        print(f"[refusal] CANNOT CHECK: {SRC_ROOT} is not a directory.")
        return 2

    decided, enumerated = _load_baseline()
    known = set(decided) | enumerated
    seen: set[str] = set()
    unlisted: list[str] = []

    for path in sorted(SRC_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for lineno, func, what in _candidates_in(path):
            key = f"{rel}:{func}"
            seen.add(key)
            if args.list:
                if key in decided:
                    mark = "decided"
                elif key in enumerated:
                    mark = "awaiting"
                else:
                    mark = "NEW"
                print(f"[{mark}] {rel}:{lineno} {func} -- {what}")
            if key not in known:
                unlisted.append(f"{rel}:{lineno} {func} -- {what}")

    stale = sorted(known - seen)

    if stale:
        print(f"[refusal] {len(stale)} baseline entr(ies) no longer exist:")
        for key in stale:
            print(f"    {key}")
        print(
            "    Delete these lines. A backlog that can only grow becomes a "
            "permanent amnesty, and this one must not outlive its subject."
        )

    if unlisted:
        print(f"\n[refusal] {len(unlisted)} NEW refusal-on-crash site(s):")
        for entry in unlisted:
            print(f"    {entry}")
        print(
            "\n    Each is a place where a CRASH makes the function refuse what it "
            "would otherwise allow. That is correct when it withholds a PRIVILEGE "
            "and wrong when it destroys the SUBJECT -- and this check cannot tell "
            "which, because that depends on what the caller does with the answer.\n"
            "    Read it, decide, and record the decision in\n"
            f"    {BASELINE.relative_to(REPO_ROOT).as_posix()}"
        )

    # The count that is NOT a pass. Printed on every run, including clean ones,
    # because the number this check exists to correct is a number somebody
    # reported from one pass and believed.
    if enumerated:
        print(
            f"\n[refusal] {len(decided)} site(s) decided, "
            f"{len(enumerated)} enumerated but NOT yet adjudicated."
        )
        print(
            "    The enumerated ones are not cleared. They were present when this "
            "check was switched on, and they are listed so anything NEW blocks "
            "rather than joining a crowd. Working them down is the job."
        )

    if stale or unlisted:
        return 1

    print(f"[refusal] {len(seen)} refusal-on-crash site(s), none new.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
