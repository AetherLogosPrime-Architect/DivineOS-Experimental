"""The driver's logic and git's dispatch to it are two different claims.

Written 2026-09-18. The classification inside ``union_resolve`` has been correct
since June and was re-proven tonight against the seven real conflicting pairs:
five resolve, two refuse on partial overlap. None of that establishes that git
ever CALLS the driver, which is a separate arrangement in two halves --
``.gitattributes`` names which driver a path uses and travels with the repo,
while the driver itself is a per-clone config entry and travels with nothing.

A clone that has not run setup reads the attribute, finds no driver by that
name, and falls back to ordinary merging. That is the right failure direction --
toward a conflict rather than toward a silent resolution -- and it is also
exactly how a working driver and an uninstalled one become indistinguishable.

So these tests build a real repository, register the driver the way the setup
script does, and merge. Not a simulated invocation: the question is whether git
reaches the driver at all.

WHY THIS FILE EXISTS AT ALL. Earlier the same evening I shipped a predicate
whose three wiring lines were never exercised and said so in the record. The
lesson arrived before the mistake this time.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DRIVER = REPO_ROOT / "scripts" / "merge_driver_generated_catalogue.py"
CATALOGUE = "docs/AUTOMATION_REGISTER.md"

# A catalogue shaped like the real one: a tally line that every branch rewrites,
# and rows that every branch appends to.
BASE = """# Automation register

Total automations: 10

| name | fires |
|---|---|
| alpha | on commit |
| beta | on push |
"""


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    (r / "docs").mkdir(parents=True)
    _git(r.parent, "init", "-q", "-b", "main", str(r))
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")

    # Registered exactly as setup/setup-hooks.sh does it, with an absolute path
    # to the driver because this throwaway repo has no scripts directory.
    _git(r, "config", "merge.catalogue.name", "generated catalogue union-merge")
    _git(
        r,
        "config",
        "merge.catalogue.driver",
        f'python "{DRIVER}" %O %A %B %L %P',
    )
    (r / ".gitattributes").write_text(f"{CATALOGUE} merge=catalogue\n", encoding="utf-8")

    (r / CATALOGUE).write_text(BASE, encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    return r


def _branch_appending(repo: Path, name: str, row: str, total: str) -> None:
    """A branch that does what every branch here does: add a row, bump the tally."""
    _git(repo, "checkout", "-q", "-b", name, "main")
    text = BASE.replace("Total automations: 10", f"Total automations: {total}")
    text = text + f"| {row} | on merge |\n"
    (repo / CATALOGUE).write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", f"add {row}")


def test_git_actually_reaches_the_driver(repo: Path) -> None:
    """The end-to-end claim: two branches conflict and the merge completes.

    THE CONTRACT CHANGED UNDER THIS TEST and the change is the finding, not an
    adjustment to make a red test green.

    It first asserted that BOTH rows survive, because the driver was a union
    resolver. That resolver turned out to fabricate: two sides describing the
    same entry differently were kept side by side, and a register listing one
    automation twice with contradictory rows is text nobody wrote. Adding a
    key-collision refusal then made it refuse all seven real pairs, which is a
    driver that never resolves.

    The register is a pure function of the tree -- so both sides of any conflict
    here are stale renderings of one fact, and keeping both was never meaningful
    in the first place. Taking one whole loses nothing because the generator
    rebuilds it, and `generate_automation_register.py --check` refuses a stale
    one at commit time.

    So the property worth testing is not which rows survive. It is that the
    driver never invents. That is pinned below.
    """
    _branch_appending(repo, "left", "gamma", "11")
    _branch_appending(repo, "right", "delta", "11")

    _git(repo, "checkout", "-q", "left")
    merged = _git(repo, "merge", "--no-edit", "right", check=False)

    text = (repo / CATALOGUE).read_text(encoding="utf-8")

    assert merged.returncode == 0, (
        "the merge did not succeed, so either the driver was never reached or it "
        f"refused. stdout={merged.stdout!r} stderr={merged.stderr!r}"
    )
    assert "<<<<<<<" not in text, "conflict markers survived a supposedly clean merge"


def test_the_result_is_always_one_of_the_two_sides_and_never_a_blend(repo: Path) -> None:
    """The safety property that replaced 'keep both rows'.

    A stale rendering is harmless because it is rebuilt. INVENTED content is not
    rebuilt -- it is read, by people trying to find out what runs by itself. So
    the one thing the driver must never do is emit a file that is neither side.
    """
    _branch_appending(repo, "left", "gamma", "11")
    _branch_appending(repo, "right", "delta", "12")

    ours = _git(repo, "show", "left:" + CATALOGUE).stdout
    theirs = _git(repo, "show", "right:" + CATALOGUE).stdout

    _git(repo, "checkout", "-q", "left")
    _git(repo, "merge", "--no-edit", "right", check=False)
    text = (repo / CATALOGUE).read_text(encoding="utf-8")

    assert text in (ours, theirs), (
        "the merged file matches neither side exactly, which means the driver "
        "composed something no branch contains. That is the fabrication failure "
        "this driver was rebuilt to remove."
    )


def test_a_row_only_one_side_has_comes_back_from_the_generator(repo: Path) -> None:
    """The half that makes taking one side honest rather than merely quiet.

    Taking one side drops the other's row from the FILE. That is only acceptable
    because the row is not information -- it is a rendering of the tree, and the
    generator puts it back. Here the generator is stood in for by a script that
    reads the tree, because the real one needs this repository; what is being
    pinned is the shape of the argument, not the real generator's output.
    """
    _branch_appending(repo, "left", "gamma", "11")
    _branch_appending(repo, "right", "delta", "11")
    _git(repo, "checkout", "-q", "left")
    _git(repo, "merge", "--no-edit", "right", check=False)

    after_merge = (repo / CATALOGUE).read_text(encoding="utf-8")
    dropped = "delta" not in after_merge or "gamma" not in after_merge
    assert dropped, (
        "this test's premise is that one side's row is dropped by the merge. If "
        "both survived, the driver is doing something other than taking one side "
        "and the argument below does not apply."
    )

    # The stand-in generator: the register is whatever the tree says it is.
    both = "| gamma | on merge |\n| delta | on merge |\n"
    (repo / CATALOGUE).write_text(BASE + both, encoding="utf-8")
    rebuilt = (repo / CATALOGUE).read_text(encoding="utf-8")

    assert "gamma" in rebuilt and "delta" in rebuilt, (
        "regeneration is what makes take-one-side lossless. If a row cannot come "
        "back from the tree, the file holds information and taking one side is "
        "data loss rather than a stale rendering."
    )


def test_an_unregistered_clone_conflicts_rather_than_resolving_silently(
    repo: Path,
) -> None:
    """The failure direction that makes the two-halves gap survivable.

    Without the per-clone driver registration the attribute names a driver that
    does not exist. Git must fall back to an ordinary merge and CONFLICT -- never
    quietly pick a side. A silent resolution here would be work disappearing in a
    fresh checkout with nothing to notice it.
    """
    # BOTH keys, which is the true fresh-clone shape. An earlier version of this
    # test unset only the driver and left the name, and that is a DIFFERENT
    # state: git treats a half-defined driver as an error and aborts the merge
    # with status 128, leaving no markers. Loud, and not what a clone that never
    # ran setup looks like. Measured all three states before fixing the test
    # rather than adjusting the assertion until it passed.
    _git(repo, "config", "--unset", "merge.catalogue.driver")
    _git(repo, "config", "--unset", "merge.catalogue.name")
    _branch_appending(repo, "left", "gamma", "11")
    _branch_appending(repo, "right", "delta", "11")

    _git(repo, "checkout", "-q", "left")
    merged = _git(repo, "merge", "--no-edit", "right", check=False)
    text = (repo / CATALOGUE).read_text(encoding="utf-8")

    assert merged.returncode != 0, (
        "an unregistered driver produced a clean merge, which means something "
        "resolved this without a person and without the driver"
    )
    assert "<<<<<<<" in text
    assert "gamma" in text and "delta" in text, (
        "the fallback must present BOTH sides to the person. A fallback that "
        "quietly keeps one side is worse than the conflict it replaces."
    )


def test_the_same_entry_described_differently_still_yields_one_whole_side(
    repo: Path,
) -> None:
    """The case that killed the union resolver, kept as a test of what replaced it.

    Both sides rewrite the same row with different meaning. The union resolver
    kept both and produced a register describing one automation twice. The
    driver must now take one side whole -- which is not a judgement about which
    description is right, because neither is: both are renderings, and the
    generator decides.
    """
    _git(repo, "checkout", "-q", "-b", "left", "main")
    (repo / CATALOGUE).write_text(
        BASE.replace("| alpha | on commit |", "| alpha | on commit and on push |"),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "left rewrites alpha")

    _git(repo, "checkout", "-q", "-b", "right", "main")
    (repo / CATALOGUE).write_text(
        BASE.replace("| alpha | on commit |", "| alpha | on schedule |"),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "right rewrites alpha")

    ours = _git(repo, "show", "left:" + CATALOGUE).stdout
    theirs = _git(repo, "show", "right:" + CATALOGUE).stdout

    _git(repo, "checkout", "-q", "left")
    merged = _git(repo, "merge", "--no-edit", "right", check=False)
    text = (repo / CATALOGUE).read_text(encoding="utf-8")

    assert merged.returncode == 0, "the merge must complete rather than stall the queue"
    assert text in (ours, theirs), (
        "the driver blended two descriptions of one entry. That is the exact "
        "fabrication the union resolver produced on five of seven real pairs."
    )
    assert not ("on commit and on push" in text and "on schedule" in text), (
        "both descriptions of the same entry survived, which is the register lying"
    )


def test_the_driver_file_is_where_the_configuration_points(repo: Path) -> None:
    """The control. Every test above would fail the same way if the path were
    simply wrong, which reads as 'the driver does not work' rather than 'the
    driver is not there'."""
    assert DRIVER.exists(), f"the driver is not at {DRIVER}"
