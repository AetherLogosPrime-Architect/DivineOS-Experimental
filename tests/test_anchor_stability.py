"""An anchor is only meaningful if nothing automated is still going to rewrite it.

THE INCIDENT, 2026-09-11. Aletheia audited a branch and signed it. Her confirm
binds to the content she read. I then ran the merge-stamp tool, checked the tree
first because I knew her signature bound to it, and it was byte-identical --
and then the pre-commit formatter rejoined two wrapped lines in a test. Same
call, same arguments, no behaviour touched. The change-fingerprint moved and her
signature read NO LONGER HOLDS.

AND IT WAS THE SECOND TIME. From a round filed 2026-05-10, found by searching
before building: "Andrew re-confirmed after auto-format whitespace changes
drifted the hash. Substantive content unchanged; intent identical to original
CONFIRMS." Same cause, four months earlier, answered with a human re-signing by
hand. A resolution rather than a fix, so the recurrence was guaranteed and only
its date was open.

So the question this answers is asked BEFORE a signature is requested rather
than after it dies: are the files this branch changes already a fixed point of
the formatter? If not, an anchor taken now is void after the next commit.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.core.anchor_stability import formatter_stability

WRAPPED = """def f():
    result = some_call(
        "a", "b"
    )
    return result
"""

ALREADY_FLAT = """def f():
    result = some_call("a", "b")
    return result
"""


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "workbench").mkdir()
    return root


def test_a_file_the_formatter_would_rewrite_is_unstable(repo):
    """THE LOAD-BEARING ONE. This is the live cause of the lost signature."""
    (repo / "src" / "thing.py").write_text(WRAPPED, encoding="utf-8")

    out = formatter_stability(repo, ["src/thing.py"])

    assert out.state == "unstable"
    assert "src/thing.py" in out.unstable


def test_a_file_already_at_the_fixed_point_is_stable(repo):
    (repo / "src" / "thing.py").write_text(ALREADY_FLAT, encoding="utf-8")

    out = formatter_stability(repo, ["src/thing.py"])

    assert out.state == "stable"
    assert out.unstable == ()


def test_instability_outside_the_changed_set_does_not_refuse(repo):
    """WAYNE'S CONTROL, and the accidental implementation it catches.

    This repository has a scratch directory the formatter would rewrite on
    sight. A check that looked at the whole tree would refuse every branch
    forever, which is a check that gets switched off inside a week -- and it
    would pass the first test above while being useless. So the question is
    scoped to the files the branch actually changes.
    """
    (repo / "src" / "thing.py").write_text(ALREADY_FLAT, encoding="utf-8")
    (repo / "workbench" / "scratch.py").write_text(WRAPPED, encoding="utf-8")

    out = formatter_stability(repo, ["src/thing.py"])

    assert out.state == "stable", (
        "a file outside the changed set made this refuse; the check is reading "
        "the tree rather than the branch"
    )


def test_a_formatter_that_cannot_run_is_could_not_tell_not_stable(repo, monkeypatch):
    """HOARE'S THREE STATES, in the one place collapsing them costs a signature.

    An instrument that did not run has not told me the branch is clean. The
    whole incident being repaired is a green that meant less than it looked
    like; answering 'stable' here would build a second one.
    """
    (repo / "src" / "thing.py").write_text(ALREADY_FLAT, encoding="utf-8")

    def explode(*_a, **_k):
        raise OSError("ruff is not installed")

    monkeypatch.setattr(subprocess, "run", explode)

    out = formatter_stability(repo, ["src/thing.py"])

    assert out.state == "cannot-tell"
    assert out.unstable == ()
    assert "could not" in out.reason.lower() or "cannot" in out.reason.lower()


def test_a_branch_with_no_python_files_is_stable(repo):
    """A documentation-only branch has nothing the formatter can move."""
    (repo / "notes.md").write_text("# hello\n", encoding="utf-8")

    out = formatter_stability(repo, ["notes.md"])

    assert out.state == "stable"


def test_it_names_every_unstable_file_rather_than_just_the_first(repo):
    """The remedy is per-file, so a verdict naming one of three sends someone
    back twice for no reason."""
    (repo / "src" / "one.py").write_text(WRAPPED, encoding="utf-8")
    (repo / "src" / "two.py").write_text(WRAPPED, encoding="utf-8")
    (repo / "src" / "ok.py").write_text(ALREADY_FLAT, encoding="utf-8")

    out = formatter_stability(repo, ["src/one.py", "src/two.py", "src/ok.py"])

    assert out.state == "unstable"
    assert set(out.unstable) == {"src/one.py", "src/two.py"}


def test_a_path_that_does_not_exist_is_not_reported_as_unstable(repo):
    """A deleted file is in the branch's changed set and has nothing to format.
    Reporting it as unstable would send someone to run a formatter over a file
    that is gone."""
    (repo / "src" / "thing.py").write_text(ALREADY_FLAT, encoding="utf-8")

    out = formatter_stability(repo, ["src/thing.py", "src/deleted.py"])

    assert out.state == "stable"
    assert "src/deleted.py" not in out.unstable
