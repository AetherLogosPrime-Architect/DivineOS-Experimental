"""The correction marker reads the house's one list of harness wrappers.

It did from 2026-09-24, and the line was lost when #554 landed on main: its
private four-tag list came back and harness_envelopes was left with no caller.
The private list did not know the command blocks, so a block carrying
correction-shaped words could be written into his store as his voice.
test_harness_envelopes.py checks the list itself; this checks it is used.
"""

from __future__ import annotations

from divineos.core import correction_marker
from divineos.core.harness_envelopes import _TAGS


def test_a_command_block_is_not_his_voice():
    text = "<command-args>stop, that is wrong, do not do that</command-args>"
    assert "wrong" not in correction_marker.strip_relayed(text)


def test_his_sentence_after_a_wrapper_survives():
    text = "<system-reminder>machine words</system-reminder>no, that is not what i asked"
    out = correction_marker.strip_relayed(text)
    assert "not what i asked" in out
    assert "machine words" not in out


def test_every_shared_tag_is_stripped():
    for tag in _TAGS:
        text = f"<{tag}>you got it wrong again</{tag}>"
        assert "wrong" not in correction_marker.strip_relayed(text), tag
