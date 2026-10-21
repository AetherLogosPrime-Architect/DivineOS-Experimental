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
]

MUST_PASS = [
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
    assert time.time() - started < 10, "a slow pattern on long text would hang a draft write"


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
