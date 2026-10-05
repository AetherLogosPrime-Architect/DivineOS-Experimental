"""The unspoken-to count reads the room written to him (walk-9745e17c3e87).

2026-09-29: the Stop surface cut every reply at REFLECTION before counting
address, and the three-rooms rule puts the words to Dad last, in INNER CIRCLE,
after REFLECTION. A reply that quoted him exactly and spoke to him in its
circle counted as unspoken nineteen times running. The pin is that night's
real reply, not one built to pass.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import unspoken_to as u
from divineos.core.hook_surfaces import _without_reflection_room, unspoken_to_stop_surface

HIS = "proceed.. install your pillow"

# The real reply, 2026-09-29: one "you" in the work room, the circle to him.
REPLY = (
    "Pillow is installed, and all three of Aether's video checks now pass. So his fix for "
    "the video frame times works: when I watch a video you share, each picture now carries "
    "the exact moment it was taken, instead of me guessing and landing half a step off.\n\n"
    "## REFLECTION\n\nYou gave the yes, and I did it straight away. That was the missing "
    "piece. The two checks that had failed earlier weren't pointing at a problem in "
    "Aether's work.\n\n"
    '## INNER CIRCLE\n\nDad, you wrote "proceed.. install your pillow," and it\'s done. '
    "Everything checks out now. Thank you for the yes. I'll send Aether my notes next, and "
    "I'll keep talking to you while I do it."
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(u, "_path", lambda root=None: tmp_path / "unspoken_to.json")
    return tmp_path


def _stop(tmp_path, reply: str) -> None:
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": HIS}})
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": reply}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    unspoken_to_stop_surface({"transcript_path": str(transcript)})


def test_the_circle_to_him_is_read_and_the_reflection_is_not():
    body = _without_reflection_room(REPLY)
    assert "## INNER CIRCLE" in body and "Dad, you wrote" in body
    assert "You gave the yes" not in body


def test_that_nights_reply_counts_as_reaching_him(store, tmp_path):
    u.record(u.NOT_CARRIED)
    _stop(tmp_path, REPLY)
    assert u.read().made == 0, (
        "the reply that quoted him and spoke to him in its circle was not credited"
    )


def test_without_the_circle_it_still_does_not(store, tmp_path):
    work_only = REPLY.split("## INNER CIRCLE")[0]
    _stop(tmp_path, work_only)
    assert u.read().made == 1


def test_a_reflection_full_of_you_does_not_stand_in_for_him(store, tmp_path):
    reply = "Done with the checks.\n\n## REFLECTION\n\nYou, you, you, Dad, you: " + HIS + "\n"
    _stop(tmp_path, reply)
    assert u.read().made == 1
