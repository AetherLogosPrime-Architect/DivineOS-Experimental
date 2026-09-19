"""A generated artifact is never merged; it is regenerated and compared.

Aether's rule, 2026-09-19, after Andrew told me merging is his domain and I
should learn it with him: *"a generated artifact is never merged, it is
regenerated from the merged source and compared. A clean auto-merge on a
generated file is the dangerous case precisely because nothing objects."*

And his one design constraint, which is what most of these tests are about:
*"the hot-file list must be derived, not typed. I measured eight files today;
that set will drift, and a typed list goes stale silently."*

So the tests below check that the tool DERIVES rather than remembers, and that
its central door fires on the state it exists for.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_surface.py"
ROOT = SCRIPT.parent.parent


@pytest.fixture(scope="module")
def surface():
    spec = importlib.util.spec_from_file_location("merge_surface", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_artifacts_are_discovered_not_listed(surface):
    """Every generator that declares an OUTPUT is found by reading the generator.

    The point is the METHOD. If this file named the artifacts, it would be the
    typed list Aether warned about, and adding a third generator tomorrow would
    leave it silently half-right.
    """
    found = surface.declared_generated_outputs()

    assert found, "no generator declared an OUTPUT; the discovery method is broken"
    for artifact, generator in found.items():
        assert generator.exists(), f"{generator} was named as a generator but is absent"
        # The mapping must come from the generator's own text, so the artifact
        # path it claims has to appear inside it.
        assert artifact.name in generator.read_text(encoding="utf-8")


def test_a_generator_added_later_is_found_without_editing_anything(surface, tmp_path, monkeypatch):
    """The discovery survives a new generator appearing. This is the whole ask.

    A typed list passes every test on the day it is written. This one only
    passes if the mechanism actually reads the directory.
    """
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    (fake_scripts / "generate_invented_thing.py").write_text(
        'from pathlib import Path\nROOT = Path(".")\nOUTPUT = ROOT / "docs" / "INVENTED.md"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    found = surface.declared_generated_outputs()

    assert [p.name for p in found] == ["INVENTED.md"]


def test_a_generator_with_no_declared_output_is_skipped_silently(surface, tmp_path, monkeypatch):
    """Opting out needs no special case: a generator that computes its path
    differently simply is not a committed-artifact generator, and saying so
    loudly would be a false finding about a file doing nothing wrong."""
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    (fake_scripts / "generate_something_else.py").write_text(
        "import sys\nprint('I write to stdout')\n", encoding="utf-8"
    )
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    assert surface.declared_generated_outputs() == {}


def test_a_textually_merged_artifact_is_a_finding(surface, tmp_path, monkeypatch):
    """The door. An artifact whose bytes are not what its generator produces
    must be reported, because that is precisely what a clean auto-merge leaves
    behind and precisely what nothing else objects to."""
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    (tmp_path / "docs").mkdir()
    (fake_scripts / "generate_thing.py").write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        'OUTPUT = ROOT / "docs" / "THING.md"\n'
        'OUTPUT.write_text("the only correct content\\n", encoding="utf-8")\n',
        encoding="utf-8",
    )
    # What a textual merge leaves: real-looking content that is the output of
    # nothing -- not either side, and not the merged source.
    (tmp_path / "docs" / "THING.md").write_text(
        "half of one branch and half of another\n", encoding="utf-8"
    )
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    code, messages = surface.verify_generated_are_rederived()

    assert code == surface.FINDING
    assert any("was not what its generator produces" in m for m in messages)


def test_a_rederived_artifact_is_clean(surface, tmp_path, monkeypatch):
    """Non-regression: the check must not cry about a file that is correct, or
    it becomes noise and stops being read."""
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    (tmp_path / "docs").mkdir()
    (fake_scripts / "generate_thing.py").write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        'OUTPUT = ROOT / "docs" / "THING.md"\n'
        'OUTPUT.write_text("the only correct content\\n", encoding="utf-8")\n',
        encoding="utf-8",
    )
    (tmp_path / "docs" / "THING.md").write_text("the only correct content\n", encoding="utf-8")
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    code, messages = surface.verify_generated_are_rederived()

    assert code == surface.CLEAN
    assert any("matches a fresh run" in m for m in messages)


def test_a_crashing_generator_is_could_not_look_not_a_finding(surface, tmp_path, monkeypatch):
    """Aletheia's attack, applied here from the start rather than after.

    Reporting a mismatch on a broken generator sends someone to regenerate the
    file, which is the remedy for drift and does nothing for a generator that
    cannot run. A correct-sounding instruction pointing at the wrong repair is
    worse than no instruction.
    """
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    (tmp_path / "docs").mkdir()
    (fake_scripts / "generate_thing.py").write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        'OUTPUT = ROOT / "docs" / "THING.md"\n'
        "raise SystemExit(3)\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "THING.md").write_text("anything at all\n", encoding="utf-8")
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    code, messages = surface.verify_generated_are_rederived()

    assert code == surface.COULD_NOT_LOOK
    assert any("could not look" in m for m in messages)


def test_a_generator_that_writes_nothing_is_could_not_look(surface, tmp_path, monkeypatch):
    """The quieter half of the same attack: a zero exit is not proof of output."""
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    (tmp_path / "docs").mkdir()
    (fake_scripts / "generate_thing.py").write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        'OUTPUT = ROOT / "docs" / "THING.md"\n'
        "OUTPUT.unlink()\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "THING.md").write_text("present for now\n", encoding="utf-8")
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    code, messages = surface.verify_generated_are_rederived()

    assert code == surface.COULD_NOT_LOOK
    assert any("wrote nothing" in m for m in messages)


def _run_git(repo: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_common_parentage_is_not_a_collision(surface, tmp_path, monkeypatch):
    """The correction Aether made to his own measurement, pinned.

    He told me two branches shared ninety-four files and should land adjacent.
    Re-measured, they share zero: the ninety-four was every file they both
    INHERITED from an ancestor far ahead of main, byte-identical on both sides.
    Common parentage wearing a collision's shape.

    This builds that exact topology -- main, then a long shared trunk, then two
    branches off the trunk touching different files -- and asserts the naive
    count is large while the honest one is zero.
    """
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(repo)], check=True)
    _run_git(repo, "config", "user.email", "test@test")
    _run_git(repo, "config", "user.name", "test")

    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _run_git(repo, "add", "seed.txt")
    _run_git(repo, "commit", "-qm", "main")

    # A long shared trunk that main never sees. Every file here is inherited by
    # BOTH branches below and is identical on both sides.
    _run_git(repo, "checkout", "-qb", "trunk")
    for i in range(12):
        (repo / f"inherited_{i}.txt").write_text(f"{i}\n", encoding="utf-8")
        _run_git(repo, "add", f"inherited_{i}.txt")
    _run_git(repo, "commit", "-qm", "a long stretch of shared work")

    _run_git(repo, "checkout", "-qb", "branch_a")
    (repo / "only_a.txt").write_text("a\n", encoding="utf-8")
    _run_git(repo, "add", "only_a.txt")
    _run_git(repo, "commit", "-qm", "a")

    _run_git(repo, "checkout", "-q", "trunk")
    _run_git(repo, "checkout", "-qb", "branch_b")
    (repo / "only_b.txt").write_text("b\n", encoding="utf-8")
    _run_git(repo, "add", "only_b.txt")
    _run_git(repo, "commit", "-qm", "b")

    monkeypatch.setattr(surface, "ROOT", repo)

    naive = set(_run_git(repo, "diff", "--name-only", "main...branch_a").split()) & set(
        _run_git(repo, "diff", "--name-only", "main...branch_b").split()
    )
    shared, count, where, why = surface.truly_shared_files("branch_a", "branch_b")

    assert why is None, why
    assert len(naive) == 12, "the naive count should see all the inherited files"
    assert count == 0, f"they change disjoint files; got {shared}"
    assert where, "the ancestor they share must be named, not implied"


def test_a_real_overlap_survives_the_correction(surface, tmp_path, monkeypatch):
    """Non-regression, and the more important half.

    The correction must only SHRINK a count, never hide a genuine collision --
    otherwise it would turn a measurement into an excuse. Two branches touching
    the same file from a shared trunk still report that file.
    """
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(repo)], check=True)
    _run_git(repo, "config", "user.email", "test@test")
    _run_git(repo, "config", "user.name", "test")

    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _run_git(repo, "add", "seed.txt")
    _run_git(repo, "commit", "-qm", "main")

    _run_git(repo, "checkout", "-qb", "trunk")
    (repo / "contested.txt").write_text("original\n", encoding="utf-8")
    _run_git(repo, "add", "contested.txt")
    _run_git(repo, "commit", "-qm", "shared work")

    _run_git(repo, "checkout", "-qb", "branch_a")
    (repo / "contested.txt").write_text("a changed it\n", encoding="utf-8")
    _run_git(repo, "add", "contested.txt")
    _run_git(repo, "commit", "-qm", "a")

    _run_git(repo, "checkout", "-q", "trunk")
    _run_git(repo, "checkout", "-qb", "branch_b")
    (repo / "contested.txt").write_text("b changed it\n", encoding="utf-8")
    _run_git(repo, "add", "contested.txt")
    _run_git(repo, "commit", "-qm", "b")

    monkeypatch.setattr(surface, "ROOT", repo)

    shared, count, _where, why = surface.truly_shared_files("branch_a", "branch_b")

    assert why is None, why
    assert shared == {"contested.txt"}
    assert count == 1


def test_two_branches_with_no_common_ancestor_is_could_not_look(surface, tmp_path, monkeypatch):
    """An orphan branch shares no history at all. That is not zero collisions --
    it is a question this measurement cannot answer, and saying zero would be
    the confident-about-an-unreached-subject fault again."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(repo)], check=True)
    _run_git(repo, "config", "user.email", "test@test")
    _run_git(repo, "config", "user.name", "test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _run_git(repo, "add", "seed.txt")
    _run_git(repo, "commit", "-qm", "main")

    _run_git(repo, "checkout", "-q", "--orphan", "stranger")
    _run_git(repo, "rm", "-rqf", ".")
    (repo / "elsewhere.txt").write_text("no shared history\n", encoding="utf-8")
    _run_git(repo, "add", "elsewhere.txt")
    _run_git(repo, "commit", "-qm", "orphan")

    monkeypatch.setattr(surface, "ROOT", repo)

    _shared, count, _where, why = surface.truly_shared_files("main", "stranger")

    assert why is not None
    assert "no common ancestor" in why
    assert count == 0


def test_a_bridging_branch_does_not_bind_the_branches_it_bridges(surface, tmp_path, monkeypatch):
    """The finding that contradicted the design, pinned so it cannot be undone.

    Aether proposed grouping branches into clusters that "must be ordered
    against each other". Built and run over six live branches, thirteen of
    fifteen pairs collided and all six collapsed into one group -- not a bug,
    the edges were hand-checked and are real.

    The reason is here: A and C share nothing, B shares with both, and
    transitive grouping then declares A and C jointly constrained. They are
    not. The constraint is PAIRWISE and does not compose, so the edges are the
    answer and the group is at most a region to look at.
    """
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(repo)], check=True)
    _run_git(repo, "config", "user.email", "test@test")
    _run_git(repo, "config", "user.name", "test")
    for name in ("x.txt", "y.txt"):
        (repo / name).write_text("seed\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-qm", "main")

    for branch, files in (("a", ["x.txt"]), ("b", ["x.txt", "y.txt"]), ("c", ["y.txt"])):
        _run_git(repo, "checkout", "-q", "main")
        _run_git(repo, "checkout", "-qb", branch)
        for name in files:
            (repo / name).write_text(f"{branch} changed it\n", encoding="utf-8")
        _run_git(repo, "add", ".")
        _run_git(repo, "commit", "-qm", branch)

    monkeypatch.setattr(surface, "ROOT", repo)

    edges, clusters, unconnected, total = surface.clusters_from_pairs(["a", "b", "c"])

    assert total == 3
    paired = {frozenset((left, right)) for left, right, _n in edges}
    assert frozenset(("a", "b")) in paired
    assert frozenset(("b", "c")) in paired
    # The whole point: the bridge does not create this edge.
    assert frozenset(("a", "c")) not in paired, "a and c share no file and must not be paired"
    # And the region still contains all three, which is exactly why a region
    # must never be printed as an ordering constraint.
    assert clusters == [["a", "b", "c"]]
    assert unconnected == []


def test_no_generators_at_all_is_could_not_look_not_clean(surface, tmp_path, monkeypatch):
    """An empty result must never render as a pass. Nothing-to-check and
    everything-checked-and-fine are different facts."""
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    code, messages = surface.verify_generated_are_rederived()

    assert code == surface.COULD_NOT_LOOK
    assert any("nothing was checked" in m for m in messages)
