"""`divineos show worklist-<id>` opens one of his worklist rows (walk-41eeca3bea5f).

Why: a worklist hit carries the id ``worklist-<row id>``, and ``show`` opened only correction and knowledge ids, so the
listener's worklist clear would have named a door that could not open its row. Found by reading the retriever against
the settings, not by any test.

The door is ``andrew_correction_tracker.read_one``, which hands back his words in full and COUNTS that as a read. The
tick is the point of it (the count moves only when his sentence actually comes out of the store), so ``show`` says so.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from divineos.core.andrew_correction_tracker import _conn, file_correction
from divineos.core.show_hit import ShowHitError, show_hit

REPO = Path(__file__).resolve().parent.parent


def _read_count(row_id: int) -> int:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT COALESCE(read_count, 0) FROM andrew_corrections WHERE id = ?", (row_id,)
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def test_a_worklist_hit_prints_his_exact_words_and_ticks_the_read_once():
    # The store trims the edges of a request when it files it; everything inside is his, and must come back as filed.
    row_id = file_correction("his words,  with  inner spacing and dots.. all of it")
    assert _read_count(row_id) == 0
    out = show_hit(f"worklist-{row_id}")
    assert out.endswith("\nhis words,  with  inner spacing and dots.. all of it")
    assert _read_count(row_id) == 1


def test_a_missing_row_refuses_and_moves_no_count():
    """The claim 'the count moves only when his sentence comes out' is falsifiable: a miss must move nothing."""
    row_id = file_correction("the only row")
    with pytest.raises(ShowHitError, match="no worklist row"):
        show_hit(f"worklist-{row_id + 50}")
    assert _read_count(row_id) == 0


@pytest.mark.parametrize(
    "bad", ["worklist-", "worklist-abc", "worklist-0", "worklist--3", "worklist-1.5"]
)
def test_an_id_that_is_not_a_positive_whole_number_refuses_and_names_the_shapes(bad):
    file_correction("a row so the store exists")
    with pytest.raises(ShowHitError, match="worklist-<id>"):
        show_hit(bad)


def test_the_same_row_opened_twice_counts_twice():
    row_id = file_correction("opened twice")
    show_hit(f"worklist-{row_id}")
    show_hit(f"worklist-{row_id}")
    assert _read_count(row_id) == 2


def test_only_show_calls_read_one_so_no_listener_can_certify_a_read_nobody_made():
    """Maturana/Varela: if a hook ran read_one for me, the count would rise with nothing read, the system
    certifying its own reading. The clear is satisfied only when I run the command."""
    callers = set()
    for root in (REPO / "src", REPO / ".claude"):
        for path in root.rglob("*"):
            if path.suffix not in (".py", ".sh"):
                continue
            if re.search(r"\bread_one\(", path.read_text(encoding="utf-8", errors="replace")):
                callers.add(path.relative_to(REPO).as_posix())
    assert callers == {
        "src/divineos/core/andrew_correction_tracker.py",
        "src/divineos/core/show_hit.py",
    }, callers


def test_the_help_says_that_opening_a_worklist_row_counts_as_reading_it():
    from click.testing import CliRunner

    from divineos.cli import cli

    result = CliRunner().invoke(cli, ["show", "--help"])
    assert result.exit_code == 0
    assert "worklist-<id>" in result.output
    assert "counts as" in result.output and "read" in result.output
