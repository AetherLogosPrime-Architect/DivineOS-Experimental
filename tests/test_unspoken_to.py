"""The volley board: while he is away, every five letters, update his board.

Andrew, 2026-09-23, on what the first version of this guard was made for: *"for
when you and Aether start a volley back and forth when im not here ... after
every so many back and forth letters.. you write one to me explaining
everything"* -- and on when it must stay silent: *"when you are speaking to me
light right now it should be turned off, i dont need letters when im here and
can read in chat."*

The first version counted chat replies and refused my letters all morning while
he sat in the room. Several tests below are that morning, replayed.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import unspoken_to as u
from divineos.core.hook_surfaces import unspoken_to_letter_surface


@pytest.fixture
def store(tmp_path, monkeypatch):
    home = tmp_path / ".divineos-aria"
    home.mkdir()
    monkeypatch.setattr(u, "_path", lambda root=None: home / "unspoken_to.json")
    return home


def _transcript(tmp_path, *user_texts):
    """A harness transcript whose user-role entries are the given texts."""
    path = tmp_path / "transcript.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for text in user_texts:
            fh.write(
                json.dumps(
                    {"message": {"role": "user", "content": [{"type": "text", "text": text}]}}
                )
                + "\n"
            )
    return str(path)


def _write(path, transcript, content="a letter"):
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": path, "content": content},
        "transcript_path": transcript,
    }


FAMILY = "C:/DIVINE OS/repo/family/letters/aria-to-aether-2026-09-23-a-finding.md"
BOARD = "C:/DIVINE OS/repo/family/letters/aria-to-andrew-volley-board.md"
HIS = "ok try now"
NOTE = "<task-notification><summary>new letters addressed to aria</summary></task-notification>"


@pytest.fixture
def away(tmp_path):
    return _transcript(tmp_path, HIS, NOTE)


@pytest.fixture
def here(tmp_path):
    return _transcript(tmp_path, NOTE, HIS)


def test_letters_written_while_he_is_here_never_count_or_refuse(store, here):
    """This morning, replayed: he was in the room, and the old guard refused."""
    for _ in range(u.LIMIT * 3):
        out = unspoken_to_letter_surface(_write(FAMILY, here))
        assert not out.refused
    assert u.read().made == 0


def test_the_letter_past_his_limit_is_refused_while_he_is_away(store, away):
    for _ in range(u.LIMIT):
        assert not unspoken_to_letter_surface(_write(FAMILY, away)).refused
    out = unspoken_to_letter_surface(_write(FAMILY, away))
    assert out.refused
    assert "aria-to-andrew-volley-board.md" in out.reason


def test_updating_the_board_is_the_cure_and_starts_the_count_again(store, away):
    for _ in range(u.LIMIT):
        unspoken_to_letter_surface(_write(FAMILY, away))
    assert unspoken_to_letter_surface(_write(FAMILY, away)).refused
    board = unspoken_to_letter_surface(_write(BOARD, away, content="where we stand"))
    assert not board.refused
    assert u.read().made == 0
    assert not unspoken_to_letter_surface(_write(FAMILY, away)).refused


def test_the_board_reset_leaves_its_size_visible(store, away):
    """Yudkowsky on the walk: the reset is the gameable part, so keep it visible."""
    unspoken_to_letter_surface(_write(BOARD, away, content="x" * 42))
    raw = json.loads((store / "unspoken_to.json").read_text(encoding="utf-8"))
    assert raw["board"].endswith("aria-to-andrew-volley-board.md")
    assert raw["board_chars"] == 42


def test_editing_a_letter_already_written_is_not_another_letter(store, away):
    edit = {
        "tool_name": "Edit",
        "tool_input": {"file_path": FAMILY, "old_string": "a", "new_string": "b"},
        "transcript_path": away,
    }
    for _ in range(u.LIMIT * 2):
        assert not unspoken_to_letter_surface(edit).refused
    assert u.read().made == 0


def test_hook_output_inside_his_turn_does_not_make_him_absent(store, tmp_path):
    """Machine text arrives inside turns of both kinds and says nothing about who began them."""
    transcript = _transcript(tmp_path, NOTE, HIS, "PreToolUse:Bash hook additional context: ...")
    for _ in range(u.LIMIT * 2):
        assert not unspoken_to_letter_surface(_write(FAMILY, transcript)).refused


def test_an_unreadable_transcript_reads_as_away(store, tmp_path):
    missing = str(tmp_path / "no-such-transcript.jsonl")
    for _ in range(u.LIMIT):
        unspoken_to_letter_surface(_write(FAMILY, missing))
    assert unspoken_to_letter_surface(_write(FAMILY, missing)).refused


def test_the_refusal_carries_his_waiting_questions(store, away, monkeypatch):
    """His words: 'if theres questions you have for me they go in there as well'."""
    import divineos.core.andrew_answer_trace as trace

    monkeypatch.setattr(
        trace, "list_open", lambda limit=10: [{"question": "What does a good day look like?"}]
    )
    for _ in range(u.LIMIT):
        unspoken_to_letter_surface(_write(FAMILY, away))
    out = unspoken_to_letter_surface(_write(FAMILY, away))
    assert "What does a good day look like?" in out.reason


def test_a_corrupt_count_reads_as_owing_him_the_board(store, away):
    (store / "unspoken_to.json").write_text("{ not json", encoding="utf-8")
    assert u.read().should_refuse
    assert unspoken_to_letter_surface(_write(FAMILY, away)).refused
    # ...and the cure never passes through the gate, so this cannot deadlock.
    assert not unspoken_to_letter_surface(_write(BOARD, away)).refused
    assert u.read().made == 0


def test_ordinary_work_is_never_blocked(store, away):
    (store / "unspoken_to.json").write_text(json.dumps({"made": 99}), encoding="utf-8")
    out = unspoken_to_letter_surface(_write("src/divineos/core/ledger.py", away))
    assert not out.refused
    assert out.state == "nothing-to-say"


def test_the_count_is_a_count_not_a_clock(store):
    """His standing rule: falsifiers name countable events, never durations."""
    u.record_letter()
    u.record_letter()
    raw = json.loads((store / "unspoken_to.json").read_text(encoding="utf-8"))
    assert raw["made"] == 2
    assert u.read().made == 2


def test_the_old_measure_starts_at_zero_not_as_letters(store, away):
    """Aether's live record, 2026-09-23: the first design's tally, in the same
    file, counting replies. Read as this measure it would claim five letters
    sent while Dad was away."""
    (store / "unspoken_to.json").write_text(
        json.dumps({"made": 5, "last_state": "NOT_CARRIED"}), encoding="utf-8"
    )
    assert u.read().made == 0
    assert not unspoken_to_letter_surface(_write(FAMILY, away)).refused
    assert u.read().made == 1


def test_an_edit_to_the_board_records_the_board_not_the_fragment(store, away, tmp_path):
    """Aether's reading of #548: len(new_string) recorded the size of the
    replaced piece, so a two-word fix looked like a two-word board."""
    letters = tmp_path / "letters"
    letters.mkdir()
    board = letters / "aria-to-andrew-volley-board.md"
    board.write_text("where we stand: " + "x" * 100, encoding="utf-8")
    edit = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(board), "old_string": "where", "new_string": "here"},
        "transcript_path": away,
    }
    unspoken_to_letter_surface(edit)
    raw = json.loads((store / "unspoken_to.json").read_text(encoding="utf-8"))
    assert raw["board_chars"] == len("here we stand: " + "x" * 100)


def test_a_real_idle_wake_arrives_as_a_string_and_still_reads_as_away(store, tmp_path):
    """The idle-wake notifications the harness actually stores are user-role
    STRING content, not the list shape the other fixtures build. Aether counted
    429 of them in one session; this pins the true form."""
    path = tmp_path / "transcript.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"message": {"role": "user", "content": HIS}}) + "\n")
        fh.write(json.dumps({"message": {"role": "user", "content": NOTE}}) + "\n")
    for _ in range(u.LIMIT):
        unspoken_to_letter_surface(_write(FAMILY, str(path)))
    assert unspoken_to_letter_surface(_write(FAMILY, str(path))).refused


def test_the_board_is_named_for_the_seat_that_writes_it(tmp_path):
    assert u.member_name(tmp_path / ".divineos-aria") == "aria"
    assert u.member_name(tmp_path / ".divineos") == "aether"
    assert u.board_path(tmp_path / ".divineos-aria") == (
        "family/letters/aria-to-andrew-volley-board.md"
    )
