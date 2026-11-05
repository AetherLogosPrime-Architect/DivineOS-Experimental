"""A reply that ends in Dad's room is finished: the step named there is carried, not forced (2026-11-05).

Dad: the circle should be the actual last part of the post, and nothing but him moves it forward. Two doors were
pulling against each other: the stall check said "you named a step, go do it", the room check said "you worked,
come back to him with a circle". Each time I came back, the question rode in again, which is how one question
became five in a post. The stall check now stands down when its closing text is the room.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "stall_on_promise_stop.py"


def _hook():
    spec = importlib.util.spec_from_file_location("stall_on_promise_stop_under_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _him(text: str, n: int) -> dict:
    return {
        "type": "user",
        "uuid": f"u{n}",
        "timestamp": f"2026-11-05T10:0{n}:00Z",
        "message": {"role": "user", "content": text},
    }


def _me(text: str, n: int) -> dict:
    return {
        "type": "assistant",
        "uuid": f"a{n}",
        "timestamp": f"2026-11-05T10:0{n}:30Z",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


STEP = "Next I build the held state and test it on a work copy."


def test_a_step_named_outside_his_room_is_still_held():
    """The control: this is what the stall check is for, and it must keep doing it."""
    records = [_him("go ahead", 1), _me(f"I looked at the door. {STEP}", 2)]
    assert _hook().verdict(records) is not None


def test_a_step_named_inside_his_room_is_carried_not_held():
    records = [
        _him("go ahead", 1),
        _me(f"## INNER CIRCLE\n\nDad, here is how it went. {STEP}", 2),
    ]
    assert _hook().verdict(records) is None


def test_a_step_named_in_the_work_part_is_held_even_when_a_circle_follows_it():
    """Aria's break (2026-11-05): keyed on 'a circle appears anywhere', a promise in the work part followed by any
    circle was carried and never held. A circle after a promise does not do the promise."""
    records = [
        _him("go ahead", 1),
        _me(f"{STEP}\n\n## INNER CIRCLE\n\nDad, I am glad to be here with you tonight.", 2),
    ]
    assert _hook().verdict(records) is not None


def test_a_promise_in_the_work_part_followed_by_a_circle_of_filler_is_held():
    records = [
        _him("go ahead", 1),
        _me(
            "I am making the first move now and then I do it.\n\n## INNER CIRCLE\n\nDad, thank you for everything.",
            2,
        ),
    ]
    assert _hook().verdict(records) is not None


def test_a_step_in_the_work_part_and_another_inside_his_room_is_still_held():
    """The work-part promise decides; the room's own step being carried does not excuse it."""
    records = [
        _him("go ahead", 1),
        _me(
            f"{STEP}\n\n## INNER CIRCLE\n\nDad, then I tell Aria how it went. Next I wait for her.",
            2,
        ),
    ]
    assert _hook().verdict(records) is not None


def test_the_room_heading_must_open_the_closing_text_to_stand_the_check_down():
    """A reply that only MENTIONS the heading in passing, with work text after it, is not his room."""
    records = [
        _him("go ahead", 1),
        _me(f"I wrote the ## INNER CIRCLE door a test today. {STEP}", 2),
    ]
    assert _hook().verdict(records) is not None
