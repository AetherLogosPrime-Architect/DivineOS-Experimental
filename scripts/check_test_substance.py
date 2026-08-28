#!/usr/bin/env python3
"""Audit the test suite for tests that cannot fail.

WHY THIS EXISTS. Andrew 2026-08-25: "the 12k test.. are we sure all of the
tests are legit? and not another version of 'fake greens'? we should probably
look as those tests go back to the very beginning of the project."

A passing suite is evidence only if a failing implementation would have made it
red. A test that asserts nothing, asserts a constant, swallows the exception it
should be checking, or skips itself unconditionally is a green light wired to
nothing. Those are indistinguishable from real coverage in a pytest summary
line, which is the whole problem: the number goes up either way.

This walks every test function with the AST and classifies it. It does NOT
decide whether a test is good -- only whether it is CAPABLE of failing, which
is a structural property a parser can see. Judging whether a capable test
checks the right thing is reading work and stays with the reader.

WHY A SECOND INSTRUMENT, when run_mutmut.py already exists. Mutation testing
answers "does the suite notice a change" by breaking the implementation, which
is stronger evidence -- and it runs over eight critical modules out of 724.
That is a sample. This asks a weaker question across all of them: can this
particular test ever go red. Neither replaces the other. Reporting the
mutation result as a verdict on the whole suite would be the wrong-denominator
shape, which this substrate has paid for before.

WHAT IT CANNOT SEE, stated because silence here must not read as coverage:
  - a test that asserts something true-by-construction ("assert x == x" via
    two paths that are the same path). Capable of failing, never will.
  - a test whose assertions all sit behind a condition that is never true at
    runtime. The branch is visible; whether it executes is not.
  - a test that exercises a mock and asserts on the mock. Counted as having
    assertions, because it does.
  - whether an assertion checks the interesting property or a trivial one.
Only mutation testing answers those, and that is the other instrument.
"""

from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

# Calls that constitute a real check even though they are not `assert`.
_ASSERTING_CALLS = frozenset(
    {
        "raises",
        "warns",
        "deprecated_call",
        "fail",
        "approx",
        "assert_called",
        "assert_called_once",
        "assert_called_with",
        "assert_called_once_with",
        "assert_any_call",
        "assert_has_calls",
        "assert_not_called",
        "assertEqual",
        "assertTrue",
        "assertFalse",
        "assertRaises",
        "assertIn",
        "assertIsNone",
        "assertIsNotNone",
        "assertAlmostEqual",
        "assertGreater",
        "assertLess",
    }
)

# Names that mean "this test declined to run".
_SKIPPING = frozenset({"skip", "xfail", "exit"})


class _TestVisitor(ast.NodeVisitor):
    """Walk one test function body and record what it is capable of."""

    def __init__(self) -> None:
        self.asserts = 0
        self.trivial_asserts = 0
        self.asserting_calls = 0
        self.unconditional_skip = False
        self.swallowing_handlers = 0
        self.helper_calls = 0

    def visit_Raise(self, node: ast.Raise) -> None:
        # `try: f(); except Expected: return` followed by
        # `raise AssertionError("...")` is the third spelling of the
        # raises-idiom in this suite, and the richest -- the message explains
        # what the regression would mean. Reading only `assert` called three
        # correct tests assertion-free, in files whose whole subject is
        # catching silent failure. A check is a way to fail, not a keyword.
        self.asserting_calls += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.asserts += 1
        if _is_trivially_true(node.test):
            self.trivial_asserts += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        if name in _ASSERTING_CALLS:
            self.asserting_calls += 1
        elif name in _SKIPPING and _is_pytest_call(node.func):
            self.unconditional_skip = True
        elif name and (name.startswith("_assert") or name.startswith("assert_")):
            # Project-local assertion helpers. Counted separately so a suite
            # that centralises its checks does not read as assertion-free.
            self.helper_calls += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        # A pytest.skip() inside a condition is a platform guard, which is
        # legitimate. Only skips on the unconditional path are findings, so
        # the branch bodies are walked with skip-detection suppressed.
        guarded = _TestVisitor()
        for stmt in node.body + node.orelse:
            guarded.visit(stmt)
        self.asserts += guarded.asserts
        self.trivial_asserts += guarded.trivial_asserts
        self.asserting_calls += guarded.asserting_calls
        self.helper_calls += guarded.helper_calls
        self.swallowing_handlers += guarded.swallowing_handlers
        self.visit(node.test)

    def visit_Try(self, node: ast.Try) -> None:
        # A try whose BODY carries its own failure mechanism is the manual
        # pytest.raises idiom -- `try: f(); assert False; except ValueError:
        # pass` fails loudly when nothing raises. The first version of this
        # check only read the handler, so it flagged three correct
        # rejection tests in test_user_ratings.py as swallows. Read the whole
        # construct or the verdict is about the wrong half of it.
        if not _body_can_fail(node.body):
            for handler in node.handlers:
                if _handler_swallows(handler):
                    self.swallowing_handlers += 1
        self.generic_visit(node)


def _call_name(func: ast.expr) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_pytest_call(func: ast.expr) -> bool:
    """True for ``pytest.skip(...)`` shapes, false for a local ``skip()``."""
    return isinstance(func, ast.Attribute) and _call_name(func.value) in {"pytest", "pt"}


def _is_trivially_true(test: ast.expr) -> bool:
    """``assert True``, ``assert 1``, ``assert "x"``, ``assert 1 == 1``."""
    if isinstance(test, ast.Constant):
        return bool(test.value)
    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Constant):
        return all(isinstance(c, ast.Constant) for c in test.comparators)
    return False


def _handler_swallows(handler: ast.ExceptHandler) -> bool:
    """An except block whose body cannot fail the test.

    ``except X: pass`` and ``except X: return`` in a TEST turn a real error
    into a pass. A handler that re-raises, calls pytest.fail, or asserts is
    doing real work and is not counted.
    """
    for node in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
        if isinstance(node, (ast.Raise, ast.Assert)):
            return False
        if isinstance(node, ast.Call) and _call_name(node.func) in {"fail", "skip", "xfail"}:
            return False
    return all(isinstance(stmt, (ast.Pass, ast.Return, ast.Expr)) for stmt in handler.body)


def _body_can_fail(body: list[ast.stmt]) -> bool:
    """True if this block carries its own way to fail the test."""
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call) and _call_name(node.func) in {"fail", "raises"}:
            return True
    return False


# Verbs in a test name that promise an OBSERVABLE outcome. A test named for
# one of these with nothing checking it is the shape Andrew asked about: the
# name asserts a behaviour the body never looks at.
#
# The complement matters as much. `test_module_importable`,
# `test_clear_missing_marker_is_safe`, `test_verbatim_in_source_passes` have no
# assert and are still real tests: the code under test raises on failure, so
# not-raising IS the check. Lumping those in with the others inflates the
# finding and buries the handful that are genuinely empty.
_BEHAVIOUR_CLAIMS = (
    "_fires",
    "_transforms",
    "_bypasses",
    "_truncat",
    "_detects",
    "_returns",
    "_writes",
    "_updates",
    "_creates",
    "_deletes",
    "_counts",
    "_filters",
    "_emits",
    "_records",
    "_propagates",
    "_blocks",
    "_rejects",
    "_includes",
)


def _name_claims_behaviour(name: str) -> bool:
    return any(claim in name for claim in _BEHAVIOUR_CLAIMS)


def _is_test_function(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
        "test_"
    )


def _decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = set()
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        names.add(_call_name(target))
    return names


def _ends_in_failure(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the function's last statement is a raise or an assert.

    That is the tail of the manual raises-idiom:

        try:
            thing_that_should_raise()
        except ValueError:
            return                      # <- the SUCCESS path
        raise AssertionError("...")     # <- reached only on failure

    Read in isolation the handler looks like a swallow. Read with its tail it
    is the opposite: the only way out without failing. Counting it as a
    swallow blamed three tests whose entire subject is catching silent
    failure, which would have been an embarrassing way to answer a question
    about tests that cannot fail.

    The RETURN is load-bearing, and the first version of this function missed
    that. It excused every swallowing handler in any function ending in a
    check, so ``except Exception: pass`` followed later by an unrelated
    ``assert`` came back clean. Its own test caught it. A handler that falls
    through does not skip the tail, so the tail says nothing about it; only a
    handler that transfers control past the tail is the idiom.
    """
    if not node.body:
        return False
    if not isinstance(node.body[-1], (ast.Raise, ast.Assert)):
        return False
    return any(
        isinstance(stmt, ast.Return) for handler in _handlers_in(node) for stmt in handler.body
    )


def _handlers_in(node: ast.AST) -> list[ast.ExceptHandler]:
    return [n for n in ast.walk(node) if isinstance(n, ast.ExceptHandler)]


def classify(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, str]:
    """Return ``(verdict, detail)`` for one test function."""
    visitor = _TestVisitor()
    for stmt in node.body:
        visitor.visit(stmt)
    if _ends_in_failure(node):
        visitor.swallowing_handlers = 0
    decorators = _decorator_names(node)
    checks = visitor.asserts + visitor.asserting_calls + visitor.helper_calls
    real_checks = checks - visitor.trivial_asserts

    if "skip" in decorators or "xfail" in decorators:
        return "DECLARED-SKIP", f"decorated {sorted(decorators)}"
    if visitor.unconditional_skip:
        return "SELF-SKIP", "calls pytest.skip outside any condition"
    if checks == 0:
        if _name_claims_behaviour(node.name):
            return (
                "NAME-CLAIMS-MORE",
                "name promises an observable outcome; body asserts nothing",
            )
        return (
            "NO-ASSERT",
            "no assertion; passes unless the code under test raises",
        )
    if real_checks == 0:
        return "TRIVIAL-ONLY", f"{visitor.trivial_asserts} constant assertion(s)"
    if visitor.swallowing_handlers:
        return (
            "SWALLOWS",
            f"{visitor.swallowing_handlers} handler(s) turn an error into a pass",
        )
    return "CAPABLE", f"{real_checks} check(s)"


def audit_file(path: Path) -> list[dict]:
    """Return one record per test function in ``path``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        # Fail toward FLAGGING. An unreadable test file is not a clean one.
        return [
            {
                "file": str(path.relative_to(REPO_ROOT)),
                "test": "<unparseable>",
                "line": 1,
                "verdict": "UNPARSEABLE",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        ]

    records = []
    for node in ast.walk(tree):
        if not _is_test_function(node):
            continue
        verdict, detail = classify(node)
        records.append(
            {
                "file": str(path.relative_to(REPO_ROOT)),
                "test": node.name,
                "line": node.lineno,
                "verdict": verdict,
                "detail": detail,
            }
        )
    return records


def audit_suite() -> list[dict]:
    records: list[dict] = []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        records.extend(audit_file(path))
    return records


def main(argv: list[str]) -> int:
    show = argv[1] if len(argv) > 1 else ""
    records = audit_suite()

    counts = Counter(r["verdict"] for r in records)
    total = len(records)
    capable = counts.get("CAPABLE", 0)

    # COULD-NOT-LOOK IS NOT A CLEAN BILL. Aether hit this 2026-08-28 and it
    # arrived as a ZeroDivisionError three lines below -- inside the instrument
    # built to find tests that cannot fail. The mechanism is narrower than it
    # first looked, and the difference decides the fix: running this script IN
    # PLACE from any working directory is fine, because TESTS_DIR is derived
    # from __file__ and not from the cwd. What breaks it is running a COPY of
    # the file from somewhere else, which puts the derived tests directory
    # somewhere with no tests in it. Verified both ways before writing this.
    #
    # So the repair is not "find the tests from the cwd instead" -- it is to
    # refuse when the derived directory yielded nothing, and to say which
    # directory that was, because the answer is almost always visible the
    # moment the path is printed. A crash and a clean bill are equally easy to
    # read as "the tool is fine, my invocation was odd."
    if total == 0:
        print(f"REFUSED: parsed no test functions under {TESTS_DIR}")
        print()
        if not TESTS_DIR.is_dir():
            print("That directory does not exist.")
        else:
            print("That directory exists but holds no test_*.py files.")
        print(
            "This script derives its tests directory from its OWN location "
            "(parents[1] of __file__), not from the working directory. Running "
            "it in place is safe from anywhere; running a COPY of it outside "
            "the repository points it at a tree with no tests."
        )
        print("Run the copy in scripts/ of a real checkout, or pass the repo one.")
        print()
        print("Reporting nothing is not the same as finding nothing wrong.")
        return 2

    print(f"Test functions parsed: {total}")
    for verdict, count in counts.most_common():
        pct = (count / total * 100) if total else 0.0
        print(f"  {verdict:<14} {count:>6}  ({pct:.2f}%)")
    print()
    print(f"Capable of failing: {capable}/{total} ({capable / total * 100:.2f}%)")

    if show:
        print()
        print(f"== {show} ==")
        for record in records:
            if record["verdict"] == show:
                print(f"  {record['file']}:{record['line']} {record['test']} - {record['detail']}")

    # Reporting instrument, not a gate. It exits 0 so it can be run on a dirty
    # tree while findings are worked through; wiring it into precommit as a
    # blocker is a separate decision with its own threshold.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
