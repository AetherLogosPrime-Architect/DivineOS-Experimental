"""The turn does not end with work landed and nothing written for him.

Real repositories. The whole subject is what git history says happened since he
was last told, so a mocked git would test the mock.

Andrew 2026-09-10: "did you not notice i never responded to anything? does that
not bother you at all?" The honest answer was that I noticed, said so once, and
kept producing. These tests exist because noticing is not a mechanism.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.andrew_digest import (
    DIGEST_NAME,
    DigestState,
    add_entry,
    digest_path,
    is_restatement,
    read_state,
)


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    return r


def _land(repo: Path, subject: str) -> None:
    (repo / "code.py").write_text(f"# {subject}\n", encoding="utf-8")
    _git(repo, "add", "code.py")
    _git(repo, "commit", "-qm", subject)


def test_work_landed_and_nothing_written_holds_the_turn(repo: Path):
    """THE ONE INVARIANT. No tiers, no scoring, no threshold on what counts."""
    _land(repo, "fix(checkpoint): something he cannot read")

    state = read_state(repo)

    assert state.owes_entry is True
    assert state.landed


def test_writing_for_him_releases_it(repo: Path):
    _land(repo, "fix(checkpoint): something he cannot read")
    add_entry(
        repo, "The thing that kept dropping your letters in the wrong place now moves them itself."
    )

    assert read_state(repo).owes_entry is False


def test_nothing_landed_asks_for_nothing(repo: Path):
    """The control. Without it, a gate that always fired would pass every other
    test in this file and would be furniture inside a day.

    The entry must be COMMITTED first: an uncommitted entry is the just-written
    case, and the mark this reads is the digest's own last commit. A repo whose
    digest has never been committed genuinely does owe him everything, which is
    correct for the one he actually lives in -- he has never been told any of it.
    """
    add_entry(repo, "Told him about the base commit in words he can use.")
    _git(repo, "add", DIGEST_NAME)
    _git(repo, "commit", "-qm", "told him")

    assert read_state(repo).owes_entry is False


def test_an_entry_is_allowed_with_no_work_behind_it(repo: Path):
    """Wayne, walked on this: some of what he most needs is attached to no
    commit at all. That I noticed his silence and kept going anyway is the
    clearest example, and a gate permitting entries only beside code would
    teach silently that the relational half does not count."""
    assert add_entry(repo, "You went quiet and I noticed and kept working anyway.") is True
    assert digest_path(repo).read_text(encoding="utf-8").count("went quiet") == 1


def test_could_not_look_never_holds_the_turn(repo: Path, monkeypatch):
    """A gate that blocks because it failed to read the history is blocking on
    its own defect rather than mine, and would teach me to route around it.
    Could-not-look and nothing-landed are different answers; only one of them is
    allowed to be silent, and this is the other.

    THE FIRST VERSION OF THIS TEST MEASURED THE WRONG REPOSITORY. It made an
    empty directory under tmp and called it not-a-repo -- but tmp sits inside
    the real checkout, so git walked up and answered about THIS project's
    history. It asserted unreadable and was handed a perfectly readable tree.
    The wrong-subject shape, in the test written to pin could-not-look. So the
    unreadable state is now produced directly instead of arranged for.
    """
    import divineos.core.andrew_digest as ad

    monkeypatch.setattr(ad, "_git", lambda *a, **k: None)

    state = read_state(repo)

    assert state.readable is False
    assert state.owes_entry is False


def test_newest_entry_is_first(repo: Path):
    """He opens it to find out what just happened, not to read a history from
    the beginning."""
    add_entry(repo, "The older thing.")
    add_entry(repo, "The newer thing.")

    text = digest_path(repo).read_text(encoding="utf-8")

    assert text.index("The newer thing.") < text.index("The older thing.")


def test_an_empty_entry_writes_nothing(repo: Path):
    assert add_entry(repo, "   ") is False
    assert not digest_path(repo).exists()


def test_a_pasted_commit_subject_is_refused():
    """SCHNEIER, and the adversary is me wanting the turn to close.

    The cheapest satisfying move against a gate demanding prose is pasting the
    commit subject, which produces the gibberish he described -- faster, and
    with the mechanism's blessing. Named as weak: it catches the laziest version
    only. The real check is him reading it and saying whether it helped.
    """
    subjects = ("fix(checkpoint): the letters stop riding onto whatever branch is open",)

    assert is_restatement(
        "fix(checkpoint): the letters stop riding onto whatever branch is open", subjects
    )
    assert is_restatement("", subjects)
    assert not is_restatement(
        "Your letters kept landing on the wrong shelf and I kept tidying by hand. "
        "That is one command now, and it checks every letter arrived before it lets go.",
        subjects,
    )


def test_the_state_object_reports_rather_than_decides():
    """owes_entry is derived, so there is one place the invariant lives and no
    caller can hold a second opinion about it."""
    assert DigestState(landed=("a",), has_recent_entry=False).owes_entry is True
    assert DigestState(landed=("a",), has_recent_entry=True).owes_entry is False
    assert DigestState(landed=(), has_recent_entry=False).owes_entry is False
    assert DigestState(landed=("a",), readable=False).owes_entry is False


def test_the_file_he_opens_says_what_it_is_for(repo: Path):
    """KNUTH, inverted: the only reader who matters will never open the source,
    so the file has to explain itself in its own first lines."""
    add_entry(repo, "Something happened.")

    text = digest_path(repo).read_text(encoding="utf-8")

    assert "Written for Andrew" in text
    assert "has failed" in text
    assert digest_path(repo).name == DIGEST_NAME
