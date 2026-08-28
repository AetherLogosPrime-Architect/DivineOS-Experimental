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


class _FakePytest:
    """Stand-in for the probe run, so every outcome can be exercised.

    Records the argv it was handed. The proof must be taken THROUGH PYTEST --
    Aria's 2026-08-28 finding was that the original took it with `python -c`
    and then spent it in `python -m pytest`, which builds a different sys.path
    from pyproject and conftest. Right answer, room next door.
    """

    def __init__(self, returncode: int, stamp: Path | None, text: str = ""):
        self._returncode = returncode
        self.stamp = stamp
        self.text = text
        self.argv: list[str] = []

    def __call__(self, cmd, **kwargs):
        self.argv = list(cmd)
        if self.stamp is not None:
            self.stamp.parent.mkdir(parents=True, exist_ok=True)
            self.stamp.write_text(self.text, encoding="utf-8")
        rc = self._returncode

        class Result:
            returncode = rc
            stdout = ""
            stderr = ""

        return Result()


def _with_fake(fake, fn):
    original = pin.subprocess.run
    pin.subprocess.run = fake
    try:
        return fn()
    finally:
        pin.subprocess.run = original


def test_the_proof_is_taken_through_pytest_not_a_bare_interpreter(tmp_path):
    """Aria's finding, pinned: the proof and its use must run the same way.

    A `python -c` probe answers about a process that never runs a graded test.
    pytest puts `pythonpath` from pyproject at sys.path[0] on its own
    authority, and conftest inserts more -- neither happens under `-c`. The old
    version was correct only because the two happened to agree, which it
    neither stated nor tested.
    """
    worktree = tmp_path / "wt"
    inside = worktree / "src" / "divineos" / "__init__.py"
    inside.parent.mkdir(parents=True)
    fake = _FakePytest(0, worktree / pin._STAMP_NAME, str(inside))
    _with_fake(fake, lambda: pin.prove_baseline(worktree, "python"))
    assert "pytest" in fake.argv
    assert "-c" not in fake.argv


def test_baseline_proof_accepts_a_module_resolved_inside_the_worktree(tmp_path):
    """The accepting direction, so the refusals are not vacuously true.

    A proof that only ever rejects passes just as happily when it rejects
    everything, which would leave the checker unable to run while looking
    correct.
    """
    worktree = tmp_path / "wt"
    inside = worktree / "src" / "divineos" / "__init__.py"
    inside.parent.mkdir(parents=True)
    fake = _FakePytest(0, worktree / pin._STAMP_NAME, str(inside))
    assert _with_fake(fake, lambda: pin.prove_baseline(worktree, "python")) == str(inside)


def test_baseline_proof_refuses_when_the_probe_test_fails(tmp_path):
    """The editable-install trap, stated as a test.

    `import divineos` inside a base-tree worktree resolves to CURRENT source
    unless the path is forced. Without this refusal the checker would grade the
    fix against itself and report a confident green -- the wrong-baseline
    shape, which cost me two wrong answers building this very instrument.
    """
    worktree = tmp_path / "wt"
    worktree.mkdir()
    assert _with_fake(_FakePytest(1, None), lambda: pin.prove_baseline(worktree, "python")) is None


def test_a_green_probe_with_no_stamp_behind_it_does_not_prove(tmp_path):
    """An unexplained pass is not proof.

    A zero exit with nothing written means the probe never actually executed --
    collected nothing, skipped, deselected. Treating that as proven is the
    armed-and-unheard shape wearing an exit code.
    """
    worktree = tmp_path / "wt"
    worktree.mkdir()
    assert _with_fake(_FakePytest(0, None), lambda: pin.prove_baseline(worktree, "python")) is None


def test_an_empty_stamp_does_not_prove(tmp_path):
    """Silence is not proof, in the file as well as in the exit code."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    fake = _FakePytest(0, worktree / pin._STAMP_NAME, "")
    assert _with_fake(fake, lambda: pin.prove_baseline(worktree, "python")) is None
