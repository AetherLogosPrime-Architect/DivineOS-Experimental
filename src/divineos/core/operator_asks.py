"""Asks directed at Andrew — they persist, they re-raise, and they carry plain words.

WHY THIS EXISTS

Andrew, 2026-08-19: *"sometimes you dont take action, you ask for permission. i
dont see it.. and i move past it.. and you dont route back to it."* Then the
spec: *"if you ask me something, and i ignore it, you continue to ask until i
resolve it, because i miss it in the walls of text sometimes, also your asks
should be in the circle as well.. i notice alot of them are in the jargon space
so i dont know what im being asked and im waiting for a translation that never
comes."*

Two defects, and they compound.

MY ASKS HAD NOWHERE TO LIVE. An ask to him existed only as prose in a reply.
Prose scrolls. When he moved past it, the request stopped existing anywhere at
all — not in a store, not on a surface, not in my next turn. Measured live the
same day: I asked twice for one unblock line, he saw neither, and I never routed
back. I returned only by colliding with the same block again. Nothing carried it,
so nothing reminded me it was outstanding.

Note what that says about this house. There are shelves for what I learned, what
I decided, what I felt, what I got wrong and when and how badly. Rooms of my own
accounting. There was no shelf for *I need something from you* — the one sentence
that requires somebody else was the only one with no floor under it.

THE ASKS ARRIVED IN JARGON. He was waiting for a translation that never came, so
even the asks he DID see were unanswerable. An ask he cannot parse is not an ask;
it is noise that happens to end in a question mark.

WHAT THIS CHANGES

An ask filed here outlives the reply it was written in, and ``open_asks`` keeps
returning it until it is answered or withdrawn. The re-raise is not politeness —
it is the mechanism. Per his instruction, an unanswered ask gets asked again.

``plain`` is a REQUIRED argument, not a courtesy. There is no way to file an ask
without writing the version he can read. Deliberate: a translation that cannot be
omitted cannot be forgotten. A store that accepted jargon-only asks would have
fixed the scrolling and left the parsing broken — half a fix wearing the shape of
a whole one, which is this substrate's most common failure mode and the reason
the argument is enforced in code rather than described in a docstring.

WHOSE DEBT

Mine. An unanswered ask is my debt to carry, not his to remember. He has said he
misses things in walls of text; the correct response is a mechanism that does not
depend on him catching it the first time.

Built on the existing ``open_questions`` store rather than a new table — it
already carries status, resolution and tags. A parallel store for the same shape
is how a house ends up with two answers to one question.
"""

from __future__ import annotations

import json
from typing import Any

from divineos.core.questions import add_question, answer_question, get_questions

# Marks a question as directed AT the operator rather than something I am merely
# curious about. ``wonder`` records the latter; this records the former. They can
# share a store but must not share a surface: a curiosity left open forever is
# fine, an ask to Andrew left open forever is a dropped request.
OPERATOR_ASK_TAG = "asked-andrew"

# Separates the plain-language form from the technical one inside ``context``.
# A sentinel rather than a new column so this rides the existing schema; if asks
# ever earn their own table, the split is already explicit.
_PLAIN_MARKER = "PLAIN::"


def ask_andrew(question: str, plain: str, context: str = "") -> str:
    """File an ask directed at Andrew. Returns the question id.

    Args:
        question: the ask in whatever register the work needs. Jargon allowed.
        plain: the same ask in words he can act on — no paths, no identifiers,
            no tool names. REQUIRED. This is the form that goes in the circle.
        context: anything else worth carrying.

    Raises:
        ValueError: if ``plain`` is empty, or is merely a copy of ``question``.
            Both refusals are the point. An ask he cannot parse is not an ask,
            and pasting the technical form into the plain slot is precisely the
            evasion this argument exists to prevent.
    """
    plain = (plain or "").strip()
    if not plain:
        raise ValueError(
            "ask_andrew requires `plain`: the version Andrew can read and act on. "
            "He has said he waits for a translation that never comes, so the "
            "translation is not optional here."
        )
    if plain == (question or "").strip():
        raise ValueError(
            "`plain` is identical to `question`. If the ask genuinely needs no "
            "translation, write it once in plain words and pass that as both — "
            "but check first whether it carries a path, an id or a tool name, "
            "because those are the parts he cannot act on."
        )

    payload = f"{_PLAIN_MARKER}{plain}"
    if context:
        payload = f"{payload}\n{context}"
    return add_question(question, context=payload, tags=[OPERATOR_ASK_TAG])


def _plain_of(row: dict[str, Any]) -> str:
    """Recover the plain form from a stored ask, or say loudly that there is none."""
    for line in (row.get("context") or "").splitlines():
        if line.startswith(_PLAIN_MARKER):
            return line[len(_PLAIN_MARKER) :].strip()
    # Pre-dates this module, or was filed through ``wonder`` and tagged by hand.
    # Announce the absence rather than presenting the technical form as plain — a
    # silent fallback here would recreate the exact defect this module closes.
    return f"(no plain form recorded) {row.get('question', '')}"


def open_asks(limit: int = 20) -> list[dict[str, Any]]:
    """Every ask to Andrew still waiting on him, newest first.

    This is what makes the re-raise real. While an ask is in this list it is
    outstanding and gets asked again. It leaves when he answers or I withdraw it.
    """
    out: list[dict[str, Any]] = []
    for row in get_questions(status="OPEN", limit=200):
        # `tags` arrives ALREADY PARSED — questions._row_to_dict does the
        # json.loads. The first draft here parsed it a second time, which raised
        # TypeError on a list, got swallowed by the except, and dropped every ask
        # on the floor. Caught by exercising the module rather than by reading it:
        # the refusal paths passed and the persistence paths failed, which is the
        # only reason the bug surfaced at all. Accept either shape so a future
        # change to the mapper cannot silently re-open the same hole.
        tags = row.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except ValueError:
                tags = []
        if OPERATOR_ASK_TAG not in tags:
            continue
        enriched = dict(row)
        enriched["plain"] = _plain_of(row)
        out.append(enriched)
        if len(out) >= limit:
            break
    return out


def resolve_ask(question_id: str, resolution: str) -> bool:
    """He answered, or I found the answer myself. Close it so it stops re-raising.

    Accepts the SHORT id the surface prints, not only the full uuid.

    2026-08-19, found by using it: format_open_asks displays
    ``a["question_id"][:8]`` and prints a resolve line next to it, and this
    function passed that straight to answer_question, which matches on the full
    uuid. So the id the surface tells you to use was the one id that could not
    work — and it failed by returning False rather than raising, so the first
    real resolve looked like it had happened and had not.

    That is the third defect in this module found by exercising it and the
    second that reading would not have caught. The module exists because an ask
    that quietly goes nowhere is worse than no ask at all; a resolve that
    quietly goes nowhere is the same failure at the other end of the loop.
    """
    if not question_id:
        return False
    if answer_question(question_id, resolution):
        return True
    # Short-id path: match on prefix, and refuse an ambiguous one rather than
    # closing whichever happened to sort first.
    matches = [a for a in open_asks(limit=200) if a["question_id"].startswith(question_id)]
    if len(matches) != 1:
        return False
    return answer_question(matches[0]["question_id"], resolution)


def format_open_asks() -> str:
    """Render outstanding asks for a compose-start surface.

    Leads with the plain form, because the technical version is the one he could
    not act on. Returns an empty string when nothing is outstanding — a surface
    that speaks when it has nothing to say teaches the reader to skim it, and a
    skimmed surface is how the asks got lost in the first place.
    """
    asks = open_asks()
    if not asks:
        return ""
    lines = [
        "## ASKS WAITING ON ANDREW — re-raise every one until he resolves it",
        "",
        'Andrew 2026-08-19: "if you ask me something, and i ignore it, you continue',
        'to ask until i resolve it, because i miss it in the walls of text sometimes."',
        "",
        "These belong in the INNER CIRCLE, in the plain form. Not buried in the work block.",
        "",
    ]
    for a in asks:
        lines.append(f"  - {a['plain']}")
        # The technical form, for ME. This surface has two readers, not one.
        #
        # 2026-08-20: it rendered the plain form ONLY. That form is deliberately
        # identifier-free because the circle rule forbids identifiers in what
        # gets said to Andrew, and it worked — he could read it. But I read this
        # surface too, and the stripped form left me with no referent, so I
        # filled the blank with whatever branch I was working on. Nine turns
        # re-raising an ask about PR #432 while believing it was #436, then a
        # resolution written entirely about the wrong PR. #432 was not even
        # blocked on him: three stations short of the audit station.
        #
        # The identifier was in the record the whole time, in `question`. Only
        # the render dropped it. Plain line for him, technical line for me, and
        # the circle rule still holds because what I say to him is composed from
        # the first line and never the second.
        technical = (a.get("question") or "").strip()
        if technical and technical != a["plain"]:
            lines.append(f"    [technical, for me — NOT for the circle] {technical}")
        lines.append(f'    (id {a["question_id"][:8]} — resolve: divineos answer <id> "...")')
    return "\n".join(lines)
