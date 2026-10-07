"""With DIVINEOS_MEMBER unset, the wall still opens -- mine, never a sibling's.

main read the seat only from DIVINEOS_MEMBER. In Aether's house that variable
is empty, so his own wall was declined every turn, and a declined wall looks
exactly like an empty one (council-d67eb185800d). The fallback is this_seat(),
which names a seat only when the data home is that seat's.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import memory_linkage_retriever as mlr


def _wall(project: Path, seat: str) -> Path:
    wall = project / "family" / "agent-memory" / seat / "MEMORY.md"
    wall.parent.mkdir(parents=True)
    wall.write_text(f"## {seat}'s entry\n\nbody\n", encoding="utf-8")
    return wall


@pytest.fixture()
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)
    root = tmp_path / "project"
    monkeypatch.setattr(mlr, "_PROJECT_ROOTS", (root,))
    return root


def test_the_seat_the_house_knows_opens_its_own_wall(project, monkeypatch):
    mine = _wall(project, "aether")
    _wall(project, "aria")
    monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aether")
    assert mlr._find_wall_path() == mine


def test_a_siblings_wall_alone_is_never_borrowed(project, monkeypatch):
    # The original bug: only Aria's wall existed, and it was handed to me.
    _wall(project, "aria")
    monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aether")
    assert mlr._find_wall_path() is None


def test_a_declared_member_still_wins(project, monkeypatch):
    aria = _wall(project, "aria")
    _wall(project, "aether")
    monkeypatch.setenv("DIVINEOS_MEMBER", "aria")
    monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aether")
    assert mlr._find_wall_path() == aria
