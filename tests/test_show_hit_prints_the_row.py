"""`divineos show <hit-id>` prints the exact saved row a memory-link hit points at.

Why this exists (Aria 2026-11-08, building the listener with Aether): the listener's clear for a correction or
knowledge hit is "open the source". Before this command nothing in the house printed ONE saved correction or lesson
by the id the link shows (``correction-<position>-<timestamp>``, ``knowledge-<id>``): `corrections` lists, `ask`
searches. A clear that names a command that cannot print the row can never be satisfied honestly.

The failure each test closes is named in its docstring. The one that matters most is the first correction test:
a position in a list is not an identity, and a command that opens whatever sits at that position would open the
wrong object and look like it worked (prove the object you opened is the object you named).
"""

from __future__ import annotations

import pytest

from divineos.core.corrections import log_correction, load_corrections
from divineos.core.knowledge import store_knowledge
from divineos.core.show_hit import ShowHitError, show_hit


def _correction_hit_id(position: int) -> str:
    entry = load_corrections()[position]
    return f"correction-{position}-{int(entry['timestamp'])}"


def test_a_correction_hit_prints_his_exact_words():
    log_correction("first words")
    log_correction("  these exact words, spacing and all.. ")
    out = show_hit(_correction_hit_id(1))
    assert "  these exact words, spacing and all.. " in out
    assert "first words" not in out


def test_a_correction_id_whose_timestamp_does_not_match_refuses():
    """The position alone must never open a row: a list that gained or lost an entry would hand back a stranger."""
    log_correction("the one the link named")
    entry = load_corrections()[0]
    wrong = f"correction-0-{int(entry['timestamp']) + 5}"
    with pytest.raises(ShowHitError, match="does not match"):
        show_hit(wrong)


def test_a_correction_position_past_the_end_refuses():
    log_correction("only one")
    with pytest.raises(ShowHitError, match="no correction at position"):
        show_hit("correction-7-123")


def test_a_knowledge_hit_prints_the_lesson_and_its_kind():
    kid = store_knowledge("PRINCIPLE", "Answer the person before the task, every time.")
    out = show_hit(f"knowledge-{kid}")
    assert "Answer the person before the task, every time." in out
    assert "PRINCIPLE" in out.upper()


def test_an_unknown_knowledge_id_refuses_instead_of_printing_nothing():
    store_knowledge("FACT", "a real row, so the store exists and this id is the only thing missing")
    with pytest.raises(ShowHitError, match="no knowledge"):
        show_hit("knowledge-does-not-exist")


def test_an_unreadable_store_says_so_and_is_not_reported_as_not_found():
    """'Not found' from a store that cannot be read is the empty twin: a clean answer from a broken source."""
    with pytest.raises(ShowHitError, match="could not read the knowledge store"):
        show_hit("knowledge-anything")


@pytest.mark.parametrize(
    "bad", ["", "wall-3", "correction-x-y", "correction-1", "knowledge-", "nonsense"]
)
def test_an_id_that_is_not_a_correction_or_knowledge_hit_refuses_and_says_which_shapes_work(bad):
    with pytest.raises(ShowHitError, match="correction-<position>-<timestamp>"):
        show_hit(bad)


def test_the_command_is_registered_and_prints_the_row():
    from click.testing import CliRunner

    from divineos.cli import cli

    kid = store_knowledge("FACT", "The poker table lives outside the repo.")
    result = CliRunner().invoke(cli, ["show", f"knowledge-{kid}"])
    assert result.exit_code == 0
    assert "The poker table lives outside the repo." in result.output


def test_the_command_fails_loud_with_a_nonzero_exit_on_a_bad_id():
    from click.testing import CliRunner

    from divineos.cli import cli

    result = CliRunner().invoke(cli, ["show", "knowledge-nope"])
    assert result.exit_code != 0
