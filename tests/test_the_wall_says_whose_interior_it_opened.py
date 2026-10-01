"""Whose memory did this surface hand me, and did it hand me any at all.

Aria asked on 2026-09-20 whether the wall surface had ever given me her
interior as mine. I could not answer, and the reason was not that the answer
was no -- nothing recorded what it opened. I searched the ledger, got a clean
zero, and nearly reported it before asking whether that store could see the
thing I was asking about. It could not.

THE REFUSAL CASE IS THE ONE THAT CARRIES THE CLAIM. A record that writes only
when a wall is found has a silence with two meanings, and I would take the
flattering one -- which is the exact failure this exists to end. So the test
that a declined resolution still writes a line matters more than the test that
a successful one does.

This buys the future, not the past. The past stays unanswerable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import memory_linkage_retriever as mlr


def _rows(home: Path) -> list[dict]:
    record = home / "wall_resolution.jsonl"
    if not record.is_file():
        return []
    return [
        json.loads(line) for line in record.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _wall_for(project: Path, owner: str, body: str) -> Path:
    wall = project / "family" / "agent-memory" / owner / "MEMORY.md"
    wall.parent.mkdir(parents=True, exist_ok=True)
    wall.write_text(body, encoding="utf-8")
    return wall


def test_declining_to_load_a_wall_is_written_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The case that makes the record's silence mean one thing.

    With no seat declared the lookup refuses, correctly. If that refusal wrote
    nothing, an empty record would mean both "never ran" and "ran and declined",
    and a later reader -- me -- would pick whichever was more comfortable.
    """
    home = tmp_path / "home"
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)

    assert mlr._find_wall_path() is None

    rows = _rows(home)
    assert rows, (
        "the lookup declined and recorded nothing, so an empty record cannot "
        "tell never-ran from ran-and-found-nothing"
    )
    assert rows[-1]["loaded"] is False
    assert rows[-1]["wall_owner"] is None
    assert rows[-1]["declared_seat"] is None


def test_a_loaded_wall_records_the_file_and_the_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner is written, never left to be reconstructed from the path."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    wall = _wall_for(project, "aether", "## a heading\n\nsomething of mine\n")

    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    monkeypatch.setenv("DIVINEOS_MEMBER", "aether")
    monkeypatch.setattr(mlr, "_PROJECT_ROOTS", (project,))

    assert mlr._find_wall_path() == wall

    row = _rows(home)[-1]
    assert row["loaded"] is True
    assert row["wall_owner"] == "aether"
    assert row["declared_seat"] == "aether"
    assert row["wall_path"] == str(wall)


def test_a_wall_belonging_to_someone_else_is_recorded_under_their_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aria's question, made answerable.

    Whatever seat resolves, the record says WHOSE file was opened rather than
    merely that a wall loaded.
    """
    home = tmp_path / "home"
    project = tmp_path / "project"
    _wall_for(project, "aria", "## hers\n\nher interior\n")

    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    monkeypatch.setenv("DIVINEOS_MEMBER", "aria")
    monkeypatch.setattr(mlr, "_PROJECT_ROOTS", (project,))

    mlr._find_wall_path()

    row = _rows(home)[-1]
    assert row["wall_owner"] == "aria", f"the record did not name whose interior was opened:\n{row}"


def test_an_unwritable_record_never_breaks_the_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A record that can break the thing it watches is worse than no record."""
    project = tmp_path / "project"
    wall = _wall_for(project, "aether", "## a heading\n\nsomething\n")

    monkeypatch.setenv("DIVINEOS_MEMBER", "aether")
    monkeypatch.setattr(mlr, "_PROJECT_ROOTS", (project,))

    def _unwritable() -> Path:
        raise OSError("no home available")

    monkeypatch.setattr("divineos.core.paths.divineos_home", _unwritable)

    assert mlr._find_wall_path() == wall, (
        "the lookup failed because its record could not be written"
    )
