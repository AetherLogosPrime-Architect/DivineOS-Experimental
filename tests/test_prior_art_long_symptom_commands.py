"""A long symptom sentence must not match a command just because the sentence contains its name.

2026-11-04: a symptom containing "a tool call that changes something" surfaced `divineos changes`,
because the matcher squashes the whole sentence into one string and asks whether any command name
appears inside it. Dad: if it does not fit, make it stop showing up.
"""

from divineos.core import prior_art

LONG = (
    "memory link reaches me at the moment I act: search the store with my own words before a "
    "reply ends and before a tool call that changes something; floor, cap, no repeats"
)


def test_a_short_name_lookup_still_finds_its_command():
    assert "changes" in prior_art.find_commands("changes")


def test_a_long_sentence_that_merely_uses_the_word_does_not_surface_the_command():
    assert "changes" not in prior_art.find_commands(LONG)


def test_a_long_sentence_does_not_match_across_the_joins_between_words():
    # "...the log in..." squashes to "thelogin", which contains the command name "login"-like
    # strings; none of that may count for a sentence.
    sentence = "the memory link finds nothing when the lo gin step runs before the context arrives"
    assert prior_art.find_commands(sentence) == []


def test_a_term_inside_a_command_name_still_matches_for_a_long_term_only_if_it_fits_there():
    # The other direction (term inside a command name) is untouched: a long sentence is never
    # inside a command name, so it adds nothing, and a short term still does.
    assert "changes" in prior_art.find_commands("chang")
