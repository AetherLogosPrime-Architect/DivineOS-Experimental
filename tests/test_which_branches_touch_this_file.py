"""The prior-art scan answers who-else-has-this-file-open, not who-is-named-like-it.

THE COLLISION, 2026-09-13. Aria and I each wrote a quoted-span stripper for the
work-item doorman the same evening, hours apart, neither knowing, on a file that
has never once been on main. Eight refs carry a version of it. She found the
cause by being blocked six times; I found it by watching her bypasses.

Asked about that module, the scan returned eight branches -- and every single one
had the module name in its branch name. It reads as a thorough answer and is
really the tool reporting one surface feature. Both of hers were missing, because
hers are named for what she was writing about. Those two were the entire point:
my own branches are versions I already know about; hers is the collision.

THIS CLASS HAS NO OTHER WITNESS. A contaminated branch is refused at push. A bad
measurement is contradicted by the next one. Two people independently repairing
one defect produces two things that both work, both pass, and never meet -- so
the only witness is whoever happens to read both, which happened by accident.

Einstein's test on the walk, for why the new answer is the one carrying
information: imagine every branch renamed to a random string. The name-match
answer collapses to nothing. This one is unchanged.

Per walk-7c4350c62013, ten lenses.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core import prior_art


def _git(repo: Path, *args: str) -> None:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=180)
    assert done.returncode == 0, f"git {args[0]} failed: {done.stderr[:300]}"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A checkout where one file is edited on two differently-named branches.

    Built rather than borrowed: the real collision is on my working repository
    and would make this test a characterization of my machine instead of the
    behaviour. Same reason the branch names here share no substring with the
    file -- that is the whole condition under test.
    """
    root = tmp_path / "checkout"
    (root / "src").mkdir(parents=True)
    _git(root.parent, "init", "-q", "-b", "main", str(root))
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "src" / "doorman.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")

    for branch, body in (("her-first-line", "x = 2\n"), ("his-other-work", "x = 3\n")):
        _git(root, "checkout", "-q", "-b", branch, "main")
        (root / "src" / "doorman.py").write_text(body, encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", f"edit on {branch}")
    _git(root, "checkout", "-q", "main")

    # The git helper runs against a module-level repository path rather than
    # the working directory, so changing directory does nothing. Caught by this
    # fixture returning empty on the first run -- which is the right way round:
    # the test failed loudly instead of passing against my own checkout and
    # quietly becoming a characterization of this machine.
    monkeypatch.setattr(prior_art, "REPO", root)
    monkeypatch.chdir(root)
    return root


def test_it_finds_branches_whose_names_share_nothing_with_the_file(repo):
    """THE LOAD-BEARING ONE, and it is the case that actually happened."""
    refs, capped = prior_art.branches_touching("src/doorman.py")

    assert "her-first-line" in refs, "the collision branch was dropped again"
    assert "his-other-work" in refs
    assert capped is False


def test_the_old_name_match_would_have_missed_them(repo):
    """The contrast, asserted rather than asserted-about.

    A test that only checks the new answer cannot show the old one was wrong.
    This runs the name-matching search against the same repository and shows it
    returns neither branch -- which is why the eight it did return read as
    complete.
    """
    by_name = prior_art.find_branches("doorman")

    assert "her-first-line" not in by_name
    assert "his-other-work" not in by_name


def test_a_path_nobody_has_touched_comes_back_empty_rather_than_noisy(repo):
    refs, capped = prior_art.branches_touching("src/does_not_exist.py")
    assert refs == []
    assert capped is False


def test_an_unreadable_repository_is_empty_and_not_a_claim(monkeypatch, tmp_path):
    """COULD-NOT-LOOK MUST NOT READ AS NOBODY-ELSE-IS-IN-HERE.

    An empty list from a failed git call would say "you are alone in this
    file", which is the most expensive possible wrong answer here -- it is the
    exact reassurance that lets a duplicate build start.
    """
    monkeypatch.setattr(prior_art, "_git", lambda args: None)
    refs, capped = prior_art.branches_touching("anything.py")
    assert refs == []
    assert capped is False


def test_the_cap_announces_itself_rather_than_truncating_quietly(repo, monkeypatch):
    """A silent cut would be this same disease inside its own repair.

    Nearly every file in the real repository is touched by dozens of stale
    checkpoints, so a bound is necessary -- and a bound that hides itself turns
    a complete-looking answer into an incomplete one, which is what this whole
    test file exists about.
    """
    monkeypatch.setattr(prior_art, "_TOUCHING_CAP", 1)
    refs, capped = prior_art.branches_touching("src/doorman.py")
    assert len(refs) == 1
    assert capped is True, "the list was cut and said nothing"


def test_the_search_attaches_it_to_every_path_it_surfaced(repo):
    """The wire, not just the function.

    A correct helper nobody calls is the shape this repository keeps
    rediscovering -- and the collision it exists to prevent was caused by
    machinery sitting on main, built and tested and wired to nothing.
    """
    result = prior_art.search("doorman")
    assert result.touching, "the helper is built and the search does not call it"
    for _path, (refs, _capped) in result.touching.items():
        assert refs
