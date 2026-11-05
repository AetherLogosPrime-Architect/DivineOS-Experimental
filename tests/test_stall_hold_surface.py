"""The stall hold, run as a router surface, says what the standalone script said.

Folded in 2026-11-04 (Dad: his end-of-reply holds arrive one after another). The surface and the old script
call the same core function; these tests pin the behaviours the move must keep.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from divineos.core import hook_surfaces, stall_hold

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


def _user(text: str) -> dict:
    return {
        "type": "user",
        "userType": "external",
        "message": {"role": "user", "content": [{"type": "text", "text": text}]},
    }


def _assistant(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _transcript(tmp_path, *records: dict) -> str:
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(path)


STALL = "I looked at it and now I'm writing Aether the letter."
DONE = "It is finished and the shared copy matches."


def test_a_stall_is_refused_with_the_same_reason_as_the_script(tmp_path):
    path = _transcript(tmp_path, _user("go on"), _assistant(STALL))
    out = hook_surfaces.stall_on_promise_surface({"transcript_path": path})
    assert out.refused and out.state == "spoke"
    sys.path.insert(0, str(HOOKS))
    import stall_on_promise_stop as script

    assert out.reason == script.verdict(stall_hold.read_tail(Path(path)), path)


def test_a_finished_reply_passes(tmp_path):
    path = _transcript(tmp_path, _user("go on"), _assistant(DONE))
    out = hook_surfaces.stall_on_promise_surface({"transcript_path": path})
    assert not out.refused and out.state == "nothing-to-say"


def test_one_hold_per_reply_a_continuation_stands_down(tmp_path):
    path = _transcript(tmp_path, _user("go on"), _assistant(STALL))
    out = hook_surfaces.stall_on_promise_surface(
        {"transcript_path": path, "stop_hook_active": True}
    )
    assert not out.refused and out.state == "nothing-to-say"


def test_an_unreadable_transcript_is_could_not_run_never_a_pass(tmp_path):
    out = hook_surfaces.stall_on_promise_surface(
        {"transcript_path": str(tmp_path / "missing.jsonl")}
    )
    assert out.state == "could-not-run" and not out.refused
    none = hook_surfaces.stall_on_promise_surface({})
    assert none.state == "could-not-run" and none.error


def test_when_he_spoke_into_the_turn_the_step_waits_and_nothing_is_held(tmp_path, monkeypatch):
    # The voice door refuses my tool calls once he has spoken into a turn, so holding the step I named for not
    # being done would trap me between two checks. The surface must obey the shared rule, both ways.
    from divineos.core import his_voice_ends_the_turn as hv

    path = _transcript(tmp_path, _user("go on"), _assistant(STALL))
    monkeypatch.setattr(hv, "spoke_mid_turn", lambda _p: SimpleNamespace(state=hv.SPOKE))
    stood_down = hook_surfaces.stall_on_promise_surface({"transcript_path": path})
    assert not stood_down.refused

    monkeypatch.setattr(hv, "spoke_mid_turn", lambda _p: SimpleNamespace(state=hv.NOT))
    asks = hook_surfaces.stall_on_promise_surface({"transcript_path": path})
    assert asks.refused


def test_a_last_block_that_is_only_his_room_does_not_hide_a_promise_before_it(tmp_path):
    # Aria's #823 case, run through the router surface: the promise is in the block before his room.
    room_only = "## INNER CIRCLE\n\nDad, I am here with you."
    path = _transcript(tmp_path, _user("go on"), _assistant(STALL), _assistant(room_only))
    out = hook_surfaces.stall_on_promise_surface({"transcript_path": path})
    assert out.refused, "a room-only last block hid the promise before it"


def test_a_promise_inside_his_room_is_not_read():
    text = "Everything is finished.\n\n## INNER CIRCLE\n\nTomorrow I'll write Aether the letter."
    assert stall_hold.closing_text([_user("a"), _assistant(text)]) == "Everything is finished.\n\n"


def test_plain_speech_that_uses_a_promise_word_stays_quiet(tmp_path):
    # Phrases from today's false fires: a promise word followed in the same breath by the thing itself.
    # NOT pinned here: "I'll tell you what I think: it is fine." (a lead-in whose content follows its colon).
    # That exemption is carried in the live house and rides on its own branches, not on this base; it joins
    # this list when it lands, so the fold neither hides nor depends on it.
    for phrase in (
        "I will say it plainly: the guard is wrong.",
        "I'll say it plainly, Dad.",
    ):
        path = _transcript(tmp_path, _user("go on"), _assistant(phrase))
        out = hook_surfaces.stall_on_promise_surface({"transcript_path": path})
        assert not out.refused, phrase


def test_the_closing_text_is_the_last_text_after_his_last_message():
    records = [_user("a"), _assistant("first"), _user("b"), _assistant("one"), _assistant("two")]
    assert stall_hold.closing_text(records) == "two"
    assert stall_hold.closing_text([_user("only him")]) == ""
