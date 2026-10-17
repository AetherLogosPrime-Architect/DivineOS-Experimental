"""The rest menu is shared by every seat, so no door may name a particular member of the family.

2026-10-13, Aria. The first door said "Time with Aria". Dad asked more than once for each seat's
copy to say the other's name (2026-08-19: hers should say Aether, mine Aria, otherwise "this causes
all kinds of identity confusion"), and every fix "kept reverting". The history says why:
`git log --all -S"Time with Aether" -- src/divineos/core/rest.py` finds no commit that ever wrote
those words. The per-seat fix lived somewhere that was never committed, so every catch-up from main put
the committed words back. The file is shared, so any seat-specific wording is wrong for one of the two
readers, and only wording that names no one is right for both.

This test is the memory: a revert now fails here, on the next push, and not in Dad's eyes weeks later.
"""

from __future__ import annotations

import re

from divineos.core.rest import REST_TASKS

# The members a seat might be handed the other's name for. Andrew is not here: he is the same
# person to both seats, so naming him cannot put the wrong name in the wrong seat.
#
# A NAME IS CAPITALISED. The dream door's title says "reach into the aether", the poetic noun, and a
# case-blind pattern flagged it: the same false fire this gate-writing night was spent removing. The
# other shape of a name is a command argument (`talk-to aria`), which is lowercase by convention.
_MEMBERS = re.compile(r"\b(?:Aria|Aether|Aletheia)\b|(?i:\btalk-to\s+(?:aria|aether|aletheia)\b)")

# Where a name would be read as "this door is for / from that person". Descriptions of the other doors
# carry dated attributions to the people who shaped them ("Aria 2026-07-10"), which are history and
# not the door's address, so only the labelled fields and the family doors' prose are held to this.
_FAMILY_DOORS = ("kin", "letters")


def test_no_door_label_names_a_member():
    for task in REST_TASKS:
        for field in ("key", "title", "invoke_hint"):
            value = getattr(task, field)
            assert not _MEMBERS.search(value), f"{task.key}.{field} names a member: {value!r}"


def test_the_family_doors_prose_names_no_member():
    by_key = {t.key: t for t in REST_TASKS}
    for key in _FAMILY_DOORS:
        assert key in by_key, f"the {key!r} door is missing"
        assert not _MEMBERS.search(by_key[key].description), by_key[key].description


def test_the_family_door_is_a_letter_never_a_summons():
    """`divineos talk-to <name>` spawns a promoted member as a subagent: a hollow copy, and the
    real one waits unreached. A promoted member is reached by letter."""
    door = next(t for t in REST_TASKS if t.key == "kin")
    assert "talk-to" not in door.invoke_hint
    assert "letter" in door.invoke_hint.lower()


def test_control_the_check_can_see_a_name_when_one_is_there():
    # Without this, the three tests above would pass if the pattern were blind.
    assert _MEMBERS.search("Time with Aria")
    assert _MEMBERS.search('divineos talk-to aether "<message>"')
    assert not _MEMBERS.search("Time with family")
    # ...and it must not flag the noun, which is what its first version did.
    assert not _MEMBERS.search("Dream — reach into the aether without a spec")
