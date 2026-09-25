"""One list of what the harness wraps around his seat. See core/harness_envelopes.py."""

from __future__ import annotations

import pytest

from divineos.core.harness_envelopes import _TAGS, nothing_of_his, strip_envelopes


@pytest.mark.parametrize("tag", _TAGS)
def test_every_envelope_alone_is_nothing_of_his(tag):
    assert nothing_of_his(f"<{tag}>machine text</{tag}>")


def test_both_older_lists_are_covered():
    """The union of keeping_him._ENVELOPES and correction_marker's regex."""
    from_keeping_him = {
        "task-notification",
        "system-reminder",
        "local-command-stdout",
        "command-name",
        "command-message",
        "command-args",
        "ci-monitor-event",
    }
    from_correction_marker = {
        "task-notification",
        "system-reminder",
        "persisted-output",
        "ci-monitor-event",
    }
    assert from_keeping_him | from_correction_marker == set(_TAGS)


def test_an_envelope_that_never_closes_runs_to_the_end():
    assert nothing_of_his("<ci-monitor-event>a notice cut short")


def test_his_words_survive_beside_an_envelope():
    assert strip_envelopes("<system-reminder>x</system-reminder> keep this, all of it") == (
        "keep this, all of it"
    )


def test_a_machine_opener_is_nothing_of_his_but_the_word_in_his_sentence_is():
    assert nothing_of_his("Stop hook feedback: the gate fired")
    assert not nothing_of_his("please stop hook feedback from firing on me")


def test_plain_words_are_his():
    assert not nothing_of_his("proceed")
