"""A review anchor must distinguish "the code moved" from "an artifact moved".

THE TRAP THIS CLOSES, measured 2026-09-03 on a live branch:

A branch behind main cannot merge until it is caught up. Catching up rewrites
the committed capability catalogue, which is generated. That rewrite lands in
the branch's cumulative diff, which moves the patch-id, which invalidates the
external reviewer's confirm -- on a branch where not one reviewed line changed.

So the remedy invalidated the licence: the only way to make the branch
mergeable was the thing that withdrew permission to merge it.

Aletheia named the class that morning, about something else: "a committed
artifact that is not a function of the code will break every anchor bound to
the code." This is that, arriving as a live instance hours later.

WHAT IS ASSERTED HERE is the discrimination, not that a number comes back:
the full anchor MUST move when an excluded artifact changes (otherwise the
exclusion is silently widening what counts as unchanged), and the code-only
anchor MUST NOT. A test that only checked the second half would pass on a
function that ignored everything.
"""

from __future__ import annotations

import subprocess

import pytest

from divineos.cli.audit_commands import _ANCHOR_EXCLUDED_PATHS, compute_branch_patch_id


def _git(*args: str, cwd) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """A repo with a main, a branch, and one excluded-path artifact."""
    r = tmp_path / "r"
    r.mkdir()
    _git("init", "-q", "-b", "main", cwd=r)
    _git("config", "user.email", "t@t", cwd=r)
    _git("config", "user.name", "t", cwd=r)
    (r / "docs").mkdir()
    (r / "docs" / "CAPABILITY_CATALOG.md").write_text("generated: v1\n", encoding="utf-8")
    (r / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git("add", "-A", cwd=r)
    _git("commit", "-qm", "base", cwd=r)
    _git("checkout", "-q", "-b", "feature", cwd=r)
    (r / "code.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    _git("add", "-A", cwd=r)
    _git("commit", "-qm", "the reviewed change", cwd=r)
    return r


def test_artifact_only_change_moves_the_full_anchor_and_not_the_code_anchor(repo, monkeypatch):
    monkeypatch.chdir(repo)

    before_full = compute_branch_patch_id("feature", main_ref="main")
    before_code = compute_branch_patch_id(
        "feature", main_ref="main", exclude=_ANCHOR_EXCLUDED_PATHS
    )
    assert before_full and before_code

    # The catch-up: the generated artifact is rewritten on the branch. No
    # reviewed line is touched.
    (repo / "docs" / "CAPABILITY_CATALOG.md").write_text("generated: v2\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "catch-up regenerates the catalogue", cwd=repo)

    after_full = compute_branch_patch_id("feature", main_ref="main")
    after_code = compute_branch_patch_id("feature", main_ref="main", exclude=_ANCHOR_EXCLUDED_PATHS)

    assert after_full != before_full, (
        "the strict anchor must still notice an artifact change -- if it does not, "
        "the exclusion has silently widened what counts as unchanged"
    )
    assert after_code == before_code, (
        "the code-only anchor must survive a catch-up that touched only artifacts; "
        "this is the whole point of the reading"
    )


def test_a_real_code_change_moves_both_anchors(repo, monkeypatch):
    """The exclusion must not hide an actual change to reviewed code."""
    monkeypatch.chdir(repo)

    before_code = compute_branch_patch_id(
        "feature", main_ref="main", exclude=_ANCHOR_EXCLUDED_PATHS
    )
    (repo / "code.py").write_text("x = 1\ny = 2\nz = 3\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "a real change to the reviewed code", cwd=repo)
    after_code = compute_branch_patch_id("feature", main_ref="main", exclude=_ANCHOR_EXCLUDED_PATHS)

    assert after_code != before_code, (
        "excluding artifacts must never make a genuine code change invisible"
    )


def test_default_is_the_strict_anchor(repo, monkeypatch):
    """No exclusion unless asked for by name -- the loose reading is opt-in."""
    monkeypatch.chdir(repo)
    (repo / "docs" / "CAPABILITY_CATALOG.md").write_text("generated: v9\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "artifact only", cwd=repo)

    strict = compute_branch_patch_id("feature", main_ref="main")
    loose = compute_branch_patch_id("feature", main_ref="main", exclude=_ANCHOR_EXCLUDED_PATHS)
    assert strict != loose, (
        "the default must be the strict reading; a caller that wants the looser "
        "one has to name it, so no gate silently inherits it"
    )
