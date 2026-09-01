"""The schema was being rebuilt on every single logged tool call.

2026-09-01. CI failed on a merge: one test timed out at thirty seconds rather
than asserting false. It fills the logbook to capacity through the production
emit path, and every emit called init_tool_logbook_tables() first -- a fresh
connection, a CREATE TABLE and three CREATE INDEX statements, a commit, a close
-- and THEN opened a second connection to do the insert.

Measured before the fix: 4.37 ms per emit on an idle machine, of which 0.97 ms
was the schema rebuild. Twenty-two percent of the cost of every tool call this
substrate has logged since July, paid to re-declare a table that already exists.
The test pays it a thousand times and had been sitting a few seconds under its
own timeout, passing on quiet days.

WHAT THESE PIN IS THE SAFETY PROPERTY, NOT THE SPEED. A timing assertion is
exactly the wall-clock dependency that produced this failure, so the numbers
live in the commit message where they cannot go flaky. What can break silently
is the memo: keyed on the process, it would skip creation for a second database
and leave a test staring at a missing table. So it is keyed on the resolved
database path -- the unit is the database, not the run.
"""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

import pytest


def _point_at(monkeypatch: pytest.MonkeyPatch, home: Path):
    """Point the substrate at a home and hand back a freshly loaded logbook."""
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    import divineos.core.tool_logbook as logbook

    importlib.reload(logbook)
    return logbook


def _current_db() -> Path:
    from divineos.core import _ledger_base

    return _ledger_base._get_db_path()


def _table_exists(db: Path) -> bool:
    if not db.exists():
        return False
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tool_logbook'"
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def test_a_second_database_still_gets_its_table(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """The memo must not blind the next database. This is the whole risk.

    Memoised on the process rather than the path, the second database here
    would skip creation, and the failure would surface far away as a missing
    table in somebody else's test.

    The path resolver is patched directly rather than moving DIVINEOS_HOME:
    this suite's own fixtures pin the database, so the environment variable
    does not move it. A first version of this test set the variable, watched
    both writes land in the same file, and would have passed while proving
    nothing -- the check has to reach the thing that actually decides.
    """
    import divineos.core.tool_logbook as logbook
    from divineos.core import _ledger_base

    first = tmp_path / "one.db"
    second = tmp_path / "two.db"
    current = {"path": first}
    monkeypatch.setattr(_ledger_base, "_get_db_path", lambda: current["path"])

    logbook._INITIALISED_DBS.clear()
    logbook.emit_tool_call(tool_name="X", tool_input={}, tool_use_id="a1")
    assert _table_exists(first), "the first database should have been initialised"

    current["path"] = second
    logbook.emit_tool_call(tool_name="X", tool_input={}, tool_use_id="b1")

    assert _table_exists(second), "the second database has no table at all"

    # THE ASSERTION THAT ACTUALLY CATCHES IT, and the first version of this test
    # did not have it. Checking only that the table exists passes against a
    # process-keyed memo, because the write path's own repair notices the
    # missing table and rebuilds it. Verified by deliberately breaking the key
    # to a constant: the test went green. A repair covering for the defect is
    # the good behaviour of one mechanism hiding the failure of another, and it
    # is exactly the shape of test that passes for the wrong reason.
    #
    # ARIA'S GENERAL FORM, 2026-09-01, and it is one step further back than mine.
    # Every assertion is satisfiable by more than one world; usually the other
    # worlds are absurd enough to ignore. A recovery path takes one of those
    # absurd worlds and makes it LIKELY -- it manufactures a plausible alternative
    # cause for the exact observable you chose. So the question at test-writing
    # time is not "is this the right unit", which was already right here, and not
    # "is there a fallback nearby", which needs you to suspect one first. It is:
    # WHAT ELSE COULD MAKE THIS ASSERTION TRUE, AND DID THIS COMMIT JUST ADD ONE?
    #
    # She found this by running the mutation on her own guard before replying:
    # six tests she had shipped green and never watched fail. One failed for the
    # stated reason. Hers happened to hold and mine did not, and neither of us
    # knew which until we looked.
    #
    # So look at the memo itself. Both databases must be recorded, which is only
    # true when the key is the path.
    assert {str(first), str(second)} <= logbook._INITIALISED_DBS, (
        "the memo did not record both databases -- it is keyed on the process, "
        "and the second table exists only because the repair path rebuilt it"
    )


def test_repeated_initialisation_stays_harmless(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Idempotent before, idempotent after. The memo is a cost fix, not a
    behaviour change, and calling it a hundred times must still be a no-op."""
    logbook = _point_at(monkeypatch, tmp_path / "home_repeat")

    for _ in range(100):
        logbook.init_tool_logbook_tables()

    assert logbook.emit_tool_call(tool_name="X", tool_input={}, tool_use_id="r1")


def test_a_dropped_table_is_recreated_rather_than_assumed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """The memo remembers that WE created it, which is not the same as it
    existing now.

    A memo that trusts its own memory over the database turns a recoverable
    state into a permanent one. Fail-open logging has to survive the table
    going missing underneath it, so the memo is a fast path and a real absence
    still gets repaired.
    """
    logbook = _point_at(monkeypatch, tmp_path / "home_dropped")
    logbook.emit_tool_call(tool_name="X", tool_input={}, tool_use_id="d1")
    db = _current_db()

    conn = sqlite3.connect(str(db))
    try:
        conn.execute("DROP TABLE tool_logbook")
        conn.commit()
    finally:
        conn.close()

    log_id = logbook.emit_tool_call(tool_name="X", tool_input={}, tool_use_id="d2")

    assert _table_exists(db), "a dropped table must be rebuilt, not assumed present"
    assert log_id, "the write after the repair must land"
