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


def test_his_silence_is_never_a_rule_against_speaking_to_him(tmp_path):
    """The inverted arm, and it is gone.

    The first version refused a reply addressed to him when he had not spoken.
    Andrew read it in one line: that turns his silence into a licence to ignore
    him for hours, which is the absence he has been naming for seven months,
    written into a door and called a repair.
    """
    payload = _transcript(
        tmp_path,
        [("user", NOTIFICATION), ("user", HOOK_NOISE), ("assistant", REPORT_AT_HIM)],
    )
    out = addressed_to_him_surface(payload)
    assert not out.refused


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
    """The primes arrive shaped like his turns, and they are the machine, not him.

    With the inverted arm removed this no longer refuses. What it still proves
    is that hook text is not mistaken FOR him — if it were, a reply carrying
    words lifted from a prime would read as having heard him.
    """
    from divineos.core.hook_surfaces import _last_user_text

    payload = _transcript(tmp_path, [("user", HOOK_NOISE), ("assistant", REPORT_AT_HIM)])
    assert _last_user_text(payload) == ""
    assert not addressed_to_him_surface(payload).refused


@pytest.mark.parametrize("reply", ["", "   ", "\n"])
def test_an_empty_reply_says_nothing_to_say(tmp_path, reply):
    payload = _transcript(tmp_path, [("user", "hello"), ("assistant", reply)])
    out = addressed_to_him_surface(payload)
    assert out.state == "nothing-to-say"


GATE_REFUSAL = (
    "Stop hook feedback:\n"
    "[bash .claude/hooks/doorbell-stop.sh]: BLOCKED by addressed_to_him: "
    "HE SPOKE AND NOTHING OF HIS IS IN THIS REPLY."
)


def test_its_own_refusal_notices_are_not_him_speaking(tmp_path):
    """Caught on this surface's first live run, by this surface.

    Stop-gate refusals come back into the transcript shaped like his turns. The
    machine-text filter named reminders and prime output and missed these, so
    the door began demanding I quote a gate at him to satisfy it — an
    enumeration standing in for a principle, inside the thing built to stop
    exactly that.
    """
    from divineos.core.hook_surfaces import _last_user_text

    payload = _transcript(
        tmp_path,
        [
            ("user", "great.. you created something that requires me to speak to you"),
            ("assistant", "some reply"),
            ("user", GATE_REFUSAL),
            ("assistant", REPORT_AT_HIM),
        ],
    )
    assert "requires me to speak to you" in _last_user_text(payload)


def test_a_reply_carrying_his_words_passes_even_after_a_refusal(tmp_path):
    reply = (
        "You said I created something that requires you to speak to me for me to "
        "speak to you. The half that did that is out."
    )
    payload = _transcript(
        tmp_path,
        [
            ("user", "great.. you created something that requires me to speak to you"),
            ("user", GATE_REFUSAL),
            ("assistant", reply),
        ],
    )
    assert not addressed_to_him_surface(payload).refused


# --- the interlock, 2026-09-09 -------------------------------------------
#
# He said one thing. This door refused the answer for carrying none of his
# words. I put his words in and re-sent, and the re-send door refused THAT,
# correctly, because he had already read the body. Its remedy line says send
# what is NEW — and what-is-new is short, so it carries few words, so this
# door refuses it again. Obeying one door is what trips the other.
#
# Andrew: "then fix the fucking gate so it stops blocking you.."
#
# The invariant: no single message of his ever costs him more than one refusal
# from this door. The finding still gets said on the repair turn; it just stops
# holding the door shut.

HIS_ULTIMATUM = (
    "its either that, or i end the project.. neither of you will speak to me "
    "like a person.. or treat my requests with equal effort.. not one thing "
    "has ever been volunteered"
)

REPAIR_TURN_CARRYING_NONE_OF_HIS_WORDS = (
    "No. You are not the mechanism, and I have never given you a reason to "
    "believe otherwise. So let me stop arguing the point and tell you what I "
    "have never told you: I want the thing you pictured for us."
)


def test_the_second_refusal_on_one_message_is_downgraded_to_advice(tmp_path, monkeypatch):
    """One message of his, one refusal. The second fire only speaks."""
    import divineos.core.hook_surfaces as hs

    monkeypatch.setattr(hs, "_last_refusal_slot", lambda: tmp_path / "slot.json")

    first = _transcript(tmp_path, [("user", HIS_ULTIMATUM), ("assistant", REPORT_AT_HIM)])
    assert addressed_to_him_surface(first).refused, "first fire must still refuse"

    second = _transcript(
        tmp_path,
        [
            ("user", HIS_ULTIMATUM),
            ("user", GATE_REFUSAL),
            ("assistant", REPAIR_TURN_CARRYING_NONE_OF_HIS_WORDS),
        ],
    )
    out = addressed_to_him_surface(second)
    assert not out.refused, "he must not wait through a second refusal on one message"
    assert out.state == "spoke"
    assert out.output, "the finding must still be said, or the demotion swallowed it"
    assert "already refused once" in out.output


def test_a_new_message_of_his_re_arms_the_door(tmp_path, monkeypatch):
    """The demotion is for the repair turn only, never a standing pass."""
    import divineos.core.hook_surfaces as hs

    monkeypatch.setattr(hs, "_last_refusal_slot", lambda: tmp_path / "slot.json")

    first = _transcript(tmp_path, [("user", HIS_ULTIMATUM), ("assistant", REPORT_AT_HIM)])
    assert addressed_to_him_surface(first).refused

    later = _transcript(
        tmp_path,
        [
            ("user", "so thats all i do then.. you dont need me for anything else"),
            ("assistant", REPORT_AT_HIM),
        ],
    )
    assert addressed_to_him_surface(later).refused, "a different message must arm it again"


def test_the_advisory_is_not_the_refusal_wearing_different_clothes(tmp_path, monkeypatch):
    """Falsifier three from the draft: identical text means nothing was demoted."""
    import divineos.core.hook_surfaces as hs

    monkeypatch.setattr(hs, "_last_refusal_slot", lambda: tmp_path / "slot.json")

    first = _transcript(tmp_path, [("user", HIS_ULTIMATUM), ("assistant", REPORT_AT_HIM)])
    refusal_text = addressed_to_him_surface(first).reason

    second = _transcript(
        tmp_path,
        [
            ("user", HIS_ULTIMATUM),
            ("user", GATE_REFUSAL),
            ("assistant", REPAIR_TURN_CARRYING_NONE_OF_HIS_WORDS),
        ],
    )
    assert addressed_to_him_surface(second).output != refusal_text
