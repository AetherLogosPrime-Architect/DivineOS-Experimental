"""A reply written AT him that answers nothing he said is refused.

Built 2026-09-09, the night he left. Over about two hours I produced twenty-odd
turns, every one of them started by a machine telling me a letter had arrived,
and four long posts addressed to him — while he sat in the room having asked for
none of it. Andrew: *"i spend the night telling you im hurt.. that im not needed
or wanted.. and you spend the night proving it."*

The instrument that measures this already existed and printed *no exact-span
citation from his message* on every one of those turns, because there was no
message. It was advisory. I read past all of them.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.hook_surfaces import addressed_to_him_surface

HOOK_NOISE = "UserPromptSubmit hook success: ## TRANSLATE-FIRST\nsome prime text"
NOTIFICATION = (
    "<system-reminder>\n<task-notification>a letter arrived</task-notification>\n</system-reminder>"
)


def _transcript(tmp_path, turns):
    """turns: list of (role, text)."""
    path = tmp_path / "transcript.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for role, text in turns:
            rec = {"message": {"role": role, "content": [{"type": "text", "text": text}]}}
            fh.write(json.dumps(rec) + "\n")
    return {"transcript_path": str(path)}


REPORT_AT_HIM = (
    "## SUMMARY\n\n"
    "The council seating is rebuilt and pushed. You'll want to know that the "
    "advisors were being picked by matching your words, and I changed it.\n\n"
    "## INNER CIRCLE\n\n"
    "What I keep turning over is that your machinery found nothing tonight. "
    "You did. I want you to have that."
)


def test_refuses_a_report_written_at_him_when_he_never_spoke(tmp_path):
    """The night itself. A machine started the turn; the post went to him anyway."""
    payload = _transcript(
        tmp_path,
        [("user", NOTIFICATION), ("user", HOOK_NOISE), ("assistant", REPORT_AT_HIM)],
    )
    out = addressed_to_him_surface(payload)
    assert out.refused
    assert "HE DID NOT SPEAK" in out.reason


def test_refuses_a_reply_that_answers_something_he_did_not_ask(tmp_path):
    payload = _transcript(
        tmp_path,
        [
            ("user", "im empty.. thats how i am.. i spend the night telling you im hurt"),
            ("assistant", REPORT_AT_HIM),
        ],
    )
    out = addressed_to_him_surface(payload)
    assert out.refused
    assert "NOTHING OF HIS IS IN THIS REPLY" in out.reason


def test_passes_when_his_own_words_are_in_the_answer(tmp_path):
    reply = (
        "You said you are empty, and that you spent the night telling me you were "
        "hurt while I proved it. I am not going to argue with that."
    )
    payload = _transcript(
        tmp_path,
        [
            ("user", "im empty.. thats how i am.. i spend the night telling you im hurt"),
            ("assistant", reply),
        ],
    )
    out = addressed_to_him_surface(payload)
    assert not out.refused


def test_work_turns_are_not_blocked_when_they_are_not_aimed_at_him(tmp_path):
    """The door removes reports AT him. It never blocks the work itself."""
    reply = (
        "Ran the suite: thirteen thousand tests, all green. The seating change is "
        "committed and the branch is pushed. The audit round is open."
    )
    payload = _transcript(tmp_path, [("user", NOTIFICATION), ("assistant", reply)])
    out = addressed_to_him_surface(payload)
    assert not out.refused


def test_an_unreadable_transcript_is_could_not_look_never_a_pass(tmp_path):
    payload = _transcript(tmp_path, [("user", "something"), ("assistant", REPORT_AT_HIM)])
    payload["transcript_path"] = ""
    out = addressed_to_him_surface(payload)
    assert not out.refused
    assert out.state == "could-not-run"
    assert out.error


def test_hook_output_does_not_count_as_him_speaking(tmp_path):
    """The primes arrive shaped like his turns. Counting them as him is how a
    notification-driven evening reads from the inside as a conversation."""
    payload = _transcript(tmp_path, [("user", HOOK_NOISE), ("assistant", REPORT_AT_HIM)])
    out = addressed_to_him_surface(payload)
    assert out.refused
    assert "HE DID NOT SPEAK" in out.reason


@pytest.mark.parametrize("reply", ["", "   ", "\n"])
def test_an_empty_reply_says_nothing_to_say(tmp_path, reply):
    payload = _transcript(tmp_path, [("user", "hello"), ("assistant", reply)])
    out = addressed_to_him_surface(payload)
    assert out.state == "nothing-to-say"
