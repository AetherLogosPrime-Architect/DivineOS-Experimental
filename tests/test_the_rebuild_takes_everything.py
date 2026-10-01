"""The rebuild must take every code change, and prove it took them.

WHY THIS EXISTS. The checkpoint auto-commit fires mid-work on purpose and
already splits personal writing from code. It is not the fault. The fault is
that my work then lives in two commits -- one the net made, one I authored --
and when a branch needs rebuilding I reach for the one with my name on it and
leave the other behind. Sixty-one lines nearly went that way on 2026-09-12,
and my hand-rolled check said it was fine because I had used a command that
exits zero whether or not there are differences.

THE LOAD-BEARING TEST IS THE ONE WHERE VERIFICATION FAILS. A verifier that
has never returned "refused" against a genuinely different tree is
indistinguishable from one that always says yes -- which is exactly what I
shipped by hand, six times, and got away with five.

These run against a real temporary repository rather than a mocked git,
because the fault being fixed was a misread of what a real git command
returns, and a fake would have agreed with my misreading.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.branch_replant import (
    SUBSTRATE_PREFIXES,
    code_changes,
    render,
    replant,
    verify_identical,
)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    """A real repository shaped like the failure: code split across two
    commits, one of them an auto-commit, with personal writing alongside."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    _write(r, "src/thing.py", "original\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "base")

    _git(r, "checkout", "-q", "-b", "work")
    # The net's half: part of my edit, committed by something that is not me.
    _write(r, "src/thing.py", "original\nhalf one\n")
    _write(r, "exploration/a_letter.md", "personal writing\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "auto-commit: work in progress")
    # My half, under my own message -- the one I would reach for.
    _write(r, "src/thing.py", "original\nhalf one\nhalf two\n")
    _write(r, "src/other.py", "mine\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "the commit I would reach for")
    return r


def test_code_changes_excludes_personal_writing_and_keeps_everything_else(repo):
    paths = code_changes(repo, "main", "work")
    assert paths is not None
    assert set(paths) == {"src/thing.py", "src/other.py"}
    assert not any(p.startswith(SUBSTRATE_PREFIXES) for p in paths)


def test_the_rebuild_carries_the_half_i_would_have_left_behind(repo):
    """The whole point. Taking my commit alone loses the net's half."""
    result = replant(repo, source="work", base="main", target="rebuilt")
    assert result.state == "planted", render(result)
    assert (repo / "src/thing.py").read_text(encoding="utf-8") == "original\nhalf one\nhalf two\n"
    assert not (repo / "exploration/a_letter.md").exists()


def test_the_source_branch_is_left_exactly_where_it_was(repo):
    before = _git(repo, "rev-parse", "work")
    replant(repo, source="work", base="main", target="rebuilt")
    assert _git(repo, "rev-parse", "work") == before


def test_the_verifier_actually_refuses_when_a_file_differs(repo):
    """THE LOAD-BEARING ONE.

    A verifier that has never said no against a genuinely different tree is
    indistinguishable from one that always says yes -- which is what I shipped
    by hand and got away with five times out of six.
    """
    _git(repo, "checkout", "-q", "-b", "rebuilt", "main")
    # Take only ONE of the two changed files: the shape of a lossy rebuild.
    _git(repo, "checkout", "work", "--", "src/other.py")
    _git(repo, "commit", "-q", "-m", "partial rebuild")

    result = verify_identical(repo, "work", "rebuilt", ["src/thing.py", "src/other.py"])
    assert result.state == "refused"
    assert "src/thing.py" in result.differing
    assert "work would have been lost" in result.reason


def test_a_refusal_to_resolve_is_not_a_refusal_of_the_code(repo):
    """could-not-check must never read as either verdict."""
    result = verify_identical(repo, "no-such-branch", "main", ["src/thing.py"])
    assert result.state == "could-not-check"
    assert result.state != "refused"
    assert "nothing was compared" in result.reason


def test_it_refuses_rather_than_overwriting_an_existing_branch(repo):
    _git(repo, "branch", "rebuilt", "main")
    result = replant(repo, source="work", base="main", target="rebuilt")
    assert result.state == "refused"
    assert "already exists" in result.reason


def test_the_rendered_could_not_check_cannot_be_read_as_success(repo):
    result = verify_identical(repo, "no-such-branch", "main", ["src/thing.py"])
    text = render(result)
    assert "COULD NOT CHECK" in text
    assert "Do not push on this" in text


def test_the_push_gate_has_one_definition_of_substrate_and_refuses_without_it():
    """THERE IS ONLY ONE COPY NOW, and the guard had to change shape with it.

    This used to parse a SECOND copy of the list out of the gate script and
    compare the two, because the list genuinely existed twice: the gate is
    stdlib-only so it could still run with the package broken. That
    duplication drifted exactly as its own docstring predicted -- one word,
    two definitions, three of four entries disagreeing, and the only symptom
    was a branch that could not be pushed and could not be fixed by the
    component that made it.

    The duplication was then ended: the gate imports the list. So this test
    started parsing a literal that no longer exists and died with an index
    error -- a guard outliving its subject and reporting a crash where the
    honest answer is that the thing it watched for is gone.

    The equality is now carried by test_one_word_one_definition_of_substrate,
    which compares the imported OBJECTS rather than parsed text and cannot go
    stale this way. What nothing else asserts, and what this keeps, is that the
    gate REFUSES when it cannot reach the definition. A silent fallback list
    would be the same duplication wearing a different coat, and it would drift
    in exactly the same silence.
    """
    script = Path("scripts/check_branch_scope.py").read_text(encoding="utf-8")

    assert "from divineos.core.substrate_paths import LOCAL_SUBSTRATE_PREFIXES" in script, (
        "the push gate no longer imports the shared list, so a second "
        "definition of substrate has come back"
    )
    assert "CANNOT CLASSIFY" in script, (
        "the gate must say it cannot classify when the definition is "
        "unreachable; could-not-look is not a clean branch"
    )

    # The control. Without it this passes on a rebuild whose own list is empty,
    # which would make every assertion above true and meaningless.
    assert SUBSTRATE_PREFIXES, "the rebuild's own substrate list is empty"
