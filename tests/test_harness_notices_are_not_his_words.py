"""The answer check must not read the harness's notices as his words.

Measured on real transcripts: the check said "he said: <system-reminder> Attribution
for git commits ..." and held a reply for not echoing a notice. Inputs (a)-(e) below
are those shapes, real and HTML-escaped.
"""

from __future__ import annotations

import json

from divineos.core.his_message import without_notices
from divineos.core.hook_surfaces import _last_user_text, addressed_to_him_surface

ATTRIBUTION = (
    "<system-reminder>\nAttribution for git commits and pull requests you create "
    "from here on:\n- End git commit messages with the session line.\n</system-reminder>"
)
REREAD = (
    "<system-reminder>\nInstruction files were re-read after the working directory "
    "changed; follow the new project instructions.\n</system-reminder>"
)
TASK = (
    "[SYSTEM NOTIFICATION - NOT USER INPUT] A background task finished and the "
    "result is below.\n\n<task-notification>\n<task-id>b123</task-id>\n"
    "<status>completed</status>\n</task-notification>"
)
HIS = "please fix the kitchen light switch before the guests arrive tomorrow evening"
YOU_REPLY = (
    "You asked about something else entirely. I think you will like the garden "
    "plan, and your tomatoes are doing well. You can see the pictures soon."
)
ECHO_REPLY = f"You said: {HIS}. {HIS}. {HIS}."


def _escaped(block: str) -> str:
    return block.replace("<", "&lt;")


def _transcript(tmp_path, user_text, reply):
    path = tmp_path / "t.jsonl"
    recs = [
        {"message": {"role": "user", "content": [{"type": "text", "text": user_text}]}},
        {"message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}},
    ]
    path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


# (a) only a notice: no words of his, so the check stands aside.
def test_a_message_that_is_only_a_notice_stands_aside(tmp_path):
    for block in (ATTRIBUTION, REREAD, TASK):
        payload = _transcript(tmp_path, block, YOU_REPLY)
        assert _last_user_text(payload) == ""
        out = addressed_to_him_surface(payload)
        assert out is not None and not out.refused
        assert out.state == "nothing-to-say"


# (b) escaped forms strip the same way.
def test_escaped_notices_strip_the_same(tmp_path):
    for block in (_escaped(ATTRIBUTION), _escaped(REREAD), _escaped(TASK)):
        payload = _transcript(tmp_path, block, YOU_REPLY)
        assert _last_user_text(payload) == ""
        out = addressed_to_him_surface(payload)
        assert not out.refused and out.state == "nothing-to-say"


# (c) his message then a notice: his words still counted, old behaviour holds.
def test_his_words_before_a_notice_still_count(tmp_path):
    text = HIS + "\n\n" + ATTRIBUTION
    assert without_notices(text).strip() == HIS
    assert addressed_to_him_surface(_transcript(tmp_path, text, YOU_REPLY)).refused


def test_a_notice_does_not_change_the_verdict_on_an_echo(tmp_path):
    with_notice = addressed_to_him_surface(
        _transcript(tmp_path, HIS + "\n\n" + ATTRIBUTION, ECHO_REPLY)
    )
    bare = addressed_to_him_surface(_transcript(tmp_path, HIS, ECHO_REPLY))
    assert (with_notice.refused, with_notice.state) == (bare.refused, bare.state)


# (d) a block in the middle is removed and the rest counted.
def test_a_block_in_the_middle_is_removed():
    for block in (ATTRIBUTION, _escaped(REREAD), TASK):
        got = without_notices("kitchen light first part\n" + block + "\nsecond part switch")
        assert "kitchen light first part" in got and "second part switch" in got
        assert "Attribution" not in got and "re-read" not in got and "task-id" not in got
        assert "SYSTEM NOTIFICATION" not in got


# (e) malformed: no crash, his words after it survive.
def test_an_unclosed_tag_does_not_swallow_his_words():
    assert HIS in without_notices("<system-reminder> never closed\n\n" + HIS)
    assert HIS in without_notices("&lt;task-notification> half " + HIS)
    assert without_notices("") == ""
    assert HIS in without_notices("<system-reminder></task-notification> " + HIS)


# (f) his own words that merely look like a notice are kept (checker's three reproductions).
def test_a_pair_he_types_in_his_own_sentence_keeps_what_is_between():
    typed = "I typed <system-reminder>keep these words</system-reminder> myself, fine?"
    assert without_notices(typed) == typed
    stretched = "tag <system-reminder>mine</system-reminder> end\n" + ATTRIBUTION
    got = without_notices(stretched)
    assert "mine" in got and "Attribution" not in got


def test_a_banner_followed_directly_by_his_words_keeps_them():
    got = without_notices("[SYSTEM NOTIFICATION - NOT USER INPUT] done.\n" + HIS)
    assert got == HIS


def test_a_mention_of_the_banner_inside_a_sentence_keeps_the_sentence():
    said = "why does it print [SYSTEM NOTIFICATION - NOT USER INPUT] before my words?"
    assert without_notices(said) == said


def test_a_windows_line_ending_envelope_is_still_cut():
    crlf = f"{ATTRIBUTION}\n{HIS}".replace("\n", "\r\n")
    assert without_notices(crlf) == HIS
    assert without_notices(f"{HIS}\n{ATTRIBUTION}".replace("\n", "\r\n")) == HIS
    assert without_notices((TASK + "\n" + HIS).replace("\n", "\r\n")) == HIS
