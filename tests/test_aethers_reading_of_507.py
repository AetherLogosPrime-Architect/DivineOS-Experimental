"""Aether's station-four reading of the repacked #507, 2026-09-23, one test per finding.

Each was measured by him against real transcripts before he wrote it down, so
each test here is the case he measured, not a case invented to pass.
"""

from __future__ import annotations

from divineos.core import keeping_him, questions_from_him
from divineos.core.council import EXPECTED_EXPERT_COUNT


# Finding 2 -- the bookmark follows the running seat.
def test_the_read_through_bookmark_lives_in_the_running_seats_home(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert keeping_him.mark_path().parent == tmp_path / "data"


# Finding 3 -- a message he sent with an attachment is still him.
def test_a_message_with_an_attachment_is_his():
    entry = {
        "type": "user",
        "userType": "external",
        "message": {
            "role": "user",
            "content": [
                {"type": "text", "text": "there is nothing merged"},
                {"type": "image", "source": {"type": "base64", "data": "x"}},
            ],
        },
    }
    assert keeping_him.is_his(entry)
    assert keeping_him.content_text(entry) == "there is nothing merged"


def test_a_tool_result_is_still_not_him():
    entry = {
        "type": "user",
        "userType": "external",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}],
        },
    }
    assert not keeping_him.is_his(entry)


# Finding 5 -- the questions rotate by what he said, and marks match whole words.
def test_different_instruction_turns_do_not_all_get_the_same_two_stems():
    # Before the fix a one-sentence turn always took the FIRST stem, so every
    # turn below would have produced the same question. Chosen by a hash of his
    # words now, nine ordinary instruction turns reach all three.
    turns = [
        "please go read the letter aether wrote about the branches tonight",
        "build the thing for the board so my asks show up next to yours",
        "fix the monitor so it stops announcing old letters as new ones",
        "go message aletheia and ask her to check the seventeen smallest first",
        "make the digest actually get written when something lands for me",
        "can you read what aletheia sent about the seventeen",
        "please build the thing that files my asks by itself",
        "i want you to message aether about the folder",
        "go fix the letter watch so it stops knocking twice",
    ]
    stems = set()
    for turn in turns:
        assert questions_from_him.turn_shape(turn) == "instruction", turn
        for q in questions_from_him.questions(turn):
            stems.add(q.split(" -- ", 1)[1])
    assert len(stems) == len(questions_from_him._INSTRUCTION), stems


def test_carefully_is_not_a_feeling_and_function_is_not_fun():
    assert questions_from_him.turn_shape("read it carefully and fix the function") != "feeling"
    assert questions_from_him.turn_shape("this standalone module is broken") != "feeling"
    assert questions_from_him.turn_shape("i feel like nobody listens") == "feeling"


# Finding 6 -- one authority for the size of the council.
def test_the_full_council_is_the_one_constant():
    from divineos.core import no_fix_claim

    assert no_fix_claim.FULL_COUNCIL == EXPECTED_EXPERT_COUNT
