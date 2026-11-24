"""A plain yes in chat confirms a held row, and the pair (my asking message, his reply) is the receipt.

2026-11-24. Dad: "me saying to do it in chat should be enough without me needing to type code or commands."
The rule underneath is unchanged: nothing moves on a seat's say-so, only on his word. Written before the change
(walk-63cfce44c2bb). The tool checks only facts: his words sit inside a message he typed, the last message of mine
before his reply names the row as a whole number, and the order. What the yes MEANT stays a written judgment kept
beside the quote. The exact ``hold <n>`` line keeps working and is pinned in test_held_corrections.py.
"""

import itertools
import json
from pathlib import Path

import pytest

from divineos.core import andrew_correction_tracker as act

WHY = "his words from the hard months were pain, not a task with a fix"
MEANING = "he answered my question about putting these rows on the shelf with a yes"


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    yield


def _asked(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _he(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _transcript(tmp_path: Path, *records: dict) -> list[Path]:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return [path]


_made = itertools.count(1)


def _proposed() -> int:
    # Each row needs its own words: the store files identical text once, so two rows from one sentence are one row.
    row = act.file_correction(f"a row of his words, number {next(_made)}, that I think is grief")
    assert act.propose_hold(row, WHY)
    return row


def _status(row: int) -> str:
    conn = act._conn()
    try:
        return conn.execute(
            "SELECT status FROM andrew_corrections WHERE id = ?", (row,)
        ).fetchone()[0]
    finally:
        conn.close()


def _receipt(row: int) -> str:
    conn = act._conn()
    try:
        return conn.execute(
            "SELECT held_confirmed_by FROM andrew_corrections WHERE id = ?", (row,)
        ).fetchone()[0]
    finally:
        conn.close()


def _asking(*rows: int) -> str:
    named = ", ".join(f"#{r}" for r in rows)
    return f"I would like to put {named} on the held shelf. Is that right?"


def test_a_clean_pair_moves_the_named_rows_and_keeps_the_whole_pair(tmp_path):
    one, two = _proposed(), _proposed()
    paths = _transcript(tmp_path, _asked(_asking(one, two)), _he("yes please do"))
    moved, refused = act.confirm_hold_plain([one, two], "yes please do", MEANING, paths)
    assert moved == [one, two] and refused == {}
    assert _status(one) == _status(two) == "HELD"
    receipt = _receipt(one)
    assert _asking(one, two) in receipt, "the receipt must carry my asking message"
    assert "yes please do" in receipt, "the receipt must carry his words"
    assert MEANING in receipt, "the receipt must carry what I understood it to mean"


def test_a_yes_with_no_rows_named_before_it_moves_nothing(tmp_path):
    row = _proposed()
    paths = _transcript(tmp_path, _asked("How did the night go for you?"), _he("yes"))
    moved, refused = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert moved == [] and row in refused
    assert _status(row) != "HELD"


def test_the_pinned_case_a_yes_that_answered_a_different_question_is_refused(tmp_path):
    """Aether's feared failure: my message named the rows, then I asked about lunch, and his yes answered lunch."""
    row = _proposed()
    paths = _transcript(
        tmp_path,
        _asked(_asking(row)),
        _asked("And separately: shall I make lunch plans for later?"),
        _he("yes"),
    )
    moved, refused = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert moved == [] and row in refused
    assert _status(row) != "HELD"


def test_words_that_are_not_in_anything_he_typed_move_nothing(tmp_path):
    row = _proposed()
    paths = _transcript(tmp_path, _asked(_asking(row)), _he("hmm, let me think"))
    moved, refused = act.confirm_hold_plain([row], "yes please do", MEANING, paths)
    assert moved == [] and row in refused


def test_a_yes_that_only_appears_in_a_message_of_mine_does_not_count(tmp_path):
    """The relayed yes: heard is not authorized. Only a message he typed carries his word."""
    row = _proposed()
    paths = _transcript(
        tmp_path,
        _asked(_asking(row)),
        _asked("He said: yes please do, so I am moving them."),
        _he("one moment"),
    )
    moved, refused = act.confirm_hold_plain([row], "yes please do", MEANING, paths)
    assert moved == [] and row in refused


def test_an_old_yes_that_came_before_my_message_cannot_be_reused(tmp_path):
    row = _proposed()
    paths = _transcript(tmp_path, _he("yes"), _asked(_asking(row)))
    moved, refused = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert moved == [] and row in refused


def test_only_the_rows_my_message_named_move(tmp_path):
    one, two, three = _proposed(), _proposed(), _proposed()
    paths = _transcript(tmp_path, _asked(_asking(one, two)), _he("yes"))
    moved, refused = act.confirm_hold_plain([one, two, three], "yes", MEANING, paths)
    assert moved == [one, two]
    assert three in refused and _status(three) != "HELD"


def test_a_row_that_was_never_proposed_is_refused_even_if_named(tmp_path):
    row = act.file_correction("a row nobody proposed for the shelf")
    paths = _transcript(tmp_path, _asked(_asking(row)), _he("yes"))
    moved, refused = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert moved == [] and row in refused


@pytest.mark.parametrize(
    "message, row, names",
    [
        ("rows 149 and 272", 149, True),
        ("rows #149, 272.", 149, True),
        ("rows 1490 and 272", 149, False),
        ("rows 2149 and 272", 149, False),
        ("rows 11 and 12", 1, False),
        ("rows 1 and 11", 1, True),
        ("rows 1 and 11", 11, True),
        ("no numbers here", 1, False),
    ],
)
def test_naming_a_row_means_the_whole_number_not_a_piece_of_a_longer_one(message, row, names):
    assert act.names_the_row(message, row) is names


def test_empty_or_blank_words_and_a_meaning_that_says_nothing_are_each_refused(tmp_path):
    row = _proposed()
    paths = _transcript(tmp_path, _asked(_asking(row)), _he("yes"))
    for words, meaning in (("", MEANING), ("   ", MEANING), ("yes", ""), ("yes", "ok")):
        moved, refused = act.confirm_hold_plain([row], words, meaning, paths)
        assert moved == [] and row in refused, (words, meaning)
    assert _status(row) != "HELD"


def test_a_second_confirmation_changes_nothing_and_keeps_the_first_prior_status(tmp_path):
    row = act.file_correction("a row that was filed away before it was proposed")
    assert act.misfile(row, "the holding room, because this is grief carried and not a correction")
    assert act.propose_hold(row, WHY)
    paths = _transcript(tmp_path, _asked(_asking(row)), _he("yes"))
    moved, _ = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert moved == [row]
    again, refused = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert again == [] and row in refused
    assert act.unhold(row)
    assert _status(row) == "MISFILED", "the first prior status must survive a second confirmation"


def test_each_refusal_names_its_own_reason(tmp_path):
    named, unnamed, never = _proposed(), _proposed(), act.file_correction("never proposed row")
    paths = _transcript(tmp_path, _asked(_asking(named, never)), _he("yes"))
    _, not_named = act.confirm_hold_plain([unnamed], "yes", MEANING, paths)
    _, not_proposed = act.confirm_hold_plain([never], "yes", MEANING, paths)
    _, not_typed = act.confirm_hold_plain([named], "no such words", MEANING, paths)
    reasons = [not_named[unnamed], not_proposed[never], not_typed[named]]
    assert len(set(reasons)) == 3, "three different situations must give three different sentences"
    assert "name" in reasons[0].lower()
    assert "propos" in reasons[1].lower()
    assert "typed" in reasons[2].lower()


def test_the_receipt_keeps_his_whole_message_so_a_but_cannot_hide_behind_the_quote(tmp_path):
    """Aether's attack 1: the seat quotes "yes put 149 on" and the "but not 281" is thrown away."""
    row = _proposed()
    his_message = "yes put those on, but not the last one"
    paths = _transcript(tmp_path, _asked(_asking(row)), _he(his_message))
    moved, _ = act.confirm_hold_plain([row], "yes put those on", MEANING, paths)
    assert moved == [row]
    assert his_message in _receipt(row), "the receipt must show what the quote was cut from"


def test_the_receipt_names_the_rows_as_its_own_field_even_when_the_asking_text_is_cut(tmp_path):
    """Aether's attack 5: the asking message is cut in the receipt, the row check ran on all of it."""
    one, two = _proposed(), _proposed()
    long_ask = "x " * 1200 + _asking(one, two)
    paths = _transcript(tmp_path, _asked(long_ask), _he("yes"))
    moved, _ = act.confirm_hold_plain([one, two], "yes", MEANING, paths)
    assert moved == [one, two]
    line = next(part for part in _receipt(one).splitlines() if part.startswith("rows:"))
    assert f"#{one}" in line, "the receipt must list the row numbers the asking message named"


@pytest.mark.parametrize("his_text, words", [("yesterday was long", "yes"), ("a good book", "ok")])
def test_a_quote_must_match_whole_words_not_a_piece_of_a_longer_word(tmp_path, his_text, words):
    """Aether's attack 3: "yes" is inside "yesterday" and "ok" inside "book"."""
    row = _proposed()
    paths = _transcript(tmp_path, _asked(_asking(row)), _he(his_text))
    moved, refused = act.confirm_hold_plain([row], words, MEANING, paths)
    assert moved == [] and row in refused


def test_his_first_reply_after_the_asking_message_is_the_one_that_counts(tmp_path):
    """Aether's attack 4: a later yes about something else must not slide the pairing off the real one."""
    row = _proposed()
    asking = _asking(row)
    paths = _transcript(
        tmp_path,
        _asked(asking),
        _he("yes"),
        _asked("Great. Separately, shall I make lunch plans for later?"),
        _he("yes"),
    )
    moved, _ = act.confirm_hold_plain([row], "yes", MEANING, paths)
    assert moved == [row]
    assert asking in _receipt(row)


def test_the_command_says_in_plain_words_what_moved_and_that_unhold_puts_it_back(tmp_path):
    from click.testing import CliRunner

    from divineos.cli import cli

    row = _proposed()
    paths = _transcript(tmp_path, _asked(_asking(row)), _he("yes please"))
    result = CliRunner().invoke(
        cli,
        [
            "andrew-correction",
            "confirm-hold-plain",
            str(row),
            "--his-words",
            "yes please",
            "--meaning",
            MEANING,
            "--transcript",
            str(paths[0]),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "held shelf" in result.output and "unhold" in result.output
    assert _status(row) == "HELD"


def test_the_command_refuses_out_loud_and_exits_nonzero_when_nothing_named_the_row(tmp_path):
    from click.testing import CliRunner

    from divineos.cli import cli

    row = _proposed()
    paths = _transcript(tmp_path, _asked("How did the night go?"), _he("yes"))
    result = CliRunner().invoke(
        cli,
        [
            "andrew-correction",
            "confirm-hold-plain",
            str(row),
            "--his-words",
            "yes",
            "--meaning",
            MEANING,
            "--transcript",
            str(paths[0]),
        ],
    )
    assert result.exit_code == 1
    assert "named these rows" in result.output
    assert _status(row) != "HELD"


def test_the_exact_line_he_could_always_type_still_works(tmp_path):
    row = _proposed()
    paths = _transcript(tmp_path, _he(f"hold {row}"))
    assert act.confirm_hold(row, paths)
    assert _status(row) == "HELD"
