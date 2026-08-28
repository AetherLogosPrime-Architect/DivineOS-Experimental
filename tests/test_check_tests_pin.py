"""Tests for the pin-checker -- does a new test fail against the old code?

The instrument exists because I shipped a regression test that was green on
both sides of the fix it claimed to guard. Its own tests therefore have to be
careful about the same thing: several below are deliberately about what the
checker CANNOT see, because a checker whose limits are unstated gets read as
covering everything.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = REPO_ROOT / "scripts" / "check_tests_pin.py"

_spec = importlib.util.spec_from_file_location("check_tests_pin", _MODULE_PATH)
assert _spec and _spec.loader
pin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pin)


# --- finding the test functions ------------------------------------------


def test_finds_module_level_test_functions():
    src = "def test_a():\n    assert 1\n\ndef helper():\n    pass\n"
    assert set(pin.test_functions(src)) == {"test_a"}


def test_ignores_non_test_functions():
    """A helper is not a test, and counting one would demand a pin it never owed."""
    src = "def build_fixture():\n    return 1\n"
    assert pin.test_functions(src) == {}


def test_finds_methods_inside_test_classes_with_node_id_separator():
    src = "class TestThing:\n    def test_b(self):\n        assert 1\n"
    assert set(pin.test_functions(src)) == {"TestThing::test_b"}


def test_unparseable_source_yields_nothing_rather_than_raising():
    """An old version that does not parse means every function reads as NEW.

    That is the safe direction: it over-reports work to do rather than
    silently skipping a file, and a crash here would take the whole check
    down over one bad historical commit.
    """
    assert pin.test_functions("def test_a(:\n") == {}


# --- what counts as changed ----------------------------------------------


def test_comment_only_edit_is_not_a_changed_test():
    """Compared as unparsed AST, so a comment edit does not demand a new pin.

    This is the difference between a check people run and a check people
    disable. Reformatting a test file must not produce a wall of findings.
    """
    before = pin.test_functions("def test_a():\n    # old note\n    assert 1\n")
    after = pin.test_functions("def test_a():\n    # new note\n    assert 1\n")
    assert before == after


def test_a_real_body_change_is_detected():
    before = pin.test_functions("def test_a():\n    assert 1\n")
    after = pin.test_functions("def test_a():\n    assert 2\n")
    assert before != after


# --- the baseline proof, which is the whole reason this is trustworthy ----


def test_baseline_proof_rejects_a_module_resolved_outside_the_worktree(tmp_path):
    """The editable-install trap, stated as a test.

    `import divineos` inside a base-tree worktree resolves to the CURRENT
    source unless the path is forced. Without this refusal the checker would
    grade the fix against itself and report a confident green -- the
    wrong-baseline shape, which cost me two wrong answers building this very
    instrument.
    """
    elsewhere = tmp_path / "not-the-worktree"
    (elsewhere / "divineos").mkdir(parents=True)
    outside = elsewhere / "divineos" / "__init__.py"
    outside.write_text("", encoding="utf-8")
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # A stand-in interpreter that reports a divineos living OUTSIDE the
    # worktree -- exactly what an editable install does. It must not prove.
    stub = tmp_path / "stub_python.py"
    stub.write_text(
        "import sys\nsys.stdout.write(sys.argv[-1])\n",
        encoding="utf-8",
    )

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = str(outside)

        assert cmd[1] == "-c"  # the probe is still a -c invocation
        return Result()

    monkey = getattr(pin, "subprocess")
    original = monkey.run
    monkey.run = fake_run
    try:
        assert pin.prove_baseline(worktree, "python") is None
    finally:
        monkey.run = original


def test_baseline_proof_accepts_a_module_resolved_inside_the_worktree(tmp_path):
    """The other direction, so the refusal above is not vacuously true.

    A test that only ever checks the rejecting case passes just as happily
    when the function rejects everything, which would make the whole checker
    unable to run while looking correct.
    """
    worktree = tmp_path / "worktree"
    inside = worktree / "src" / "divineos" / "__init__.py"
    inside.parent.mkdir(parents=True)
    inside.write_text("", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class Result:
            stdout = str(inside)

        return Result()

    original = pin.subprocess.run
    pin.subprocess.run = fake_run
    try:
        assert pin.prove_baseline(worktree, "python") == str(inside)
    finally:
        pin.subprocess.run = original


def test_a_python_that_prints_nothing_does_not_prove_a_baseline(tmp_path):
    """Silence is not proof. An import that produced no path must refuse."""
    import sys

    worktree = tmp_path / "wt"
    worktree.mkdir()
    # sys.executable here has no divineos on the forced PYTHONPATH, so the
    # probe cannot resolve one inside this empty worktree.
    assert pin.prove_baseline(worktree, sys.executable) is None
