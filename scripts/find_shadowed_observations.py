"""Find a name that carries an OBSERVATION and is then overwritten by a FINDING.

WHY THIS EXISTS (2026-09-18, council-bb635a3d2612).

The gravity classifier recorded "this shell command wrote a file" by reassigning
the same variable that gated the command-level checks. Noting a write therefore
switched those checks OFF, and a commit with its output sent to a log file faced
no gate at all. One redirect, zero checks. The comment two lines above promised
the opposite and had been false since the reassignment was introduced.

One name was doing two jobs — the OBSERVED tool kind, and a FINDING about the
command — and recording the finding silently ended the other job. It reads
correctly at the assignment site, which is why several careful readings that day
went straight past it.

I wrote in that commit that I had NOT surveyed for other instances. This is the
survey, so that sentence is a statement rather than a receipt.

WHAT IT LOOKS FOR
-----------------
A local name assigned more than once, where a later assignment is a BARE
LITERAL, and the name is still used in an `if` test afterwards. The literal is
the tell: that is what recording a finding looks like.

HOW TO READ A HIT — the part that does not survive in anyone's memory, so it
lives here instead:

    A flag that was ALWAYS a flag is fine. Something set False, later set True,
    then tested, is the ordinary set-and-test pattern and is not a defect.

    The fault is a name that carried an OBSERVATION and was then overwritten by
    a FINDING, while tests written against the observation still read it.

    Only reading separates those two. This tool cannot.

MY FIRST MODEL WAS WRONG, AND THAT IS THE MOST USEFUL THING HERE.
I looked for tested-then-overwritten-then-tested. The real fault had NO tests
before the overwrite — every test came after — so the first version of this
probe sailed straight past the one case it was built to find. I learned that
only by running it against the pre-repair file and watching it come back clean
when it should not have.

A probe that misses its founding case reports silence, and silence from a broken
instrument is indistinguishable from silence from a healthy system. That is the
same shape as the hole it hunts, one level up. So: CONTROL IT BOTH WAYS before
believing a sweep — it must find the known case, and must stop finding it after
the repair. Both were run.

WHAT THIS DOES NOT LOOK AT, said in the same breath so silence is never read as
coverage:
  - the same fault spread across two functions, or through an attribute
  - anything not Python — the shell hooks were never scanned and are not covered
  - overwrites from an expression rather than a bare literal

PRIOR ART, checked rather than assumed: fourteen other scripts here parse the
tree, and the two nearest neighbours do different jobs — one finds functions
nothing calls, the other finds first-party imports hidden inside swallowed
exceptions. Neither looks at reassignment.

SWEEP RESULT at time of writing: no second instance WITHIN this shape across the
hook and council-gate modules. Eight candidates surfaced; all eight were benign
on reading. The claim is "no second instance within this shape." Not "none."
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def scan(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, str, int, int]]:
    """Candidates inside one function. Never a verdict — see the reading rule."""
    assigns: dict[str, list[int]] = {}
    const_assigns: dict[str, list[int]] = {}
    tests: dict[str, list[int]] = {}

    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigns.setdefault(target.id, []).append(node.lineno)
                    if isinstance(node.value, ast.Constant):
                        const_assigns.setdefault(target.id, []).append(node.lineno)
        elif isinstance(node, ast.If):
            for sub in ast.walk(node.test):
                if isinstance(sub, ast.Name):
                    tests.setdefault(sub.id, []).append(node.lineno)

    hits = []
    for name, const_lines in const_assigns.items():
        if len(assigns.get(name, [])) < 2:
            continue
        first_assign = min(assigns[name])
        for line in const_lines:
            if line == first_assign:
                continue  # an initialisation, not an overwrite
            after = [t for t in tests.get(name, []) if t > line]
            if after:
                hits.append((name, fn.name, line, len(after)))
                break
    return hits


def main(paths: list[str]) -> int:
    total = 0
    for path in paths:
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError) as exc:
            # Loud rather than skipped: an unreadable file is not a clean one,
            # and a silent skip here would rebuild the exact blind spot above.
            print(f"UNREADABLE {path}: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for name, fname, line, n_after in scan(node):
                    total += 1
                    print(
                        f"{path}:{line}  {name!r} overwritten by a literal in "
                        f"{fname}(), then tested {n_after} time(s) after"
                    )
    print(f"--- {total} candidate(s). Read each one: a flag is fine, an")
    print("    overwritten observation is the fault. This cannot tell them apart. ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
