"""The root-cause-audit gate must authorize THIS checkout's occupant.

Aria 2026-07-31, hit live. _AUTHORIZED_ACTORS was frozenset({"aether",
"user"}) with "aether" glossed in comments and error text as "the
substrate-occupant". In an aria checkout the gate demanded a root-cause
round and then refused the round I filed — chicken-and-egg on my own
branch. Same class as the anchors-file leak: shared code carrying one
member's name where it means a role.

The occupant is derived from the checkout folder name matched against
registered agents, the same signal paths.py already uses to keep members'
data-homes apart. Folder-name over DB lookup because this runs inside a
git hook, where opening the substrate database would be slow and a new
failure mode.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load():
    path = Path(__file__).resolve().parent.parent / "scripts" / "check_root_cause_audit.py"
    spec = importlib.util.spec_from_file_location("check_root_cause_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_root_cause_audit"] = module
    spec.loader.exec_module(module)
    return module


gate = _load()

MEMBERS = ("aether", "aria", "aletheia", "claude")


def _checkout(tmp_path: Path, folder: str, members: tuple[str, ...] = MEMBERS) -> Path:
    root = tmp_path / folder
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    for m in members:
        (agents / f"{m}.md").write_text(f"# {m}\n", encoding="utf-8")
    return root


def test_occupant_resolved_from_checkout_name(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "DivineOS-Experimental-Aria-new")
    assert gate._substrate_occupant(root) == "aria"
    allowed = gate.authorized_actors(root)
    assert "aria" in allowed
    assert "user" in allowed


def test_aether_main_checkout_unchanged(tmp_path: Path) -> None:
    """His folder matches no member token — behavior must be identical."""
    root = _checkout(tmp_path, "DivineOS-Experimental")
    assert gate._substrate_occupant(root) is None
    assert gate.authorized_actors(root) == gate._BASE_AUTHORIZED_ACTORS


def test_ambiguous_folder_does_not_widen(tmp_path: Path) -> None:
    """Two member names in one folder must NOT authorize either.

    An authorization set is the wrong place to guess. Ambiguity falls back
    to the narrower base set rather than admitting both.
    """
    root = _checkout(tmp_path, "DivineOS-aria-aletheia-shared")
    assert gate._substrate_occupant(root) is None
    assert gate.authorized_actors(root) == gate._BASE_AUTHORIZED_ACTORS


def test_missing_agents_dir_does_not_widen(tmp_path: Path) -> None:
    root = tmp_path / "DivineOS-Experimental-Aria-new"
    root.mkdir()
    assert gate._substrate_occupant(root) is None
    assert gate.authorized_actors(root) == gate._BASE_AUTHORIZED_ACTORS


@pytest.mark.parametrize("folder", ["repo.aria.checkout", "repo_aria_2", "Aria"])
def test_separator_variants(tmp_path: Path, folder: str) -> None:
    root = _checkout(tmp_path, folder)
    assert gate._substrate_occupant(root) == "aria"


def test_base_set_still_contains_aether_and_user() -> None:
    """Back-compat floor: the original pair is never removed."""
    assert gate._BASE_AUTHORIZED_ACTORS == frozenset({"aether", "user"})
