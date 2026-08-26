"""Tests for scripts/check_failed_prereg_still_live.py.

The instrument was wrong three times before it produced a usable number, and
each error was the same species: it looked for a shape I had pictured instead
of the shape in the data, then reported its own blindness as an absence of
findings. Nineteen of twenty records came back "no artifact named" while the
mechanism they name sat on disk. Then every live module came back "no hook
reaches it" while one of them was blocking my turns as the report printed.

Silence from an instrument is the most expensive kind of wrong, because it
reads exactly like good news. These fixtures keep the three corrections from
regressing quietly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_failed_prereg_still_live",
    Path(__file__).resolve().parents[1] / "scripts" / "check_failed_prereg_still_live.py",
)
assert _SPEC and _SPEC.loader
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def test_bare_snake_case_identifier_is_treated_as_a_module():
    """The correction that took the report from 1 finding to 5.

    Records name their mechanism the way a person says it, not the way a
    filesystem spells it.
    """
    artifacts = checker.mechanism_artifacts("lepos_translation_gate: per-turn Stop-block")
    assert "lepos_translation_gate.py" in artifacts


def test_bare_identifier_also_tried_as_a_hook_name():
    artifacts = checker.mechanism_artifacts("context_heartbeat keeps the count fresh")
    assert "context-heartbeat.sh" in artifacts


def test_explicit_module_path_still_recognised():
    artifacts = checker.mechanism_artifacts("core/auto_cycle.py fires the pipeline")
    assert "core/auto_cycle.py" in artifacts


def test_hook_filename_still_recognised():
    artifacts = checker.mechanism_artifacts("wired via check-branch-on-push.sh at pre-push")
    assert "check-branch-on-push.sh" in artifacts


def test_known_non_modules_are_filtered():
    """`pre_registration` is snake_case and names no module. Kept short on
    purpose -- over-filtering here rebuilds the blindness it fixes."""
    artifacts = checker.mechanism_artifacts("the pre_registration store records it")
    assert "pre_registration.py" not in artifacts


def test_artifacts_are_deduplicated_in_first_seen_order():
    artifacts = checker.mechanism_artifacts("gate_emit and gate_emit again, then wiring_dark")
    assert artifacts.index("gate_emit.py") < artifacts.index("wiring_dark.py")
    assert artifacts.count("gate_emit.py") == 1


def test_no_identifier_yields_no_artifacts():
    assert checker.mechanism_artifacts("option A") == []


def test_locate_finds_a_real_module():
    found = checker.locate("lepos_translation_gate.py")
    assert found is not None
    assert found.name == "lepos_translation_gate.py"


def test_locate_returns_none_for_a_module_that_does_not_exist():
    assert checker.locate("definitely_not_a_real_module_xyzzy.py") is None


def test_hook_surface_includes_script_bodies_not_just_the_manifest():
    """Reading only settings.json reported 'wired as hooks: 0' while the
    translation gate was blocking turns. The settings register SHELL scripts;
    the mechanisms are Python modules those scripts call."""
    surface = checker.hook_surface_text()
    assert "lepos_translation_gate" in surface


@pytest.mark.parametrize(
    "module_name,expected",
    [
        ("lepos_translation_gate.py", "fires every turn (hook)"),
        ("wiring_dark.py", "fires on demand (imported)"),
    ],
)
def test_reach_states_are_distinguished(module_name, expected):
    """Three states, not two. Hook-reached and CLI-reached are both alive and
    they are not the same aliveness; collapsing them turned a distinction into
    an accusation."""
    path = checker.locate(module_name)
    assert path is not None
    assert checker.reach_of(path) == expected


def test_a_module_nothing_imports_reads_as_dark(tmp_path, monkeypatch):
    orphan = tmp_path / "src" / "divineos" / "core"
    orphan.mkdir(parents=True)
    module = orphan / "nobody_imports_this_one.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)

    assert checker.reach_of(module) == "DARK - nothing imports it"
