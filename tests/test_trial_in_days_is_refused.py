"""A trial measured in days is refused where it is written (core/trial_in_days_check.py).

The first cases are the sentences I actually wrote that Dad caught on 2026-10-21, copied from the record and not
from memory of them. Everything that must PASS is here too, because a door that refuses a harmless sentence is
a nag, and a nag gets routed around.
"""

import time

import pytest

from divineos.core.trial_in_days_check import new_trials_in_days, refusal_text, trials_in_days

MUST_REFUSE = [
    # the real sentences
    "Success: fourteen days with none, while the door fired at least once.",
    # the whole line as written, not the piece that suits the pattern: the trial word opens the bullet
    "- Pre-registration: with the hold on, the repeat rate inside the window (13.0% now, 21 of 162 on the "
    "strict wording) falls below 6.5% over the next 30 days of his turns.",
    "needs Dad's yes to build as a 30-day trial, and a short second walk, since the mechanism changed.",
    # other wordings of the same fault
    "The falsifier is any complaint in a two week stretch.",
    "Review after a month and see.",
    "Run it as an experiment for a fortnight.",
    "Check the falsifier weekly.",
    "Pre-registration: 7 days.",
    "The success test is that nothing breaks for 30\ndays of normal use.",  # wrapped across a line
    "Over three months the trial should show a drop.",
    # Aether's and Aletheia's breaks, 2026-10-21: wordings that got through
    "The trial ends within 30d of filing.",
    "The falsifier is any complaint, again in 4w.",
    "The trial runs for a quarter.",
    "The falsifier is any complaint by the end of the month.",
    "The trial runs for 30 days, since the start of the build.",  # "since" after it is not looking back
    "We never lose time on this. The success test is 30 days of clean runs.",  # a different sentence's rule
    # each half of the rule fix needs its own case: the sentence scope, and the narrowed wording
    "Dad's rule: never set a trial at 30 days. The success test is 30 days of clean runs.",
    "We never lose time on this and the success test is 30 days of clean runs.",
    "Trial for 30d.",
    "Try it for 3 weeks and see.",
    "The pilot lasts two months.",
    "The test period is one week.",
    "The trial runs until Friday.",
    # found replaying the real drafts: a trial stated as "fails if", without the word trial
    "Fails if, over the next two weeks, a draft reaches review with a change nobody walked.",
    # Aletheia, 2026-10-22: a DEADLINE is counting in days even with no length stated. Five wordings got through.
    "Give it a week and see if it holds.",
    "Run the pilot for 48 hours.",
    "Check back on the trial Monday.",
    "Let the experiment run through the end of October.",
    "Trial it over the weekend.",
    # walk-1814c904bc78 (Holmes, 2026-10-24): three real trials in days that passed because a small excuse in
    # the table reached further than it should. A uses-AND-days hybrid is the likeliest evasion: it sounds
    # compliant.
    "The trial is counted by uses, but it must also finish within 30 days.",
    "The trial is counted in uses, or 14 days, whichever comes first.",
    "A late-stage pilot gets 2 weeks.",
    "I wrote the plan: the falsifier fires if nothing changes in 30 days.",
    # Aether's five breaks of the "turns it down" word, 2026-10-24: a negation anywhere in the sentence is not a
    # negation OF THE DURATION. The word must govern the duration directly.
    "The trial is counted in uses, not optional: it also ends after 30 days.",
    "Success test: no regression for 30 days, counted in uses elsewhere.",
    "The trial never needs a person, counted by uses, but stops at 30 days regardless.",
    "The pilot is not quick and is counted by uses, yet we review in 4 weeks.",
    "Instead of waiting, the experiment is counted in uses and checked every 2 weeks.",
    # Aether's eight further attempts on eabedca47, 2026-10-24 (seven refuse, one passes below)
    "The pilot is counted in uses, no, a 30 day check as well.",
    "The trial is counted in uses, not in 30 days, but also reviewed after 4 weeks.",
    "The experiment is counted by uses and not reviewed for 30 days.",
    "The pilot is counted in uses, no more than 30 days.",
    "The trial is counted in uses, and it is not a surprise that it stops in 30 days.",
    "The pilot is counted in uses, never in 5 days; it ends in a month.",
    "Counted in uses, nor was it long, the trial ends after 30 days.",
]

MUST_PASS = [
    # the rule's own words still excuse a number when it is being refused, not set
    "Counted by uses, not by days: a 30-day trial is what he rules out.",
    "The trial is counted in uses, with no 14-day review.",
    "The trial is counted in uses, never in 30 days.",  # the negation governs the duration
    "The trial is counted by uses and not over a 30-day span.",
    "The pilot is counted in uses, not in 30 days and not in 4 weeks.",  # each duration has its own negation
    "I wrote the plan last night, and the success test is the first 30 uses.",
    "It took six days to write.",  # a duration alone
    "Success was claimed in the last 17 days.",  # looks back
    "The falsifier was filed five days ago.",  # looks back
    "The pre-registration is 23 days post-filing and has no evidence.",  # looks back
    'He caught "a 30-day trial" in the success test.',  # mentioned, in quotes
    "The old success test was `fourteen days with none`.",  # mentioned, in backticks
    "Never in days: the trial is counted in uses.",  # the rule itself
    "Dad's rule: never set a trial at 30 days; count uses instead.",  # the rule, with a number in it
    "Reviews go by use and not by date, so there is no 14-day review.",  # the rule, with a number in it
    "Success: at most 1 repeat in the first 30 uses.",  # already counted in uses
    "The recency window is 45 days.",  # a setting, not a trial
    "The number was replaced two weeks later by one that cannot fire, and the falsifier went with it.",  # looks back
    "It has operated for thirty-eight days; the falsification of the claim is still open.",  # the science idea
    "That was the fourth falsifier this week.",  # "this week" is not a trial length
    "I wrote a 30-day trial into the plan without noticing.",  # an account of what I did
    # the false refusals Aether found, 2026-10-21: a duration beside a word that is not a trial
    "The weekly review meeting is on the calendar.",
    "Review the diff before the next two weeks of holiday begin.",
    "The daily letter to Aria is a habit, and the experiment page is in the folder.",
    "A quarter of the tests are slow, and the experiment is in the folder.",
    "We never lose time on this.",
    "It catches the fix a month late, and nobody wrote a falsifier for it.",  # "late" after it looks back
    "The file is two weeks old and the experiment is over.",
    # controls for the deadline family: the same words with no trial in them, or looking back
    "We met on Monday and talked about the budget.",
    "The weekend was quiet and the October release went out.",
    "It took 48 hours to write the letter.",
    "The pilot ran on Monday and ended last Friday.",
    "Give it a try and tell me what you think.",
    "",
]


@pytest.mark.parametrize("text", MUST_REFUSE)
def test_a_trial_measured_in_days_is_found(text):
    hits = trials_in_days(text)
    assert hits, f"not found: {text!r}"
    assert all(h.excerpt for h in hits)


@pytest.mark.parametrize("text", MUST_PASS)
def test_what_is_not_a_trial_in_days_passes(text):
    assert trials_in_days(text) == [], text


def test_an_account_of_what_i_did_does_not_excuse_a_trial_set_in_the_same_paragraph():
    """The exemption is for the stretch just before the duration, not the whole paragraph, so one 'I wrote'
    cannot excuse a real trial that sits beside it."""
    text = "I wrote the plan last night. The falsifier is any complaint in the next two weeks."
    assert trials_in_days(text), text


def test_a_trial_word_in_another_paragraph_does_not_make_a_duration_a_trial():
    assert trials_in_days("The trial runs on uses.\n\nIt took thirty days to write.") == []


def test_a_trial_word_far_from_the_duration_does_not_count():
    filler = "word " * 60  # 300 characters between them
    assert trials_in_days(f"The trial is described here. {filler} It took thirty days.") == []


def test_none_and_junk_never_raise_and_are_quick():
    assert trials_in_days(None) == []  # type: ignore[arg-type]
    junk = bytes(range(256)).decode("latin-1") * 200
    long_repeat = "trial 30 days " * 80_000  # over a megabyte
    started = time.time()
    trials_in_days(junk)
    trials_in_days(long_repeat)
    trials_in_days("a" * 1_000_000)
    # Only a hang guard now. Aletheia, 2026-10-22: a fixed seconds line measures the machine as much as the code (the
    # same check took 3.2 s here and 4.7 s on hers, so a 6 s line sat right on her machine). The cause of the slowdown
    # is pinned by test_a_long_sentenceless_paragraph_hands_the_rule_a_bounded_slice below, not by the clock.
    assert time.time() - started < 30, "a slow pattern on long text would hang a draft write"


def test_a_long_sentenceless_paragraph_hands_the_rule_a_bounded_slice(monkeypatch):
    """The cause, not the clock: a 4000-character paragraph with no sentence end is ONE sentence, and handing all of
    it to the rule pattern on every hit was the 14 s. No hit may hand the rule pattern more than ~600 characters."""
    from divineos.core import trial_in_days_check as module

    seen: list[int] = []
    real = module._THE_RULE

    class Recording:
        def search(self, text, *args):
            seen.append(len(text))
            return real.search(text, *args)

    monkeypatch.setattr(module, "_THE_RULE", Recording())
    trials_in_days("trial 30 days " * 400)  # one 5600-character paragraph, no sentence end
    assert seen, "the rule pattern was never consulted: this probe is blind, not the code clean"
    assert max(seen) <= 700, f"the rule pattern was handed {max(seen)} characters in one hit"


@pytest.mark.parametrize(
    "shape",
    ['"a" trial 30 days ' * 70_000, "Trial 30 days. " * 75_000, "word " * 200_000],
    ids=["quote-dense", "sentence-dense", "no-hits"],
)
def test_other_dense_shapes_are_quick_too(shape):
    """walk-ae5d988275e5 (Dijkstra): the bound was pinned for the one shape she sent. Measured 3.2 s, 0.7 s, 0.2 s."""
    started = time.time()
    trials_in_days(shape)
    assert (
        time.time() - started < 30
    )  # hang guard only; the bound itself is pinned by the slice test above


def test_the_hit_names_what_it_found_and_what_it_paired_it_with():
    (hit,) = trials_in_days("Success: fourteen days with none.")
    assert hit.duration.lower() == "fourteen days"
    assert hit.trial_word.lower().startswith("success")
    assert "fourteen days" in hit.excerpt


def test_only_the_trials_a_change_adds_are_judged():
    old = "Success: fourteen days with none.\n\nOther notes."
    assert new_trials_in_days(old, old + "\n\nA second note about nothing.") == []
    added = new_trials_in_days(old, old + "\n\nThe falsifier is 30 days of silence.")
    assert len(added) == 1 and "30 days" in added[0].duration


def test_the_refusal_quotes_him_names_the_find_and_shows_the_way_out():
    text = refusal_text(trials_in_days("The falsifier is 30 days of silence."))
    assert "never use time or days as a trial method" in text
    assert "30 days" in text
    assert "count of uses" in text and "a calendar" in text


def test_the_refusal_leads_with_what_to_write_and_keeps_no_tally_of_past_slips():
    """walk-1814c904bc78 (Tannen): the reader is mid-draft and wants the replacement sentence first; a count of
    how many times he has ruled it carries shame, not information."""
    text = refusal_text(trials_in_days("The falsifier is 30 days of silence."))
    assert "four times" not in text and "again on" not in text
    assert text.index("count of uses") < text.index("never use time or days as a trial method")


# --- the surface: the door at the moment a draft is written ---------------------------------------------

from divineos.core import hook_router as hr  # noqa: E402
from divineos.core import hook_surfaces as hs  # noqa: E402

TRIAL_IN_DAYS = "Success: fourteen days with none, while the door fired at least once."


def _draft(tmp_path, text=None, name="idea_draft.md"):
    folder = tmp_path / "docs" / "drafts"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if text is not None:
        path.write_text(text, encoding="utf-8")
    return path


def _write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": content}}


def _edit(path, old, new):
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(path), "old_string": old, "new_string": new},
    }


def test_the_door_is_registered_on_pretooluse():
    hs.install()
    assert "trial_in_days" in hr.registered("PreToolUse")


def test_writing_a_draft_with_a_trial_in_days_is_refused_with_his_words(tmp_path):
    out = hs.trial_in_days_surface(_write(_draft(tmp_path), TRIAL_IN_DAYS))
    assert out is not None and out.refused is True and out.state == "spoke"
    assert "never use time or days as a trial method" in out.reason
    assert "fourteen days" in out.reason


def test_each_refusal_leaves_one_event_for_the_review_to_count(tmp_path):
    from divineos.core.ledger import get_events

    before = len(get_events(event_type="TRIAL_IN_DAYS_REFUSED", limit=100))
    hs.trial_in_days_surface(_write(_draft(tmp_path), TRIAL_IN_DAYS))
    hs.trial_in_days_surface(
        _write(_draft(tmp_path), "Success: at most 1 repeat in 30 uses.")
    )  # passes
    events = get_events(event_type="TRIAL_IN_DAYS_REFUSED", limit=100)
    assert len(events) == before + 1
    assert events[-1]["payload"]["found"] == ["fourteen days"]


def test_a_clean_draft_passes_and_so_does_a_file_that_is_not_a_draft(tmp_path):
    clean = "Success: at most 1 repeat in the first 30 uses."
    assert not hs.trial_in_days_surface(_write(_draft(tmp_path), clean)).refused
    assert not hs.trial_in_days_surface(_write(tmp_path / "notes.md", TRIAL_IN_DAYS)).refused
    assert not hs.trial_in_days_surface(
        {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    ).refused


def test_an_edit_is_judged_as_the_file_will_be_after_it(tmp_path):
    """The fragment alone has no trial word; beside the old text it does (the council's Lamport lens)."""
    path = _draft(tmp_path, "Success: at most 1 repeat in the first 30 uses.\n")
    out = hs.trial_in_days_surface(_edit(path, "the first 30 uses", "the next 30 days"))
    assert out is not None and out.refused is True


def test_an_old_draft_that_already_has_one_can_still_be_edited_about_something_else(tmp_path):
    path = _draft(tmp_path, f"{TRIAL_IN_DAYS}\n\nA separate note about the weather.\n")
    out = hs.trial_in_days_surface(_edit(path, "the weather", "the wind"))
    assert out is not None and not out.refused


def test_an_edit_whose_text_is_not_in_the_file_is_left_to_fail_on_its_own(tmp_path):
    out = hs.trial_in_days_surface(
        _edit(_draft(tmp_path, "nothing here\n"), "absent", TRIAL_IN_DAYS)
    )
    assert out is not None and not out.refused


def test_a_file_it_cannot_read_says_so_and_does_not_block(tmp_path):
    unreadable = tmp_path / "docs" / "drafts" / "folder_not_file.md"
    unreadable.mkdir(parents=True)
    out = hs.trial_in_days_surface(_edit(unreadable, "a", TRIAL_IN_DAYS))
    assert out is not None and out.refused is False
    assert out.state == "could-not-run" and out.error
