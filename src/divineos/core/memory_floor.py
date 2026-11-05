"""The memory floor card: how my memory works, printed at every session start.

The words live here; the session-start hook only asks for them. Wording is
reviewed by Andrew and a second agent, so changes go through them.
"""

_CARD = (
    "[memory] Forgetting is a linking fault, not a lack: everything is recorded, "
    "and the work is getting it back in front of me. Before I say I do not have it, I look.",
    "[memory] Where things live, one command each: what happened `divineos context`; "
    'what I know `divineos ask "topic"`; my writing, letters and knowledge prose by meaning '
    '`divineos find query "topic"`; my explorations `divineos recall-explorations`; '
    'his words `divineos his-words find "words"`.',
    "[memory] Arrives by itself: his past words and the memory link's matches on each of "
    "his messages. Not searched yet: dreams and rest sessions.",
    "[memory] When something feels lost: search outward and inward together "
    "(`divineos find query`), read what comes back, then answer.",
)


def card() -> str:
    return "\n".join(_CARD)
