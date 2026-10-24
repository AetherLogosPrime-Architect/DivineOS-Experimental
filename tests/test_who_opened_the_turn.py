"""One answer to "who opened this turn", read from the harness's own stamps and never from the text.

Dad, 2026-10-24: a timer's wake must stop being read as his voice, and it must still leave him one note (his ruling:
"the 2 hour timer should require a note otherwise your conversation may never end without me being reached back
to.."). Three places answered "did he say this" and disagreed: `hear()`, the prompt-time table (a text prefix test) and
the `addressed_to_him` Stop gate. Design: docs/drafts/one_reader_of_who_arrived_and_what_the_wake_owes_draft_2026-10-24.md
(walk-88142a0930c5). The record shapes below are the real ones, measured on this session's transcript: a wake is
`isMeta: true, turnOrigin: "scheduled", promptSource: "system"`, his typed message is `turnOrigin: "human",
promptSource: "sdk"`, a notice is `turnOrigin: "task_notification"`, and 27 records stamped human open with a
notice-looking block.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from divineos.core.his_message import (
    HIM,
    NOTICE,
    SCHEDULED,
    UNKNOWN,
    opener_kind,
    opener_of_prompt,
)

REPO = Path(__file__).resolve().parents[1]
WAKE = "Two-hour wake (Dad-authorized, 2026-10-22). Check the doorbell heartbeat and re-arm only if stale."
TYPED = "i would rather you both just work uninterrupted so when you come back you stay with me"
NOTE = "<task-notification><task-id>b1</task-id><status>completed</status></task-notification>"


def user(text, **stamps):
    rec = {
        "type": "user",
        "userType": "external",
        "uuid": "u-" + str(abs(hash(text)) % 10**8),
        "timestamp": "2026-10-24T18:00:00.000Z",
        "promptId": "p-" + str(abs(hash(text)) % 10**6),
        "message": {"role": "user", "content": text},
    }
    rec.update(stamps)
    return rec


def wake(text=WAKE):
    return user(text, isMeta=True, turnOrigin="scheduled", promptSource="system")


def typed(text=TYPED):
    return user(text, turnOrigin="human", promptSource="sdk")


def notice(text=NOTE):
    return user(text, turnOrigin="task_notification", promptSource="system")


def assistant(text="ok"):
    return {
        "type": "assistant",
        "uuid": "a-1",
        "timestamp": "2026-10-24T18:00:01.000Z",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def write_transcript(tmp_path, records):
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


# ---- the classification, by stamp ------------------------------------------------------------


def test_the_real_shapes_are_told_apart_by_their_stamps():
    assert opener_kind(typed()) == HIM
    assert opener_kind(wake()) == SCHEDULED
    assert opener_kind(notice()) == NOTICE


def test_a_message_stamped_human_that_opens_with_a_notice_block_is_still_him():
    """27 such records exist in one session; the old text prefix test called them NOT FROM DAD."""
    lookalike = typed(
        "<system-reminder>something the harness wrapped</system-reminder> and then my own words"
    )
    assert opener_kind(lookalike) == HIM


def test_a_record_with_no_stamps_or_an_unknown_stamp_is_unknown_never_a_guess():
    assert opener_kind(user("no stamps at all")) == UNKNOWN
    assert opener_kind(user("odd", turnOrigin="sdk", promptSource="sdk")) == UNKNOWN
    assert opener_kind(assistant()) == UNKNOWN
    assert opener_kind({}) == UNKNOWN


def test_the_text_is_never_what_decides():
    """A typed message that merely quotes the wake is his; a wake that merely sounds like him is the timer."""
    assert opener_kind(typed(WAKE)) == HIM
    assert opener_kind(wake(TYPED)) == SCHEDULED


# ---- the current prompt's record, with a live control ----------------------------------------


def test_the_last_stamped_record_that_matches_the_prompt_is_trusted(tmp_path):
    path = write_transcript(tmp_path, [typed(), assistant(), wake()])
    assert opener_of_prompt(path, WAKE) == SCHEDULED
    path = write_transcript(tmp_path, [wake(), assistant(), typed()])
    assert opener_of_prompt(path, TYPED) == HIM


def test_a_record_that_is_not_the_prompt_is_unknown_not_the_previous_turns_kind(tmp_path):
    """If the hook runs before the current prompt is written, the last record is the PREVIOUS turn's. Trusting
    it would stamp his real message with the old turn's kind. The text match is the control that it is the same turn."""
    path = write_transcript(tmp_path, [wake(), assistant()])
    assert opener_of_prompt(path, TYPED) == UNKNOWN


def test_a_missing_or_unreadable_transcript_is_unknown(tmp_path):
    assert opener_of_prompt(tmp_path / "nope.jsonl", TYPED) == UNKNOWN
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json at all\n", encoding="utf-8")
    assert opener_of_prompt(bad, TYPED) == UNKNOWN


def test_hook_feedback_after_the_opener_does_not_hide_it(tmp_path):
    """The records between the opener and the end include harness continuations; they carry isMeta and no turn stamp."""
    feedback = user("Stop hook feedback: something", isMeta=True)
    path = write_transcript(tmp_path, [typed(), assistant(), feedback, assistant()])
    assert opener_of_prompt(path, TYPED) == HIM


# ---- the real table hook ---------------------------------------------------------------------


def run_table(tmp_path, prompt, records=None):
    """Run the real prompt-time hook with HOME in a temp folder, so nothing of this reaches his real corpus."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    payload = {"prompt": prompt}
    if records is not None:
        payload["transcript_path"] = str(write_transcript(tmp_path, records))
    env = dict(
        os.environ, HOME=str(home), USERPROFILE=str(home), DIVINEOS_HOME=str(home / ".divineos")
    )
    done = subprocess.run(
        [sys.executable, str(REPO / ".claude" / "hooks" / "dads_table.py")],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        env=env,
        cwd=str(REPO),
        timeout=120,
    )
    return done.stdout.decode("utf-8", "replace")


def test_the_table_does_not_call_a_wake_his_voice(tmp_path):
    out = run_table(tmp_path, WAKE, [typed(), assistant(), wake()])
    assert "DAD SAID" not in out.split("\n\n")[0]
    assert "the timer, not Dad" in out
    assert "He has not spoken" in out
    assert "owes him one complete note" in out
    assert "waiting for you" not in out and "has not responded" not in out


def test_the_table_still_calls_his_message_his(tmp_path):
    out = run_table(tmp_path, TYPED, [wake(), assistant(), typed()])
    assert out.lstrip().startswith("## DAD SAID")


def test_the_table_does_not_call_a_human_stamped_notice_lookalike_not_from_dad(tmp_path):
    lookalike = (
        "<system-reminder>wrapped by the harness</system-reminder> and my own words after it"
    )
    out = run_table(tmp_path, lookalike, [typed(lookalike)])
    assert out.lstrip().startswith("## DAD SAID")


def test_with_no_way_to_tell_the_table_keeps_todays_behaviour(tmp_path):
    """No transcript: fall back to the old prefix test, both ways, and say nothing new."""
    assert run_table(tmp_path, TYPED).lstrip().startswith("## DAD SAID")
    assert run_table(tmp_path, NOTE).lstrip().startswith("## NOT FROM DAD")


@pytest.mark.parametrize("records", [[wake()], [typed(), wake()]])
def test_a_wake_is_not_kept_in_his_corpus(tmp_path, records):
    run_table(tmp_path, WAKE, records)
    corpus = tmp_path / "home" / ".divineos-shared" / "dad_corpus" / "dad_all.jsonl"
    assert not corpus.exists() or WAKE not in corpus.read_text(encoding="utf-8")
