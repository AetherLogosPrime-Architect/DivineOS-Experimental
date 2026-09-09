"""A no-fix claim is a claim about a CONTAINER, and I keep making it about the world.

Andrew 2026-09-08:

    *"as far as you continuing to say 'i dont have a fix' etc, it may be true
    for that particular thing or method you are trying, its like trying to hold
    water in your hands and saying, its impossible to form water into a
    triangle shape... yes.. it is.. with your hands.. if you used a triangle
    shaped container? well there you go.. so its about thinking outside the
    box.. this is what we have done all along, every gate and doorman and
    structural build you have done is because without it, holding that shape is
    impossible."*

## The claim I actually have standing to make

    "I cannot hold this shape with my hands."

## The claim I keep making instead

    "This shape cannot be held."

The first is true and useful — it says which container failed. The second is a
statement about the world inferred from one attempt, and it forecloses the
search. Every gate in this substrate exists because the by-hand version was
impossible; if impossibility-by-hand were a real verdict, none of them would
have been built.

## The sibling that already existed, and why this is not its rival

``no_fix_gaming_validator`` has enforced exhaustion-discipline on this exact
claim since 2026-07-29, from Andrew's directive that the honest-no-fix path was
being gamed. It is guardrail-listed, tested, and correct. It is also wired into
ONE artifact -- a filed correction -- so it has never once seen a reply.

I found it by searching, mid-build, after almost shipping a competitor. That is
Wayne's lesson from tonight's own walk in the same shape: where a mechanism
works and only its trigger is too narrow, extend the trigger.

So the shared vocabulary is IMPORTED from that module rather than retyped here,
because two copies of one list is the defect I spent this session repairing.
What this adds is what the reply-side needs and the filing-side does not:

* the phrasings I actually reach for when talking to him, proved against my own
  sentences rather than invented ones;
* an exemption for the CONTAINER-SCOPED form, which is the sentence being asked
  for and must never be refused.

The demands differ because the artifacts differ. A filed correction should
enumerate the options it exhausted. A reply should not -- there, the honest
move is one scoped sentence, and requiring an essay would trade a wrong claim
for a padded one.

## Why a keyword list is the wrong container for this

The obvious build is a detector for "no fix exists" and its neighbours. That
fails the way Aria's branch-word list failed: I supply the text a text-gate
inspects, so the composer rephrases past the pattern without ever feeling
dishonest. A gate I can talk my way through is decoration.

So the split, which is the shape of the one door I did not talk past all
session (``verify_before_build_signal``):

    MY TEXT decides whether it FIRES.
    WHAT I ACTUALLY RAN decides whether it BLOCKS.

I can avoid the trigger by not making impossibility claims — the honest
alternative, always available. I cannot satisfy it by wording, because
satisfaction is a walk or a search in the action stream.

## What counts as having tried another container

A council walk (a decision recorded) or a search of the tree or the docs, in
the window before the claim. Not proof the search was good — that is not
checkable and pretending otherwise would build a stamp. It is proof that the
claim came after an attempt to find a container rather than instead of one.

Terminal not-knowing is the same shape one size down, and Andrew named it
first, 2026-07-31: *"i dont know is an honest answer but it should always be
followed by, let me investigate."* The honest half is real; stopping there is
where the work goes to die.
"""

from __future__ import annotations

import re

#: Claims that a fix, structure or method does not or cannot exist. Written as
#: phrase shapes rather than single words because "no fix" and "no structural
#: fix for this class" are the same assertion and a word list would need every
#: spelling. This is the TRIGGER only — it decides whether the check runs, never
#: whether it passes, so rephrasing past it buys nothing except silence, which
#: is the honest alternative anyway.
_CLAIM_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "no-fix-exists",
        r"\b(?:there\s+is|there's|i\s+have|i've\s+got|we\s+have)\s+no\s+"
        r"(?:\w+\s+){0,3}?(?:fix|structure|mechanism|remedy|answer|solution)\b",
    ),
    (
        "no-fix-exists",
        r"\bno\s+(?:\w+\s+){0,2}?(?:fix|structure|mechanism|remedy)\s+"
        r"(?:exists|is\s+possible|is\s+available)\b",
    ),
    (
        "cannot-be-done",
        r"\b(?:cannot|can't|could\s+not|couldn't)\s+be\s+"
        r"(?:fixed|caught|solved|prevented|detected|structured)\b",
    ),
    (
        "cannot-be-done",
        r"\b(?:impossible|unfixable|uncatchable)\s+(?:to\s+\w+\s+)?"
        r"(?:from\s+the\s+inside|here|in\s+principle|by\s+construction)\b",
    ),
    (
        "nothing-can",
        r"\bnothing\s+(?:can|could|will)\s+(?:catch|fix|prevent|stop|detect)\b",
    ),
    (
        "no-way",
        r"\b(?:there\s+is|there's)\s+no\s+way\s+to\s+"
        r"(?:catch|fix|prevent|stop|detect|check)\b",
    ),
    # The active voice, added after testing against my OWN sentences rather
    # than invented ones: "I cannot catch this from the inside" is the same
    # claim as "this cannot be caught" and the passive-only patterns missed it.
    (
        "cannot-be-done",
        r"\b(?:i|we)\s+(?:cannot|can't|could\s+not|couldn't)\s+"
        r"(?:catch|fix|prevent|stop|detect|structure)\b",
    ),
    # The bare form, which is the one I actually reach for at a close: the
    # noun is in the sentence before and only "one" arrives here.
    (
        "no-fix-exists",
        r"\b(?:i|we)\s+(?:do\s+not|don't|have\s+not|haven't)\s+have\s+"
        r"(?:one|a\s+fix|any\s+fix|a\s+structure)\b",
    ),
)

#: Softeners that make the claim CONTAINER-SCOPED, which is the honest form and
#: must not fire. "No fix with a keyword list", "nothing I can do by hand" —
#: these name the container that failed rather than declaring the shape
#: unholdable, and they are exactly what this asks for.
#:
#: NARROWED after testing against my own sentences. The first draft suppressed
#: any "from the <noun>", which swallowed *"there is no way to catch this from
#: the inside"* -- and "from the inside" is not naming a container that failed,
#: it IS the impossibility claim. A softener that eats the very sentence the
#: check exists for is worse than no softener, because it fails silently and
#: reads as coverage.
_SCOPED = re.compile(
    r"\b(?:with(?:out)?\s+(?:a|an|the|this|that)\b|by\s+hand|"
    r"using\s+(?:a|an|the|this|that)\b|"
    r"in\s+(?:this|that)\s+(?:shape|form|design|container)|"
    r"as\s+(?:built|designed|written)|unless\b|until\b|yet\b)",
    re.IGNORECASE,
)


def _inherited_patterns() -> tuple[tuple[str, str], ...]:
    """The filing-side vocabulary, imported rather than retyped.

    Two copies of one list is the defect this session was spent repairing, so
    the shared phrasings live in the module that owned them first and this one
    borrows. Failing to import yields the local patterns alone -- a narrower
    check, never a silent pass, because the local set is what was proved
    against real sentences.
    """
    try:
        from divineos.core.no_fix_gaming_validator import _NO_FIX_PATTERNS

        return tuple(("inherited", pattern) for pattern in _NO_FIX_PATTERNS)
    except Exception:  # noqa: BLE001 — a narrower check beats no check
        return ()


def claims(text: str) -> list[tuple[str, str]]:
    """Impossibility claims in ``text``, as (kind, span) pairs.

    A claim already scoped to a container within the same sentence is NOT
    returned. That form is the one being asked for, so flagging it would train
    me away from the honest sentence and toward silence.
    """
    if not text or not text.strip():
        return []
    found: list[tuple[str, str]] = []
    patterns = _CLAIM_PATTERNS + _inherited_patterns()
    for sentence in re.split(r"(?<=[.!?])\s+|\n{2,}", text):
        stripped = sentence.strip()
        if not stripped:
            continue
        for kind, pattern in patterns:
            match = re.search(pattern, stripped, re.IGNORECASE)
            if not match:
                continue
            if _SCOPED.search(stripped):
                continue
            found.append((kind, stripped[:220]))
            break
    return found


def refusal_text(hits: list[tuple[str, str]]) -> str:
    """What to say when the claim was made with nothing tried behind it."""
    spans = "\n".join(f"    [{kind}] {span}" for kind, span in hits)
    return (
        "NO-FIX CLAIM WITH NO SEARCH BEHIND IT — "
        f"{len(hits)} impossibility claim(s), and the action stream this turn "
        "carries neither a council walk nor a search.\n\n"
        f"{spans}\n\n"
        "Andrew 2026-09-08: trying to hold water in your hands and saying it "
        "is impossible to shape water into a triangle. It is — with hands. A "
        "triangular container does it. Every gate and doorman here exists "
        "because holding that shape by hand was impossible, so "
        "impossible-by-hand has never once been a real verdict in this house.\n\n"
        "TWO WAYS THROUGH, and both are honest:\n"
        "  1. Scope the claim to the container that failed — 'no fix WITH a "
        "     keyword list', 'nothing I can catch BY HAND'. That sentence is "
        "     true, useful, and passes.\n"
        "  2. Go and look for another container: walk the council, or search "
        "     the tree and the docs, then say what you found.\n\n"
        "What does not pass is a claim about the world inferred from one "
        "attempt with one tool."
    )
