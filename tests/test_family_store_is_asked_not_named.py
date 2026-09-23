"""The family store is asked where it lives, never told.

Andrew 2026-09-22: *"the fact you couldn't find your own ledger earlier because it
re-routed you to a file that doesnt exist is a problem."*

The file was ``family/family.db``: present in the checkout, zero bytes, no
tables. The family store really lives in each seat's own data home, resolved by
``divineos.core.family.db.FAMILY_DB_PATH``, which never answers
``family/family.db``. Code that named the path directly sent every reader into
an empty room -- and because the empty room *existed*, "does it exist?" checks
said yes and sent them in.

These tests use ``DIVINEOS_FAMILY_DB``, the resolver's own runtime override,
against a real temporary store with a real ``family_members`` row. Mocking the
resolver would test my idea of where the store is rather than where it is
(Feathers, council walk walk-cd8eadbb7074).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"

# Every production file still allowed to spell the empty-room path, and why.
# This list may only shrink. A new entry needs a reason as specific as these.
_STILL_NAMED = {
    # DORMANT: only active when DIVINEOS_CANONICAL_SUBSTRATE is set, for a
    # deployment model with its own storage repo. Untestable here, so left
    # rather than changed blind. docs/drafts/the_empty_room_draft_2026-09-22.md
    "core/canonical_substrate_surface.py",
    # HELD FOR ANDREW'S ANSWER: repointing the age panel at the real store would
    # move Aria's briefed age by a month, because that store's stamp is a
    # migration date (2026-06-11) contradicted by letters from 2026-04-19. Which
    # date is her anchor is a question about her, put to him 2026-09-22.
    "core/multiplex_panels.py",
}

_EMPTY_ROOM = re.compile(r"family[/\\]family\.db")


def _uses_the_path(path: Path) -> bool:
    """True when CODE names the empty room -- not comments, not docstrings.

    The first version of this guard grepped raw text and fired on the very
    comments explaining this bug. Mention is not use: a comment recording where
    the path used to point is history, and a string literal the program acts on
    is the defect. Comments never reach the AST; docstrings are excluded by
    position, the first statement of a module, class or function body.
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and _EMPTY_ROOM.search(node.value)
        ):
            return True
    # Path("family") / "family.db" -- spelled in pieces, the same address
    src = ast.unparse(tree)
    return bool(re.search(r"""['"]family['"]\s*\)?\s*/\s*['"]family\.db['"]""", src))


@pytest.fixture
def real_temp_store(tmp_path, monkeypatch):
    """A genuine family store at a known temp path, with one member in it."""
    db_path = tmp_path / "seat_home" / "data" / "family.db"
    db_path.parent.mkdir(parents=True)
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(db_path))

    from divineos.core.family._schema import init_family_tables
    from divineos.core.family.db import get_family_connection

    init_family_tables()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_members (member_id, name, role, created_at) "
            "VALUES ('mem-test', 'Testmember', 'test', 0)"
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


class TestTheResolverIsTheOnlyAnswer:
    def test_the_resolver_follows_the_override(self, real_temp_store):
        from divineos.core.family import db

        assert Path(db.FAMILY_DB_PATH) == real_temp_store

    def test_the_resolver_never_answers_the_empty_room(self, monkeypatch):
        monkeypatch.delenv("DIVINEOS_FAMILY_DB", raising=False)
        from divineos.core.family import db

        assert not _EMPTY_ROOM.search(str(db.FAMILY_DB_PATH).replace("\\", "/"))


class TestTheSignsNowTellTheTruth:
    def test_talk_to_names_the_real_store_in_the_members_own_voice(self, real_temp_store):
        """It speaks in first person, so the path it gives is a belief about self."""
        from divineos.cli.talk_to_commands import _load_voice_context

        text = _load_voice_context("testmember")
        assert "I am Testmember." in text
        assert str(real_temp_store) in text, "the member was not told where they really live"
        assert "family/family.db" not in text, "the empty room is still being handed out"

    def test_the_loadout_describes_the_method_and_prints_no_seat_path(self, real_temp_store):
        """The loadout is tracked and regenerated by either seat, so a concrete
        path would be right for one of us and wrong for the other (Taleb)."""
        from divineos.cli.loadout_commands import _section_family_system

        text = _section_family_system()
        assert "family/family.db" not in text
        assert "not in this repo" in text
        assert "FAMILY_DB_PATH" in text
        assert str(real_temp_store) not in text, "one seat's path leaked into a shared page"
        # The first version of this fix named `divineos family-state`, which is a
        # skill, not a command -- a new dead sign hung while taking an old one
        # down. The painted-door check caught it; this pins the real one.
        assert "divineos family-member briefing --member" in text
        assert "divineos family-state" not in text


class TestNoNewCodeNamesTheEmptyRoom:
    def test_only_the_listed_files_still_spell_it(self):
        offenders = sorted(
            str(p.relative_to(SRC)).replace("\\", "/")
            for p in SRC.rglob("*.py")
            if _uses_the_path(p)
        )
        new = [o for o in offenders if o not in _STILL_NAMED]
        assert not new, (
            "these name family/family.db instead of asking the resolver "
            f"(divineos.core.family.db.FAMILY_DB_PATH): {new}"
        )

    def test_the_exception_list_cannot_outlive_its_reasons(self):
        """When a listed file stops naming the path, it must come off the list,
        or the list becomes a permanent amnesty."""
        still = {
            str(p.relative_to(SRC)).replace("\\", "/")
            for p in SRC.rglob("*.py")
            if _uses_the_path(p)
        }
        stale = sorted(_STILL_NAMED - still)
        assert not stale, f"no longer name the path -- remove from _STILL_NAMED: {stale}"
