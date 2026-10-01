"""Adding substrate to a branch and removing it from everywhere are opposite acts.

Written 2026-09-18, against a defect recorded before it was repaired
(knowledge fa405b09).

THE DEFECT. The branch-scope check lists paths a branch CHANGED, not paths it
CARRIES, so a deletion counted as substrate-on-this-branch exactly like an
addition -- and the refusal said only "substrate file(s) on this branch" for
both. Two hazards in one sentence:

  * this branch would ADD substrate where it does not belong, and
  * this branch would REMOVE substrate from everywhere on merge.

Both deserve refusal. They do not deserve the same words, because the remedies
differ: an addition is rebuilt away, a removal has to be confirmed as intended.

WHAT IT COST. A branch deleting a tracked secret-shaped file reached an auditor
inside an eighty-six file diff, and the only thing telling her to read that
deletion as the repair rather than a loss was a letter written by hand. A guard
whose output needs a human escort is making work instead of saving it.

THE REPAIR IS NOT A FILTER, and this is the half the tests below guard hardest.
Dropping deletions from the count clears the refusal and is the permitting
direction: it would let a branch quietly delete substrate from the main line,
which is the worse failure, because an addition stays visible in a diff forever
and a removal looks like nothing once it lands. The refusal condition is
untouched. Only the message learns to say which way it found.

SIBLING: test_branch_scope_sees_deleted_but_present_on_disk.py covers the other
deletion defect in this same scan -- a path deleted on the branch and still on
disk. That one is about what the scan can SEE; this one is about what it SAYS.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Imported by path the way the sibling scope tests do it. A spec_from_file_location
# load fails here: the script defines a frozen dataclass, and dataclasses resolves
# annotations through sys.modules, which a module built by hand is not in yet.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    import check_branch_scope as scope
finally:
    sys.path.pop(0)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real repository with a real substrate file.

    Not a mocked git: a fake --name-status would test this file's idea of the
    format rather than git's, and the format is the whole risk here.

    The module pins ``cwd=REPO_ROOT`` on every git call, so chdir alone leaves
    it querying the real repository -- where these branches do not exist and
    every answer comes back empty. Empty then reads as the classifier finding
    nothing, which is could-not-look wearing the clothes of nothing-there. The
    constant is repointed for the duration, and the vacuity control below is
    what caught this: it was the only test that passed, and it passed because
    the answer was empty for the wrong reason.
    """
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    letters = r / "family" / "letters"
    letters.mkdir(parents=True)
    (letters / "kept.md").write_text("a letter that exists on main\n", encoding="utf-8")
    (r / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "main")
    monkeypatch.setattr(scope, "REPO_ROOT", r)
    monkeypatch.chdir(r)
    return r


def test_a_branch_that_deletes_substrate_reports_removes(repo: Path) -> None:
    """The live case. The branch takes a substrate file off the main line."""
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "kept.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "untrack it")

    directions = scope.substrate_directions("topic", "main")
    assert directions.get("family/letters/kept.md") == "REMOVES", (
        "A deletion must be named as one. Reported as a bare substrate path it "
        "reads as contamination, which is the opposite of what it is."
    )


def test_a_branch_that_adds_substrate_reports_adds(repo: Path) -> None:
    """The other hazard, which must keep its own word."""
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "new.md").write_text("swept in\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "sweep")

    directions = scope.substrate_directions("topic", "main")
    assert directions.get("family/letters/new.md") == "ADDS"


def test_a_rewrite_is_neither(repo: Path) -> None:
    """Modification is a third state and collapsing it into either is a lie."""
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "kept.md").write_text("edited\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "edit")

    directions = scope.substrate_directions("topic", "main")
    assert directions.get("family/letters/kept.md") == "REWRITES"


def test_a_renamed_letter_is_classified_by_the_name_it_has_now(repo: Path) -> None:
    """Renames carry two names and would be mangled by a naive split.

    Long hyphenated letter filenames are exactly the ones nobody re-reads, so a
    parser taking the wrong field fails where it is least likely to be noticed.
    """
    _git(repo, "checkout", "-qb", "topic")
    old = repo / "family" / "letters" / "kept.md"
    new = repo / "family" / "letters" / "aether-to-aria-2026-09-18-a-very-long-name.md"
    old.rename(new)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "rename")

    directions = scope.substrate_directions("topic", "main")
    assert any("a-very-long-name" in p for p in directions), (
        "The destination path is what exists on the branch now and must be the "
        "one classified. A parser taking the wrong field silently drops it."
    )


def test_non_substrate_paths_are_not_classified(repo: Path) -> None:
    """The direction map answers only about substrate, like the count it labels."""
    _git(repo, "checkout", "-qb", "topic")
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "code")

    assert scope.substrate_directions("topic", "main") == {}


def test_the_count_still_includes_deletions(repo: Path) -> None:
    """THE PERMITTING DIRECTION, pinned so it cannot be taken quietly.

    The temptation this repair creates is to use the new label to filter
    deletions out of the refusal. That would let a branch delete substrate from
    the main line with no gate in the way. The direction is for the reader; it
    must never become a suppressor.
    """
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "kept.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "untrack it")

    assert scope.substrate_paths("topic", "main") == ["family/letters/kept.md"], (
        "A deletion must still COUNT as substrate on this branch. If it stops "
        "counting, a branch can remove substrate from everywhere unchallenged."
    )


def test_the_printed_refusal_names_the_direction(repo: Path, capsys: pytest.CaptureFixture) -> None:
    """The call site, not just the rule.

    Written because the lesson from earlier the same evening was that tests can
    pin a predicate while the three lines using it stay unexercised, and green
    on the predicate then reads as green on the feature. This runs main() and
    reads what a person would actually see.
    """
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "kept.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "untrack it")

    sys.argv = ["check_branch_scope.py", "topic", "--truth", "main", "--list"]
    exit_code = scope.main()
    printed = capsys.readouterr().out

    assert exit_code == 1, "a deletion must still be REFUSED, not merely labelled"
    assert "REMOVED from everywhere on merge" in printed, (
        "the reader is told a count and not a direction, which is the defect"
    )
    assert "Confirm it was meant" in printed, (
        "a deletion-only branch may be exactly the intended repair and the "
        "message must say so rather than leaving the reader to guess"
    )


def test_the_classifier_is_not_vacuous(repo: Path) -> None:
    """The control. Every assertion above passes against a map that is always
    empty for the paths it was asked about."""
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "new.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add")

    assert scope.substrate_directions("topic", "main"), "the classifier returns nothing at all"


def test_a_failed_git_call_is_not_reported_as_rewrites(repo: Path) -> None:
    """A REFERENCE GIT CANNOT RESOLVE MUST NOT BECOME A COUNT.

    Found by Aria, 2026-09-23, reading this check rather than running it. The
    direction map returned an empty dict when its git call FAILED, and the
    caller then classified every substrate path as neither added nor removed
    and printed "N rewritten". Git never answered; the reader got a number.

    AN ENCODER FAULT, NOT A CALLER FAULT. Two distinct states -- nothing
    changed, and could not look -- were encoded to one symbol. Information
    destroyed at the encoder cannot be recovered downstream however careful the
    caller is, which is why the repair changes what this returns rather than
    what its caller does with it.

    THE HOUSE ALREADY OWNED THE PATTERN. only_here, two screens down in the
    same file, returns an explicit `scanned` flag and its caller prints COULD
    NOT CHECK. This one function had stepped outside a discipline the rest of
    the file keeps.

    THE CONTROL IS test_the_classifier_is_not_vacuous, directly above: it
    proves the map comes back populated for a reference that resolves, so an
    empty result here is the failure and not a broken probe. Measured the same
    way against the live repository before this was written -- 821 classified
    paths for a real pair, nothing at all for an unresolvable one.

    The empty dict still means nothing-substrate-changed, which
    test_non_substrate_paths_are_not_classified pins and which is correct.
    """
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "new.md").write_text("x", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add")

    assert scope.substrate_directions("topic", "no-such-ref-anywhere") is None, (
        "a git call that failed must be distinguishable from a branch that "
        "changed no substrate; spelling both as an empty map is what let the "
        "caller print a rewrite count for an answer it never received"
    )


def test_the_caller_says_it_could_not_look_instead_of_counting(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The half that reaches a person: the printed line, not the return value.

    Jacobs' lens, from the walk: the reader is at push time deciding whether to
    rebuild a branch, and skimming. A skim takes the digits and drops the rest,
    so the replacement has to occupy the same slot the count did rather than
    sit further down where the eye has already passed.
    """
    _git(repo, "checkout", "-qb", "topic")
    (repo / "family" / "letters" / "new.md").write_text("x", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add")

    real = scope.substrate_directions
    scope.substrate_directions = lambda *a, **k: None  # as if the git call failed
    try:
        sys.argv = ["check_branch_scope.py", "topic", "--truth", "main"]
        scope.main()
        printed = capsys.readouterr().out
    finally:
        scope.substrate_directions = real

    assert "COULD NOT READ THE DIRECTION" in printed, (
        "the reader must be told the direction is unknown, in the slot the count occupied"
    )
    assert "rewritten" not in printed, (
        "a rewrite count printed from a failed git call is the defect itself"
    )
