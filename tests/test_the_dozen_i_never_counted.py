"""The gate must fire on the sentence that caused it, and stay quiet elsewhere.

Pre-registration: prereg-34b60b20bf36.

THE REAL EVENT is the first test and the only one that would justify the build:
on 2026-09-11 I told Andrew the house held "maybe a dozen things" in a turn
where nothing ran, and he answered "a dozen things? so all of this time we have
built a dozen things?" If the gate does not fire on that, it is decoration
whatever else it passes.

The rest of the file is the falsifier's ground, per the pre-registration: the
predicted death is noise, so most of these tests assert SILENCE. A gate that
fires on clock times and on his own figures handed back gets switched off
inside a week, and then the prime tells me a second layer is covering me while
nothing is.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.unmeasured_quantity import (
    QuantityFinding,
    check_payload,
    find_unmeasured_quantities,
    render,
)


# ---------------------------------------------------------------- the incident


def test_the_dozen_fires():
    """The sentence that caused this gate."""
    reply = (
        "You are not as far behind as it feels. What is actually standing in "
        "this house is maybe a dozen things, and you could walk them in an "
        "afternoon."
    )
    finding = find_unmeasured_quantities(reply, "i wanted it to be as we were going")
    assert finding.state == "found"
    assert any("dozen" in f.lower() for f in finding.fragments)


def test_the_dozen_does_not_fire_if_i_actually_counted():
    """Same sentence, and the figure is in what I read. The control.

    Without this, a gate that fired on every quantity would pass the test above
    and I would have learned nothing about whether the measurement half of the
    predicate does any work at all.
    """
    reply = "What is actually standing in this house is maybe a dozen things."
    finding = find_unmeasured_quantities(reply, "", tools_ran=True, tool_output="count: 12 modules")
    assert finding.state == "found-nothing"


def test_an_unrelated_command_does_not_buy_a_number():
    """THE HOLE ANDREW SENT ME BACK FOR, asserted against.

    The first version short-circuited on 'did any tool run', so listing a
    directory bought me any figure I liked. Turing's lens: a check that cannot
    distinguish counting from not-counting is not a check. Here a real command
    ran and returned real output, and the figure is nowhere in it.
    """
    finding = find_unmeasured_quantities(
        "There are about fifty gates in this house now.",
        "",
        tools_ran=True,
        tool_output="README.md\nsetup.py\nsrc\ntests",
    )
    assert finding.state == "found"


def test_a_vague_quantity_is_held_even_when_commands_ran():
    """'several' has no value to trace, so nothing can vouch for it.

    Deliberate rather than a gap: these are the words the reach uses when it
    wants to sound measured without measuring.
    """
    finding = find_unmeasured_quantities(
        "several branches are still unlanded",
        "",
        tools_ran=True,
        tool_output="branch listing: main, gate/unmeasured-quantity",
    )
    assert finding.state == "found"


def test_the_message_carries_the_incident_not_a_rule():
    """A rule without its reason is a thing to route around."""
    out = render(find_unmeasured_quantities("about a dozen things are built"))
    assert "a dozen things" in out
    assert "living room" in out
    assert "COUNT IT" in out


def test_the_message_does_not_claim_no_tool_ran():
    """ADDED 2026-09-11 after the gate printed a falsehood about my own turn.

    The rebuild changed the predicate and left the old sentence -- "NO tool ran
    this turn" -- standing above it, so the thing built to catch me stating
    unchecked facts stated one itself. A test asserts the STATE and never reads
    the prose, which is why nothing caught it; this one reads the prose.
    """
    out = render(
        find_unmeasured_quantities(
            "about fifty gates are standing", tools_ran=True, tool_output="unrelated"
        )
    )
    assert "NO tool ran" not in out
    assert "does" in out and "not appear" in out


# ------------------------------------------------------------------- the noise


@pytest.mark.parametrize(
    "reply",
    [
        "I will look at it around 3:15 and report back.",
        "That correction was filed on 2026-09-11.",
        "The check is at v2.1.0 now.",
        "Cited in the commit as prereg-f79983d51516.",
    ],
)
def test_ordinary_numbers_stay_silent(reply):
    """The predicted death, asserted against.

    Each of these would fire a naive digits-plus-context detector, and each is
    a number that means nothing about how much is built.
    """
    assert find_unmeasured_quantities(reply).state == "found-nothing"


def test_his_own_number_fires_too_when_nothing_measured_it():
    """REVERSED 2026-09-11, and the reversal is the point.

    This test used to assert the opposite: that a figure appearing in his
    message was excused whatever I did with it. That guard was written to stop
    the gate firing while the two of us discuss a number he raised, and it made
    quoting him an unconditional pass.

    Traceability does that job properly now. So the honest expectation is that
    his number fires as well, until something I read vouches for it -- because
    a figure I restate as fact having checked nothing is my claim, not his.
    """
    his = "a dozen things? so all of this time we have built a dozen things?"
    reply = "A dozen things is about right for what is standing."
    assert find_unmeasured_quantities(reply, his).state == "found"


def test_his_number_is_quiet_once_something_measured_it():
    """The other half, so the reversal above is not just a stricter gate."""
    his = "a dozen things? so all of this time we have built a dozen things?"
    reply = "A dozen things is about right for what is standing."
    finding = find_unmeasured_quantities(
        reply, his, tools_ran=True, tool_output="modules standing: 12"
    )
    assert finding.state == "found-nothing"


def test_a_number_with_no_subject_is_prose():
    """'seven months' is a duration, not a count of what is built."""
    reply = "You have been at this for seven months and you are not behind."
    assert find_unmeasured_quantities(reply).state == "found-nothing"


# ------------------------------------------------- could-not-check is its own state


def test_a_missing_transcript_reports_could_not_check():
    finding = check_payload({})
    assert finding.state == "could-not-check"
    assert finding.should_warn


def test_an_unreadable_transcript_reports_could_not_check(tmp_path):
    finding = check_payload({"transcript_path": str(tmp_path / "nope.jsonl")})
    assert finding.state == "could-not-check"
    assert "could not be read" in finding.reason


def test_could_not_check_says_so_out_loud():
    """Silence must never be readable as a pass. This is the eviction lesson."""
    out = render(QuantityFinding("could-not-check", reason="the file was gone"))
    assert "COULD NOT CHECK" in out
    assert "not a pass" in out


def test_found_nothing_prints_nothing():
    assert render(QuantityFinding("found-nothing")) == ""


def test_an_invented_state_is_refused():
    with pytest.raises(ValueError):
        QuantityFinding("probably-fine")


# ------------------------------------------------------- end to end, real payload


def _turn(tmp_path, reply, user_text, tool_calls, tool_text=""):
    """A transcript in the harness's own shape, results included.

    The results are the part that matters now: the gate reads what commands
    handed back, not merely that commands existed.
    """
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": user_text}}),
    ]
    if tool_calls:
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "tool_use", "name": "Bash", "input": {}}],
                    },
                }
            )
        )
        lines.append(
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "content": tool_text},
                        ],
                    },
                }
            )
        )
    lines.append(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": reply}],
                },
            }
        )
    )
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"transcript_path": str(path)}


def test_end_to_end_fires_on_the_real_shape(tmp_path):
    """His actual message, and the reply that followed it.

    WRITTEN WRONG THE FIRST TIME, and the mistake is worth keeping in view. I
    put his OBJECTION -- "a dozen things? so all of this time" -- in as the
    prior message, and the his-own-words guard then suppressed the very
    incident the gate exists for. But his objection came AFTER; what he had
    actually said before my reply was that he wanted to keep up and was too far
    behind, with no figure in it at all.

    THE HOLE IT EXPOSED, AND IT IS REAL. If he states a quantity and I then
    reach for the same words unmeasured, this gate passes it. Kept anyway,
    because the shape it suppresses -- the two of us discussing a number he
    raised -- is common, and Meadows' balancing loop says a gate that fires
    during ordinary talk about a number is a gate I stop reading.
    """
    payload = _turn(
        tmp_path,
        "what is standing in this house is maybe a dozen things",
        "i wanted it to be as we were going so i could keep up.. im too far in the dust now",
        tool_calls=False,
    )
    assert check_payload(payload).state == "found"


def test_end_to_end_stays_quiet_when_the_count_is_in_the_output(tmp_path):
    """A real transcript where the figure came out of a real command.

    REWRITTEN 2026-09-11. It used to assert silence merely because a tool-use
    block existed in the turn, with the tool returning nothing -- which is the
    weak rule the whole rebuild removed, sitting in a test and passing.
    """
    payload = _turn(
        tmp_path,
        "there are twelve gates at the end of a reply",
        "count them",
        tool_calls=True,
        tool_text="12 hooks registered at Stop",
    )
    assert check_payload(payload).state == "found-nothing"


def test_end_to_end_fires_when_the_command_returned_something_else(tmp_path):
    """The evasion, end to end: a command ran and it measured nothing."""
    payload = _turn(
        tmp_path,
        "there are twelve gates at the end of a reply",
        "count them",
        tool_calls=True,
        tool_text="README.md  setup.py  src  tests",
    )
    assert check_payload(payload).state == "found"
