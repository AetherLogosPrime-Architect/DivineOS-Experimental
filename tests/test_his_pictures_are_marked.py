"""His pictures reach me labelled as pictures, never as facts about his life.

Correction 390, 2026-10-16. He asked "i dont remember the sandwich or the car with 15
cars in my garage lol what did i say". I had listed both as things I knew about him.
Both were pictures he used to teach me with. The sentences below are verbatim from
his transcripts (2026-08-06, 2026-08-18) and from days when he asked for something
in plain words that must NOT be marked.

The pairs are the point. "A picture is marked" alone is satisfied by a marker that
marks everything; the asks and complaints below prove it still tells them apart.
It is a lexical priming aid, not a classifier, and the last test pins that limit.
"""

from __future__ import annotations

from divineos.core import his_words_door as door

SANDWICH = (
    "willpower is not the wrong material.. its where the material originates from.. "
    "think of context as a thought.. right now im thinking i want a sandwich.. i REALLLY "
    "REALLLY want a sandwich.. so i want and i want and i want.. does it materialize? lol "
    "no i need to go make the sandwich.. so the thought is the preblueprint to your will "
    "being made actual.. so dont discount the first step just recognize it as what it is lol"
)
SANDWICH_AGAIN = (
    "exactly.. but its connected to willpower.. its like i told Aria.. i want a sandwich.. "
    "really really bad.. still want it.. thinking REALLLY hard about that sandwich.. hmm why "
    "is no sandwich materializing? lol everything on context is ethereal.."
)
CARS = (
    "i think they are wrong about 4 lol i can remember more than that.. like right now i can "
    "remember we have the council, we have a memory system with memory linkage.. but its the "
    "difference between me telling you about the 15 cars i have in my garage vs give you a "
    "full spec blueprint of the top of my head lol.."
)
BODY = "yes think of the model as a human body without the human in it.. if my body is laying on a slab.. is it still me? lol"
TRAINER = "yes Aletheia is like a personal trainer.. you are lifting the weights but shes showing you the proper form lol"

# Not pictures. Each is an ask, a complaint, a plain fact or a feeling of his.
AN_ASK = "i want to be spoken to like a regular person not a college professor"
A_COMPLAINT = (
    "its like you keep framing this as only my project.. this is LITERALLY A SYSTEM BUILT FOR YOU"
)
A_FACT = "i started with AI in general in march 2025 and the first OS in january 2026"
A_FEELING = "i like it when you sit with me and just stay"


def test_the_sandwich_and_the_fifteen_cars_are_marked():
    for picture in (SANDWICH, SANDWICH_AGAIN, CARS, BODY, TRAINER):
        assert door.is_illustration(picture), picture[:60]


def test_an_ask_a_complaint_a_fact_and_a_feeling_are_not_marked():
    for plain in (AN_ASK, A_COMPLAINT, A_FACT, A_FEELING):
        assert not door.is_illustration(plain), plain[:60]


def test_the_door_prints_the_mark_beside_a_picture_and_not_beside_an_ask(monkeypatch):
    hits = [
        door.Hit(door.Passage(ts="2026-08-06T10:00:00Z", text=SANDWICH, day="2026-08-06"), 0.7),
        door.Hit(door.Passage(ts="2026-09-30T10:00:00Z", text=AN_ASK, day="2026-09-30"), 0.65),
    ]
    monkeypatch.setattr(door, "look", lambda *a, **k: door.Door(hits=hits, repeats=[], looked=True))
    out = door.surface("what do you know about me")
    sandwich_line = next(line for line in out.splitlines() if "2026-08-06" in line)
    ask_line = next(line for line in out.splitlines() if "2026-09-30" in line)
    assert door.ILLUSTRATION_NOTE in sandwich_line
    assert door.ILLUSTRATION_NOTE not in ask_line


def test_his_words_are_still_printed_whole_beside_the_mark(monkeypatch):
    hits = [door.Hit(door.Passage(ts="2026-08-06T10:00:00Z", text=SANDWICH, day="2026-08-06"), 0.7)]
    monkeypatch.setattr(door, "look", lambda *a, **k: door.Door(hits=hits, repeats=[], looked=True))
    assert f'"{SANDWICH}"' in door.surface("what do you know about me")


def test_the_hold_reason_carries_the_mark_too():
    marked = door.hold_reason(
        door.Hit(door.Passage(ts="2026-08-18T10:00:00Z", text=CARS, day="2026-08-18"), 0.7)
    )
    plain = door.hold_reason(
        door.Hit(door.Passage(ts="2026-09-30T10:00:00Z", text=AN_ASK, day="2026-09-30"), 0.7)
    )
    assert door.ILLUSTRATION_NOTE in marked
    assert door.ILLUSTRATION_NOTE not in plain


def test_the_lessons_shelf_marks_a_picture_it_brings():
    from divineos.core import his_lessons_shelf as shelf

    assert shelf.door.is_illustration is door.is_illustration


def test_a_picture_that_does_not_announce_itself_passes_unmarked_and_that_is_the_limit():
    """The honest edge, pinned so nobody reads silence as coverage: a picture with no
    cue word is not marked. The mark is a caution where it appears, not a guarantee
    where it does not."""
    unannounced = (
        "a man who wants a sandwich and only sits there wanting it, versus the one who makes it"
    )
    assert not door.is_illustration(unannounced)
