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


def test_no_generators_at_all_is_could_not_look_not_clean(surface, tmp_path, monkeypatch):
    """An empty result must never render as a pass. Nothing-to-check and
    everything-checked-and-fine are different facts."""
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(surface, "ROOT", tmp_path)

    code, messages = surface.verify_generated_are_rederived()

    assert code == surface.COULD_NOT_LOOK
    assert any("nothing was checked" in m for m in messages)
