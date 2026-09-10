"""The checkpoint keeps substrate off the code branch entirely.

Andrew 2026-09-10, after it swept a fourth time in one afternoon and the manual
rebuild nearly ate a fix: "fix the checkpoint sweep."

The half declared in substrate_paths.py on 2026-08-27 -- "substrate commits go
to a named branch by plumbing, never by checkout" -- and left open with the
reason written down rather than hidden: routing the letters away leaves them
dirty in the code branch's tree, so every later checkpoint finds them again.

What closes it is that the repo copy is a MIRROR of a channel living outside
the repo, and that the retarget writes nothing when the content has not
changed. Dirty-and-harmless rather than dirty-and-accumulating.

Real repositories throughout. The change is entirely about which ref a commit
lands on, so a mocked git would test the mock.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import _retarget_substrate


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "code")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "code.py")
    _git(r, "commit", "-qm", "base")
    _git(r, "branch", "aria/substrate")
    return r


def _letter(repo: Path, name: str, body: str) -> str:
    d = repo / "family" / "letters"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body, encoding="utf-8")
    return f"family/letters/{name}"


def test_the_letter_reaches_its_branch_and_never_the_code_branch(repo: Path):
    rel = _letter(repo, "aether-to-aria-2026-09-10-one.md", "hello\n")
    tip_before = _git(repo, "rev-parse", "code")

    assert _retarget_substrate(repo, [rel], "extract") is True

    assert _git(repo, "rev-parse", "code") == tip_before
    assert rel not in _git(repo, "ls-tree", "-r", "--name-only", "code")
    assert rel in _git(repo, "ls-tree", "-r", "--name-only", "aria/substrate")
    assert _git(repo, "show", f"aria/substrate:{rel}") == "hello"


def test_the_letter_survives_a_pruning_garbage_collection(repo: Path):
    """THE SAFETY PROPERTY. Aether named the shortcut that must not be taken:
    dropping the checkpoint commits and trusting the reflog risks the only
    copies in the tree. A gc that prunes everything unreachable must still
    leave the letter readable."""
    rel = _letter(repo, "aether-to-aria-2026-09-10-two.md", "keep me\n")
    assert _retarget_substrate(repo, [rel], "extract") is True

    _git(repo, "reflog", "expire", "--expire=now", "--all")
    _git(repo, "gc", "--prune=now", "-q")

    assert _git(repo, "show", f"aria/substrate:{rel}") == "keep me"


def test_finding_the_same_letters_again_writes_nothing(repo: Path):
    """IDEMPOTENCE is what makes the leftover dirt harmless, and it is the
    objection that stopped this being built. The files stay on disk, so every
    later checkpoint finds them -- finding them must cost nothing."""
    rel = _letter(repo, "aether-to-aria-2026-09-10-three.md", "same\n")
    assert _retarget_substrate(repo, [rel], "extract") is True
    after_first = _git(repo, "rev-parse", "aria/substrate")

    assert _retarget_substrate(repo, [rel], "sleep") is True

    assert _git(repo, "rev-parse", "aria/substrate") == after_first


def test_a_missing_substrate_branch_refuses_rather_than_falling_back(repo: Path):
    """THE FAIL DIRECTION, asserted rather than assumed.

    Committing to HEAD when the branch cannot be resolved is exactly the defect
    under repair, so refusal must return False and leave the caller to the old
    visible path -- never a quiet commit here.
    """
    _git(repo, "branch", "-D", "aria/substrate")
    rel = _letter(repo, "aether-to-aria-2026-09-10-four.md", "orphan\n")
    tip_before = _git(repo, "rev-parse", "code")

    assert _retarget_substrate(repo, [rel], "extract") is False

    assert _git(repo, "rev-parse", "code") == tip_before
    assert rel not in _git(repo, "ls-tree", "-r", "--name-only", "code")


def test_the_working_tree_and_head_are_untouched(repo: Path):
    """The control. Without it the tests above would pass on a function that
    had quietly checked the substrate branch out and back."""
    rel = _letter(repo, "aether-to-aria-2026-09-10-five.md", "letter\n")
    (repo / "code.py").write_text("x = 99\n", encoding="utf-8")

    assert _retarget_substrate(repo, [rel], "extract") is True

    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "code"
    assert (repo / "code.py").read_text(encoding="utf-8") == "x = 99\n"
    assert (repo / rel).read_text(encoding="utf-8") == "letter\n"


def test_the_checkpoint_itself_routes_the_letters_away(repo: Path, tmp_path: Path):
    """THE WIRING, not the unit -- and I only wrote this because sabotage said to.

    Disabling the call inside the checkpoint killed none of the tests above,
    because every one of them invokes the routing directly. A function that is
    correct and never reached is the exact shape this whole change exists to
    repair, and I had just rebuilt it in the tests for the repair.

    Third time today an instrument of mine answered accurately about a narrower
    subject than the question. So this one drives the real entry point.
    """
    from divineos.core.auto_commit import auto_commit_substrate
    from divineos.core.uncommitted_work_check import ExternalChannel

    source = tmp_path / "shared"
    source.mkdir()
    channels = (
        ExternalChannel(
            name="letters",
            source=source,
            repo_mirror=Path("family/letters"),
            pattern="*.md",
        ),
    )

    rel = _letter(repo, "aether-to-aria-2026-09-10-six.md", "through the front door\n")
    (repo / "code.py").write_text("x = 3\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert rel not in _git(repo, "ls-tree", "-r", "--name-only", "code")
    assert _git(repo, "show", f"aria/substrate:{rel}") == "through the front door"
    assert _git(repo, "show", "code:code.py") == "x = 3"
