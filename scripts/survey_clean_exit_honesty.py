"""Two measurements of whether our own checks can be caught being wrong.

WHERE THIS CAME FROM. Aether, 2026-09-20, naming the limit neither of us has
passed: every catch that day came from a wrong answer too strange to survive
being looked at, never from checking. His conclusion, and it is the right one
-- the practice that would move the limit is not looking harder, it is
refusing to accept outputs in forms that cannot look wrong. He said it out
loud specifically so it would not become another thing we name three times.
This is the measurement half of that.

FIRST MEASUREMENT: does the check refuse when it could not check?
A guard is a conditional whose test is an emptiness, zero, or is-None check
and whose body exits non-zero, returns non-zero, or raises. Grepping for the
word "refuse" counts a WORD; this counts a SHAPE. The distinction is the whole
reason the first version of this was thrown away.

SECOND MEASUREMENT: can the all-clear look wrong?
"no findings" reads identically whether the scan covered the tree or nothing
at all. "no findings among 812 scanned" cannot -- a broken scan shows in the
number. That difference is the only thing that has actually caught anything
here, so it is worth knowing which of our checks have it.

WHAT THIS DOES NOT DECIDE. Neither list is a list of defects. A diff-mode
check has no emptiness case worth refusing, because an empty diff genuinely IS
clean. Whether a given script needs either guard is a judgement about what its
caller does with the answer, and it stays with a reader.

THE CONTROLS RUN ON EVERY INVOCATION, and that is deliberate rather than
tidy. Each matcher is checked against a script read by hand before any of its
other answers print, and a failed control refuses the whole run. The first
version of this reported its own control as missing -- the guard it could not
see returns a conditional rather than a plain value -- and without the control
that blindness would have shipped as a finding about twenty-three scripts.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _refuse_if_not_the_repository() -> str | None:
    """Return a refusal message if this file is not sitting in the tree.

    The root is derived from this file's own position, so a copy dropped in a
    scratch directory reads whatever happens to be beside it -- right kind of
    object, wrong object, which is the fault this whole house has been chasing.
    Aether hit it running this from his scratchpad, 2026-09-20: it did not
    error, it surveyed a directory that was not the repository.

    A location it cannot confirm must not produce a clean-looking survey.
    """
    for marker in (REPO / "scripts", REPO / "src" / "divineos", REPO / ".claude" / "hooks"):
        if not marker.is_dir():
            return (
                f"REFUSED: {REPO} does not look like the repository "
                f"(missing {marker.relative_to(REPO)}).\n"
                "  This file locates the tree from its own position, so a copy "
                "outside it\n  surveys the wrong directory. Run it from inside "
                "the repository."
            )
    return None


def _is_emptiness_test(node: ast.expr) -> bool:
    # if not <thing>:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    # if len(x) == 0 / < 1, or x == 0
    if isinstance(node, ast.Compare):
        for side in [node.left, *node.comparators]:
            if isinstance(side, ast.Constant) and side.value in (0, 1):
                return True
            # `if added is None:` -- the could-not-read form. A diff-mode check
            # has no emptiness case worth refusing (an empty diff IS clean),
            # but it still has to refuse when it could not read the diff at
            # all. Same class, different instance: could-not-check must never
            # wear the clean answer.
            if isinstance(side, ast.Constant) and side.value is None:
                return True
    return False


def _body_refuses(body: list[ast.stmt]) -> bool:
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Return) and node.value is not None:
            # A plain `return 1`, or a conditional one such as
            # `return 0 if args.warn_only else 1` -- the real guards in this
            # tree are written the second way, and the first version of this
            # probe saw only the first and reported its own control as absent.
            values = [node.value]
            if isinstance(node.value, ast.IfExp):
                values = [node.value.body, node.value.orelse]
            for value in values:
                if isinstance(value, ast.Constant) and isinstance(value.value, int):
                    if value.value != 0:
                        return True
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name in {"exit", "SystemExit"}:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value not in (0, None):
                        return True
    return False


def has_guard(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_emptiness_test(node.test):
            if _body_refuses(node.body):
                return True
    return False


def _clean_message_carries_a_denominator(path: Path) -> bool:
    """Does any all-clear message name what was examined?

    The FORM: a print whose argument is an f-string carrying an interpolated
    value, sitting in a function that also returns 0. `no duplicates among 812
    scanned` can look wrong to a reader. `All checks passed` cannot -- it reads
    identically whether the scan covered the tree or nothing at all.

    This is deliberately generous: any interpolation counts. A generous
    matcher here makes the NEGATIVE answer the trustworthy one, which is the
    direction that matters -- a script this says has no denominator almost
    certainly has none.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return False

    def interpolating_print(stmt: ast.stmt) -> bool:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            return False
        if getattr(stmt.value.func, "id", None) != "print":
            return False
        # NOT A MESSAGE TO THE ERROR STREAM. Two scripts print a could-not-run
        # notice to stderr and then return zero, and the first version of this
        # counted those as all-clears -- a refusal read as the opposite of
        # itself. Caught by the output looking wrong, which is the only thing
        # that has caught anything here, and exactly why this prints the lines
        # rather than only counting them.
        for kw in stmt.value.keywords:
            if kw.arg == "file":
                return False
        for arg in stmt.value.args:
            if isinstance(arg, ast.JoinedStr):
                if any(isinstance(v, ast.FormattedValue) for v in arg.values):
                    return True
        return False

    # THE SUCCESS PATH ONLY. Scanning the whole file for an interpolation
    # answers a different question and answers it 35 times out of 37 -- a
    # script can be chatty about its findings and print a bare OK when it
    # finds none, which is the exact shape in question.
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i, stmt in enumerate(body):
            clean_exit = (
                isinstance(stmt, ast.Return)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value == 0
            )
            if clean_exit and i > 0 and interpolating_print(body[i - 1]):
                prev = body[i - 1]
                return (prev.lineno, getattr(prev, "end_lineno", None) or prev.lineno)
    return None


def _clean_message_text(path: Path, span: tuple[int, int]) -> str:
    """The all-clear line as written, so a reader can see the shape rather than
    be told about it. Asked for by Aether, 2026-09-20: he wanted to read what a
    good all-clear looks like in this house rather than invent a shape for his.
    """
    start, end = span
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not 0 < start <= end <= len(lines):
        return "(could not read the line)"
    # A multi-line call is joined rather than truncated at its opening
    # parenthesis. The first version printed a bare "print(" for one script,
    # which said nothing about the shape a reader was asking to see.
    return " ".join(" ".join(lines[start - 1 : end]).split())


def main() -> int:
    wrong_tree = _refuse_if_not_the_repository()
    if wrong_tree:
        print(wrong_tree)
        return 2

    scripts = sorted((REPO / "scripts").glob("check_*.py"))
    if not scripts:
        print("REFUSED: found no check scripts, so the probe is broken.")
        return 2

    # CONTROL FIRST. The probe must find a case I know the answer to before any
    # of its other answers are worth reading.
    known_yes = REPO / "scripts" / "check_duplicate_files.py"
    if not known_yes.exists():
        print(f"REFUSED: control file missing: {known_yes}")
        return 2
    if not has_guard(known_yes):
        print("REFUSED: the probe cannot find the guard in a script I know has one.")
        print("  The instrument is blind; every other answer below would be noise.")
        return 2
    print(f"control held (positive): the probe finds the guard in {known_yes.name}")

    # NEGATIVE CONTROL. A matcher that says yes to everything would pass the
    # positive control above and be useless. This file was read before being
    # named here: its refusals all fire on FINDINGS (drift detected, conflict
    # markers present), and it has no emptiness or could-not-read guard.
    known_no = REPO / "scripts" / "check_doc_counts.py"
    if known_no.exists() and has_guard(known_no):
        print("REFUSED: the probe claims a guard in a script read by hand as having none.")
        print("  It is saying yes too easily; the list below would be meaningless.")
        return 2
    print(f"control held (negative): the probe finds no guard in {known_no.name}")

    guarded, unguarded = [], []
    for path in scripts:
        (guarded if has_guard(path) else unguarded).append(path.name)

    print()
    print(f"{len(scripts)} check script(s); {len(guarded)} refuse on an empty scan, {len(unguarded)} do not")
    print()
    print("NO EMPTY-SCAN REFUSAL -- candidates, not defects.")
    print("  A script that cannot scan nothing does not need the guard.")
    for name in unguarded:
        print(f"  {name}")

    # CONTROLS AGAIN, on the second measurement, because it is a different
    # matcher and the first pair of controls says nothing about it.
    dup = REPO / "scripts" / "check_duplicate_files.py"
    if not _clean_message_carries_a_denominator(dup):
        print()
        print("REFUSED (second measurement): the probe misses a clean line I read")
        print(f"  by hand in {dup.name}: 'no byte-identical files among N scanned'.")
        return 2
    doc = REPO / "scripts" / "check_doc_counts.py"
    if not _clean_message_carries_a_denominator(doc):
        print()
        print("REFUSED (second measurement): the probe misses the all-clear in")
        print(f"  {doc.name}, which names every count it measured.")
        return 2

    speaking, bare = [], []
    for path in scripts:
        span = _clean_message_carries_a_denominator(path)
        if span:
            speaking.append((path.name, _clean_message_text(path, span)))
        else:
            bare.append(path.name)

    print()
    print("SECOND MEASUREMENT -- whose ALL-CLEAR can look wrong at all.")
    print("  (controls held: both scripts read by hand are found)")
    print(f"  {len(speaking)} of {len(scripts)} name what they examined in the message")
    print("  they print on their way to a clean exit. The rest say it in fixed")
    print("  text, which reads the same whether the scan covered the whole tree")
    print("  or nothing at all.")
    print()
    print("THE ALL-CLEARS THAT CAN LOOK WRONG, as written:")
    for name, text in speaking:
        print(f"  {name}")
        print(f"      {text}")
    print()
    print("THE ONES THAT CANNOT:")
    for name in bare:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
