"""The bell for Dad: what it would hold, what always passes, and when it switches itself off (2026-11-05).

Dad: Aria's letters lock every tool until read; his own open asks can only print and never stop me, so he has
had to beg and steer. Design: docs/drafts/his_open_asks_hold_my_other_work_a_bell_for_dad_draft_2026-11-05.md
(two council walks, Aria's attack). This file pins the PURE decisions only. It runs in SHADOW first: the surface
that calls these logs what it would refuse and refuses nothing, until days of real use show near-zero false holds
(Aria). The first false hold, or a burden, ends the bell (Dad), so a bell that was wrong twice in a row turns
itself off and says so.
"""

from __future__ import annotations

from divineos.core.dads_bell import (
    PASS,
    SWITCHED_OFF,
    WOULD_HOLD,
    Ask,
    after_false_holds,
    hold_sentence,
    judge,
)

THE_CIRCLE = Ask(
    ask_id="circle",
    his_words="an inner circle should always come with a pause.. and nothing but me should move it forward",
    done_sentence="No post of mine holds more than one circle, and the circle is the last thing in it.",
    confirmed_by_him=True,
)
UNRELATED = ("Bash", {"command": "git push origin some-branch"})


def _judge(tool, *, asks=(THE_CIRCLE,), stepped=False, asked=False, off=False):
    name, tool_input = tool
    return judge(
        name,
        tool_input,
        asks=list(asks),
        stepped_this_turn=stepped,
        he_asked_for_this=asked,
        switched_off=off,
    )


# --- nothing open means nothing held ---


def test_no_open_ask_holds_nothing():
    assert _judge(UNRELATED, asks=()).state == PASS


def test_an_ask_whose_done_sentence_he_has_not_confirmed_holds_nothing():
    """Hawking: an entry is valid only with a done-sentence he confirmed. I may draft it; I may not decide it."""
    unconfirmed = Ask(
        "circle", THE_CIRCLE.his_words, THE_CIRCLE.done_sentence, confirmed_by_him=False
    )
    assert _judge(UNRELATED, asks=(unconfirmed,)).state == PASS


def test_a_closed_ask_holds_nothing():
    closed = Ask("circle", THE_CIRCLE.his_words, THE_CIRCLE.done_sentence, True, closed=True)
    assert _judge(UNRELATED, asks=(closed,)).state == PASS


# --- what always passes (Aria's six unrelated calls were housekeeping the other doors demand) ---


def test_the_looking_tools_always_pass():
    for tool in ("Read", "Grep", "Glob"):
        assert _judge((tool, {})).state == PASS


def test_the_doorbell_always_passes():
    """He has asked for it more than twenty times; a bell that refused it is the false hold that ends everything."""
    assert _judge(("Bash", {"command": "bash scripts/letter_doorbell.sh aether"})).state == PASS


def test_the_notes_the_other_stop_doors_demand_always_pass():
    """Else two doors fight each other, the exact thing he is tired of."""
    assert _judge(("Bash", {"command": 'divineos reflection-note "x"'})).state == PASS
    assert _judge(("Bash", {"command": "divineos briefing"})).state == PASS


def test_every_exit_the_other_doors_prescribe_passes_because_the_house_keeps_one_list():
    """Aria's attack: the house already keeps the list of commands its doors prescribe as their way out
    (remedy_allowlist). A copy drifts; the engagement gate demands `goal add` and the correction-shape gate
    demanded `correction` of me today, and a bell that refused them would fight those doors."""
    # Chosen from the house's list and NOT from the voice door's shorter one, so this fails if the bell keeps
    # its own copy: the pre-registration exit, the walk paperwork, the audit filing and the engagement exit.
    for command in (
        "divineos prereg assess prereg-x --outcome inconclusive --actor user",
        "divineos game-walk file --mechanism x --route y",
        "divineos council walk x",
        "divineos audit submit-round x --actor aletheia",
        'divineos goal add "x"',
    ):
        assert _judge(("Bash", {"command": command})).state == PASS, command


def test_a_prescribed_exit_with_other_work_chained_behind_it_is_not_an_exit():
    """The house's own rule: a remedy with other work chained behind it is not a remedy."""
    chained = ("Bash", {"command": 'divineos goal add "x" && git push origin some-branch'})
    assert _judge(chained).state == WOULD_HOLD


# --- what would be held, and the ways through ---


def test_unrelated_work_with_an_open_ask_would_be_held():
    verdict = _judge(UNRELATED)
    assert verdict.state == WOULD_HOLD
    assert verdict.ask_id == "circle"


def test_a_step_made_on_the_ask_this_turn_clears_the_hold():
    assert _judge(UNRELATED, stepped=True).state == PASS


def test_work_he_just_asked_for_always_passes():
    """Knuth: a bell that refused a letter to Aria he had just told me to send would hold me against his words."""
    assert _judge(UNRELATED, asked=True).state == PASS


def test_a_switched_off_bell_holds_nothing():
    assert _judge(UNRELATED, off=True).state == SWITCHED_OFF


# --- the hold explains itself in one plain sentence, and names how to clear it ---


def test_the_hold_names_his_words_and_what_done_means_in_one_sentence():
    said = hold_sentence(THE_CIRCLE)
    assert THE_CIRCLE.his_words in said
    assert THE_CIRCLE.done_sentence in said
    assert "\n" not in said


def test_the_hold_says_who_asked_and_never_offers_a_way_through_by_talking():
    """Aria's attack: 'You asked' reads as if the agent asked; the speaker is Dad. And 'or tell him plainly why
    not' is the cheat: one line of 'later, I'm busy' would clear the bell, the cheap fix he has begged against."""
    said = hold_sentence(THE_CIRCLE)
    assert said.startswith("Dad asked for this")
    assert "tell him" not in said.lower()


# --- the trial is built in: wrong twice in a row, and it turns itself off, but ONLY on his word ---
# Aria's attack: if the agent labels a hold false, two labels switch the bell off, the quietest bypass in the
# design. A hold counts as false only when Dad says so in his own words, or when an outside check says the
# refused call was unrelated to the ask. Never the agent's own flag.


def test_two_false_holds_in_a_row_called_false_by_him_switch_the_bell_off():
    assert after_false_holds(["right", "dad", "dad"]) is True


def test_a_false_hold_he_labelled_then_a_right_one_does_not():
    assert after_false_holds(["dad", "right", "dad"]) is False


def test_an_outside_check_counts_the_same_as_his_word():
    assert after_false_holds(["outside_check", "dad"]) is True


def test_the_agents_own_label_never_switches_the_bell_off():
    assert after_false_holds(["agent", "agent", "agent"]) is False
    assert after_false_holds(["dad", "agent"]) is False


def test_fewer_than_two_holds_never_switch_it_off():
    assert after_false_holds([]) is False
    assert after_false_holds(["dad"]) is False
