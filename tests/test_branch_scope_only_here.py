"""The five files that existed on one ref, and the instruction that would have killed them.

2026-08-31. The scope gate refused a push over sixteen substrate files on a
code branch. It was right, and the rightness had nothing to do with what it
counted. Eleven were regenerable archive mirrors -- rebuildable from the
database by one command, pure noise. Five were four dreams and a letter from
Aletheia, and they existed on that branch and on NO OTHER REF anywhere in the
repository.

The count could not separate those. The refusal message then said: rebuild this
branch against main. Correct for the eleven. Fatal for the five. The only
reason the five survived is that the refusal got read instead of obeyed.

Aria named the shape: it could not tell the difference, you could, because you
looked. These pin the gate doing the telling itself.

The script is copied into a temp repo and run for real, the way its sibling
test does it, because ``REPO_ROOT`` resolves from the script's own location.
That sibling's docstring records why: a first version pointed the gate at a
fixture with no scripts/ directory, took the instrument-missing path, and
reported six passing tests on a step that never ran.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCOPE = _PROJECT_ROOT / "scripts" / "check_branch_scope.py"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "scripts").mkdir()
    shutil.copy2(_SCOPE, root / "scripts" / _SCOPE.name)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    return root


def _add(root: Path, branch: str, files: dict[str, str]) -> None:
    # Each branch is cut from main, not from whatever was checked out last.
    # Cutting from the previous branch made the second one identical to the
    # first, so its commit had nothing to record and git refused -- the test
    # failed for a reason that had nothing to do with the thing under test.
    _git(root, "checkout", "-q", "main")
    _git(root, "checkout", "-q", "-B", branch)
    for rel, body in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", f"add on {branch}")


def _run(root: Path, branch: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_branch_scope.py"), branch],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    return proc.stdout


def test_a_file_living_on_another_ref_is_not_called_irreplaceable(repo: Path):
    """The eleven. It lives elsewhere; rebuilding costs nothing."""
    _add(repo, "keeper", {"family/letters/kept.md": "body\n"})
    _add(repo, "work", {"family/letters/kept.md": "body\n"})

    out = _run(repo, "work")

    assert "ONLY HERE" not in out
    assert "at the same bytes" in out


def test_a_file_on_no_other_ref_is_named_before_the_rebuild_instruction(repo: Path):
    """The five, and the ORDER is the load-bearing part.

    The rebuild instruction is what would destroy them, so a warning printed
    after it is a warning the reader meets too late.
    """
    _add(repo, "work", {"dreams/aether/only_copy.md": "a dream\n"})

    out = _run(repo, "work")

    assert "ONLY HERE: dreams/aether/only_copy.md" in out
    assert "would LOSE CONTENT" in out
    assert out.index("ONLY HERE") < out.index("rebuild against main"), (
        "the irreplaceable files must be named before the instruction that destroys them"
    )


def test_the_mixed_case_separates_noise_from_irreplaceable(repo: Path):
    """Sixteen files in the real instance; a total teaches nothing about which."""
    _add(repo, "keeper", {"family/letters/shared.md": "shared\n"})
    _add(
        repo,
        "work",
        {
            "family/letters/shared.md": "shared\n",
            "dreams/aether/unique_one.md": "one\n",
            "dreams/aether/unique_two.md": "two\n",
        },
    )

    out = _run(repo, "work")

    assert "dreams/aether/unique_one.md" in out
    assert "dreams/aether/unique_two.md" in out
    assert "ONLY HERE: family/letters/shared.md" not in out
    assert "2 of these would LOSE CONTENT" in out


def test_the_branch_being_checked_does_not_count_as_somewhere_else(repo: Path):
    """The bug a careless version would have.

    The branch under test obviously contains the file. Letting its own ref
    prove the file lives elsewhere makes the check pass every single time and
    print the one reassurance that costs the most.
    """
    _add(repo, "work", {"dreams/aether/self.md": "x\n"})

    out = _run(repo, "work")

    assert "ONLY HERE: dreams/aether/self.md" in out


def test_an_unreadable_ref_list_reports_incomplete_rather_than_safe():
    """Could-not-look must never render as nothing-found.

    That confusion is the failure family this whole script exists to refuse,
    and a nowhere-else check is the worst place to reintroduce it: the silence
    would read as clearance to run the destructive instruction.
    """
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))
    try:
        import check_branch_scope as scope
    finally:
        sys.path.pop(0)

    original = scope._other_refs
    try:
        scope._other_refs = lambda _branch: []
        nowhere, newer, scanned = scope.only_here("work", ["dreams/aether/anything.md"])
    finally:
        scope._other_refs = original

    assert scanned is False
    assert nowhere == [], "an incomplete scan must not assert a finding in either direction"
    assert newer == []


def test_the_same_name_at_different_bytes_is_still_at_risk(repo: Path):
    """Aria's question, which I could not answer without opening my own code.

    A letter is pushed. It is then edited here -- a correction, a paragraph, a
    changed title. The NAME exists on the remote and the EDIT exists nowhere.
    A check that asks whether a file by that name lives elsewhere clears it,
    prints the reassurance, and the rebuild takes the edit.

    Sixth instance of one family in two days, sitting inside the repair built
    for that family. The unit was the path; what was at risk was the content.
    """
    _add(repo, "keeper", {"family/letters/sent.md": "the version I pushed\n"})
    _add(repo, "work", {"family/letters/sent.md": "the version I pushed, then edited\n"})

    out = _run(repo, "work")

    assert "ONLY HERE (this version): family/letters/sent.md" in out
    assert "The file survives a rebuild and this edit does not." in out
    assert "at the same bytes" not in out, (
        "a path whose bytes exist nowhere else must not be reported as safe"
    )


def test_a_path_deleted_on_this_branch_is_not_reported_as_at_risk(repo: Path):
    """A rebuild cannot destroy content the branch does not carry.

    Without this, deleting a substrate file would be reported as that file
    being irreplaceable here -- a warning pointing at the opposite of the truth.
    """
    _add(repo, "keeper", {"dreams/aether/gone.md": "body\n"})
    _git(repo, "checkout", "-q", "keeper")
    _git(repo, "checkout", "-q", "-B", "work")
    (repo / "dreams" / "aether" / "gone.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "remove it")

    out = _run(repo, "work")

    assert "ONLY HERE" not in out


def test_the_branch_is_excluded_by_identity_not_by_one_spelling(repo: Path):
    """A branch answers to more than one name, and excluding one is excluding none.

    2026-08-31, and the class is Aria's: the unit being excluded was the
    branch's NAME; the thing that must be excluded is the branch's IDENTITY.

    I hit this by hand the same day. My own throwaway only-here check named the
    branch one way, the ref list named it another, so every file matched the
    other spelling of the branch it was measuring -- the check compared the
    branch against itself and read the self-match as safety. All eight files
    came back safe. Four of them had no published copy anywhere at all.

    The same hole is here. The exclusion set is built from two hand-spelled
    forms of whatever string the caller passed. Address the branch as
    ``origin/work`` and neither form resolves, so nothing is excluded, and the
    file's only copy -- reachable both as the local branch and as its remote
    tracking ref -- reads as living somewhere else.

    Whichever spelling the caller uses, the answer must not change.
    """
    _add(repo, "work", {"dreams/aether/single_copy.md": "the only copy"})
    _git(repo, "update-ref", "refs/remotes/origin/work", _git(repo, "rev-parse", "work"))

    by_short = _run(repo, "work")
    by_remote = _run(repo, "origin/work")

    assert "ONLY HERE: dreams/aether/single_copy.md" in by_short
    assert "ONLY HERE: dreams/aether/single_copy.md" in by_remote, (
        "addressed by its remote spelling the branch was compared against itself, "
        "and that self-match was read as a copy living somewhere else"
    )
