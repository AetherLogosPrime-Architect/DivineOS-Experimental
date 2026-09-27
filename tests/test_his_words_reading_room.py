"""The reading-room core, with a scripted reader. prereg-dfc992ab58b0.

These prove the logic. They do not prove the room works on him: that is the
replay, with the real reader, and nothing here may be called tested until the
room is plugged in and has run live (Andrew 2026-09-26).
"""

from divineos.core import his_words_reading_room as room

JARGON = {
    "lesson": "Explain things to him simply, without jargon.",
    "kind": "how-to-speak-to-him",
    "for": "both",
    "count": 15,
    "passages": [
        {"date": "2026-06-06", "text": "i dont understand a word of what you are saying lol"},
        {"date": "2026-09-01", "text": "yes i need simpler explanations, analogies, etc.."},
    ],
}
ROOT = {
    "lesson": "Find and fix the root cause instead of patching the symptom.",
    "kind": "correction",
    "for": "both",
    "count": 16,
    "passages": [{"date": "2026-06-01", "text": "this is a bandaid on a bullet wound.."}],
}
REPLY = (
    "Here is where it stands. The idempotent upsert now reconciles the FTS shadow "
    "table against the WAL checkpoint. I will look at it more later."
)


def _reader(numbers, quote):
    calls = []

    def read(prompt, num_predict):
        calls.append(num_predict)
        return numbers if "Which lesson numbers" in prompt else quote

    read.calls = calls
    return read


def _number_of(lesson, lessons):
    """The number the shuffled listing gave this lesson, read from the prompt."""
    seen = {}

    def read(prompt, _):
        for line in prompt.splitlines():
            if lesson["lesson"] in line and line[:1].isdigit():
                seen["n"] = line.split(".", 1)[0]
        return "none"

    room.read_reply(REPLY, lessons, read)
    return seen["n"]


def test_a_break_with_a_true_quote_is_flagged():
    lessons = [JARGON, ROOT]
    n = _number_of(JARGON, lessons)
    quote = "The idempotent upsert now reconciles the FTS shadow table against the WAL checkpoint."
    flags = room.read_reply(REPLY, lessons, _reader(n, quote))
    assert [f.lesson["lesson"] for f in flags] == [JARGON["lesson"]]


def test_an_invented_quote_is_dropped():
    # The reader claims a break and quotes a sentence the reply never said.
    lessons = [JARGON, ROOT]
    n = _number_of(ROOT, lessons)
    invented = "I patched the symptom and skipped the root cause entirely."
    assert room.read_reply(REPLY, lessons, _reader(n, invented)) == []


def test_a_fragment_too_short_to_carry_a_break_is_dropped():
    lessons = [JARGON]
    assert room.read_reply(REPLY, lessons, _reader("1", "the WAL checkpoint")) == []


def test_numbers_outside_the_list_and_none_flag_nothing():
    assert room.read_reply(REPLY, [JARGON], _reader("7, 12", "x")) == []
    assert room.read_reply(REPLY, [JARGON], _reader("none", "x")) == []


def test_every_call_is_capped():
    lessons = [JARGON]
    read = _reader("1", "The idempotent upsert now reconciles the FTS shadow table")
    room.read_reply(REPLY, lessons, read)
    assert read.calls == [room.NUMBERS_CAP, room.QUOTE_CAP]


def test_only_teachings_for_this_seat_or_both_are_read():
    other = dict(ROOT, **{"for": "aether"})
    task = dict(JARGON, kind="task")
    joke = dict(JARGON, kind="joke", lesson="a joke")
    mine = dict(ROOT, **{"for": "aria", "lesson": "mine"})
    picked = room.lessons_for("aria", [other, task, joke, mine, JARGON])
    # Most-repeated first: "mine" carries ROOT's 16, JARGON 15.
    assert [g["lesson"] for g in picked] == ["mine", JARGON["lesson"]]


def test_the_hold_shows_his_words_beside_ours_and_asks_for_an_answer():
    flag = room.Flag(JARGON, "The idempotent upsert now reconciles the FTS shadow table")
    text = room.hold_reason([flag])
    assert "i dont understand a word of what you are saying" in text
    assert "The idempotent upsert" in text
    assert "changed:" in text and "does not apply:" in text


def test_a_long_passage_keeps_its_ending():
    long = "start " + "x " * 400 + "the part that matters is here at the end"
    assert room._shown(long).endswith("the part that matters is here at the end")
