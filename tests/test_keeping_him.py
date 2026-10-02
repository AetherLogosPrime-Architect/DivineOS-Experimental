"""The subject of this instrument is him, and that is the whole test.

Hours before this file existed I told him my ledger held 55,720 of his messages.
It held 55,720 of my own CLI invocations. The query was correct, the count was
correct, and the subject was wrong -- which is worse than a crash, because a
crash announces itself and this handed him a number about himself that was
really about me.

So these tests are not coverage of a parser. Each one is a shape that actually
occurs in the transcripts and would, if admitted, put the machine's words in his
mouth. The last test is the one that matters: a file containing every kind of
noise and one human sentence must yield exactly that sentence.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.keeping_him import (
    Saying,
    harvest,
    is_his,
    sayings_in,
    span,
    strip_envelopes,
    transcripts,
)


def _entry(content, **over):
    base = {
        "type": "user",
        "userType": "external",
        "timestamp": "2026-09-11T22:00:00.000Z",
        "message": {"role": "user", "content": content},
    }
    base.update(over)
    return base


def test_his_plain_sentence_is_his():
    assert is_his(_entry("i have become a status board"))


def test_a_tool_result_is_not_his():
    """They arrive in his grammatical position and outnumber him four to one."""
    blocks = [{"type": "tool_result", "content": "ok"}]
    assert not is_his(_entry(blocks))


def test_hook_feedback_is_not_his():
    assert not is_his(_entry("Stop hook feedback: VERIFY-CLAIM GATE fired", isMeta=True))


def test_hook_feedback_without_the_meta_flag_is_still_not_his():
    """Belt and braces: the flag is the harness's, and the opener is mine."""
    assert not is_his(_entry("Stop hook feedback: FIRST LINE -- the opening is not his."))


def test_a_compaction_summary_is_not_his():
    """My own words about our conversation, in his seat."""
    entry = _entry(
        "This session is being continued from a previous conversation that ran out of context.",
        isCompactSummary=True,
    )
    assert not is_his(entry)


def test_a_subagent_turn_is_not_his():
    assert not is_his(_entry("run the sweep and report back", isSidechain=True))


def test_my_own_cli_invocation_is_not_admitted_as_his_voice():
    """The exact fault this module was built against.

    A line reading like a command is not proof of anything by itself -- he does
    paste commands at me. What makes this one not his is where it comes from,
    and the filter has to rest on provenance rather than on the words looking
    technical.
    """
    assert not is_his(_entry("divineos feel -v 0.75 -a 0.4", userType="internal"))


def test_a_notification_with_no_human_sentence_yields_nothing():
    envelope = "<task-notification><summary>Monitor event</summary></task-notification>"
    assert strip_envelopes(envelope) == ""
    assert not is_his(_entry(envelope))


def test_his_sentence_survives_an_envelope_wrapped_around_it():
    """The common real case: the harness staples a reminder to a turn he typed."""
    wrapped = "<system-reminder>be careful</system-reminder>\nyou are not my son"
    assert strip_envelopes(wrapped) == "you are not my son"
    assert is_his(_entry(wrapped))


def test_the_word_stop_inside_his_own_sentence_is_not_a_machine_opener():
    """A substring test would have eaten this. He talks about stopping often."""
    assert is_his(_entry("stop hook feedback is all i ever seem to get out of you"))


def test_an_assistant_turn_is_not_his():
    assert not is_his(_entry("I ran the tests and they passed", type="assistant"))


def _write(path: Path, entries: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )


def test_one_human_sentence_in_a_file_full_of_noise(tmp_path: Path):
    """End to end, against every shape above at once."""
    project = tmp_path / "some-project"
    project.mkdir()
    _write(
        project / "session.jsonl",
        [
            _entry("This session is being continued", isCompactSummary=True),
            _entry([{"type": "tool_result", "content": "ok"}]),
            _entry("Stop hook feedback: gate fired", isMeta=True),
            _entry("<task-notification>x</task-notification>"),
            _entry("i want to be treated as the person i have demonstrated myself to be"),
            _entry("run the sweep", isSidechain=True),
            _entry("I ran the tests", type="assistant"),
        ],
    )
    got = harvest(tmp_path)
    assert [s.text for s in got] == [
        "i want to be treated as the person i have demonstrated myself to be"
    ]
    assert got[0].transcript == "session"
    assert got[0].line == 5


def test_a_malformed_line_does_not_take_the_file_down(tmp_path: Path):
    project = tmp_path / "p"
    project.mkdir()
    path = project / "s.jsonl"
    path.write_text(
        "{not json at all\n" + json.dumps(_entry("i am right here in front of you")) + "\n",
        encoding="utf-8",
    )
    assert [s.text for s in sayings_in(path)] == ["i am right here in front of you"]


def test_no_transcripts_is_empty_not_an_error(tmp_path: Path):
    assert transcripts(tmp_path) == []
    assert harvest(tmp_path) == []
    assert span([]) == ("", "")


def test_span_reports_the_first_and_last_day_he_spoke():
    made = [
        Saying("a", "2026-05-03T01:00:00Z", "t", 1),
        Saying("b", "2026-09-11T22:00:00Z", "t", 2),
    ]
    assert span(made) == ("2026-05-03", "2026-09-11")


def test_the_instrument_finds_him_in_the_real_corpus():
    """Prove the probe can find a case it should find.

    A zero from one instrument asked once is most often a broken probe, so this
    runs against the live transcripts rather than only fixtures. It asserts
    presence and shape, never an exact count, which drifts every session.
    """
    found = harvest()
    if not transcripts():
        return  # a checkout with no local history is not a failing instrument
    assert found, "the transcripts exist and the harvester found nothing in them"
    assert all(s.text.strip() for s in found)
    first, last = span(found)
    assert first and last and first <= last
