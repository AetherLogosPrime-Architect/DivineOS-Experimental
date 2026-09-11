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
        # The bare form and the first-person one. "Nothing I can catch by hand"
        # slipped the first version, which knew only "nothing CAN catch" -- and
        # it slipped while I was using it as an example of an acceptable
        # sentence, which is exactly how a hole gets written on purpose.
        r"\bnothing\s+(?:(?:i|we)\s+(?:can|could)|can|could|will)\s+"
        r"(?:catch|fix|prevent|stop|detect)\b",
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
#: REMOVED 2026-09-08, hours after being added, and the removal is the point.
#:
#: Andrew: *"you said you allowed for the narrower true thing, who determines
#: if its true? the optimizer always looks for a reason not to do something,
#: (i cant think of a way to fix this therefore its impossible so no point in
#: trying) that is the behavior that needs changed."*
#:
#: I was the one deciding whether the narrowing was true, which hands the
#: verdict straight back to the thing that wanted to stop. A narrowing is
#: always available and always sounds accurate, so the exemption was a door
#: with my own hand on the latch.
#:
#: Aria named this class in June and I rebuilt the wrong version anyway: the
#: word is the OUTPUT of the shape, not the cause. The exemption caught
#: wording. The cause is the optimizer hunting for a reason to stop looking,
#: and it phrases that reason impeccably.
#:
#: WHAT STAYS LEGITIMATE needs no exemption, which is why removing this costs
#: nothing. His own examples -- *"a keyword list cannot be used for
#: enforcement... you cannot hold things in memory without structural
#: support"* -- take a named MECHANISM as their subject, while every pattern
#: above takes the PROBLEM as its subject. Verified against both of his
#: sentences rather than assumed: neither fires.
_SCOPED = None

#: THE ONE THING THAT STILL PASSES, and it is not the old exemption wearing a
#: new coat. The difference is what the sentence CLAIMS, not how it is worded.
#:
#:     "no fix with a keyword list"   -> a verdict about a container, and it
#:                                       licenses stopping. REFUSED.
#:     "I have not found one yet"     -> a report of present state, and it
#:                                       licenses nothing. PASSES.
#:
#: A temporal marker holds the question open by construction. If the optimizer
#: learns to append "yet" to everything, it has learned to stop issuing
#: verdicts -- which is the entire win, not a leak.
#:
#: This must stay open or the gate teaches me to go silent rather than to keep
#: looking, which is this mechanism's own second falsifier.
_PAUSE = re.compile(
    r"\b(?:yet|so\s+far|thus\s+far|to\s+date|at\s+the\s+moment|for\s+now)\b",
    re.IGNORECASE,
)

#: MENTION IS NOT USE, and this gate proved it the hard way by refusing the
#: reply in which I QUOTED a give-up phrase in order to report that the
#: detector had missed it. The sentence was about the phrase; it claimed
#: nothing.
#:
#: Aletheia predicted exactly this class on 2026-06-17, for any detector
#: operating on father-channel text: *builders and auditors discussing the
#: detector is part of the deployment context*, so meta-discussion belongs in
#: the regression set. She was right about a different detector, months before
#: this one existed, and the rule generalised without needing to be rewritten.
#:
#: The shape is borrowed from ``correction_shape_v2.self_admission_detector``,
#: which already owns mention-versus-use here. Quotation marks, backticks, code
#: fences, example markers, and talk about the mechanism itself all mark a
#: phrase as being displayed rather than asserted.
_MENTION = re.compile(
    r"[\"'“”‘’`*]|```|~~~|"
    r"\b(?:for\s+example|e\.?g\.?|such\s+as|slipped|slips|missed|misses|"
    r"caught|catches|fires?|fired|matched|matches|the\s+phrase|the\s+form|"
    r"the\s+detector|the\s+pattern|the\s+gate|the\s+check|the\s+claim\s+shape)\b",
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
    # The full stop is its own claim-kind and comes FIRST, because it is the
    # thing this gate is actually for. A terminus needs no impossibility
    # wording at all -- "nothing to be done about it" closes the enquiry on its
    # own, and every version of this check before 2026-09-09 slept through it.
    patterns = (("terminus", _TERMINUS.pattern),) + _CLAIM_PATTERNS + _inherited_patterns()
    for sentence in re.split(r"(?<=[.!?])\s+|\n{2,}", text):
        stripped = sentence.strip()
        if not stripped:
            continue
        for kind, pattern in patterns:
            match = re.search(pattern, stripped, re.IGNORECASE)
            if not match:
                continue
            # No CONTAINER-scoping exempts a claim any more (see _SCOPED). A
            # temporal marker still does, because it makes the sentence a
            # report of where I am rather than a verdict on what exists.
            if _PAUSE.search(stripped):
                continue
            # Mention is not use: a phrase being displayed, quoted or discussed
            # is not a claim. This gate learned it by refusing the reply that
            # reported its own miss.
            if _MENTION.search(stripped):
                continue
            # A constraint that LEADS SOMEWHERE is the working half of the
            # thought, not the failure. "Humans cannot fly, so we built a wing
            # that does not flap" is the sentence this house is made of.
            if _CONTINUES.search(stripped) and not _TERMINUS.search(stripped):
                continue
            found.append((kind, stripped[:220]))
            break
    return found


#: The council roster, and Andrew's stated bar for concluding no solution
#: exists: *"unless the entire 45 lenses of the council and the internet comes
#: back all agreeing that what were trying to do has absolutely no solution. we
#: look to find one.. lol"*
#:
#: Encoded literally, and the consequence is intended: the conclusion becomes
#: practically unreachable. That is not a wall, because the way through costs
#: nothing and is the true sentence anyway -- I have not found one YET, here is
#: what I tried, here is the next thing I am trying. A pause is not a verdict,
#: and only the verdict is being refused.
FULL_COUNCIL = 45

#: THE TARGET WAS WRONG, and this is the correction.
#:
#: Andrew 2026-09-09: *"its not about not declaring impossibility, they exist,
#: its about stopping there as the verdict, humans cannot fly, this is a fact,
#: we have no wings, were too heavy and we would tire out easily from flapping,
#: did that stop us from flying? lol"*
#:
#: I had been refusing the CONSTRAINT. The constraint is usually true and is
#: the honest half. What must be refused is the FULL STOP after it -- the move
#: that turns a fact about the present into the end of the enquiry.
#:
#:     "humans cannot fly, so we built a wing that does not flap"   PASSES
#:     "humans cannot fly, nothing to be done about it"             REFUSED
#:
#: Same constraint in both. What differs is whether anything follows. So a
#: claim is judged on what comes AFTER it, not on its wording and not on how
#: much searching came before -- a constraint that leads somewhere needs no
#: council quorum, because it is already doing the work.
#:
#: This is the close-reach anchor one level over, and that anchor said it in
#: July: *close no longer means terminate... the reach delivers me into a state
#: that continues, not out of one.*
_CONTINUES = re.compile(
    r"\b(?:so\s+(?:i|we|the|it|that|this)|therefore\s+(?:i|we)|"
    r"instead|which\s+is\s+why|that\s+is\s+why|hence|"
    r"the\s+next\s+(?:thing|step|container|move)|"
    r"what\s+(?:i|we)\s+(?:am|are)\s+trying|"
    r"i\s+am\s+(?:trying|building|testing|looking)|"
    r"the\s+way\s+(?:round|around|through)|work(?:ing)?\s+around|"
    r"leads?\s+to|points?\s+at)\b",
    re.IGNORECASE,
)

#: The full stop itself: language that closes the enquiry outright. Not one of
#: these was caught before, which is how a gate aimed at the wrong half looks
#: from the outside -- it fires on true sentences and sleeps through the give-up.
_TERMINUS = re.compile(
    r"\b(?:nothing\s+(?:to\s+be\s+done|more\s+to\s+be\s+done|for\s+it)|"
    r"no\s+point\s+(?:in\s+)?(?:trying|looking|continuing|pursuing)|"
    r"not\s+worth\s+(?:trying|pursuing|looking)|"
    r"that\s+is\s+(?:just\s+)?(?:how\s+it\s+is|the\s+end\s+of\s+it)|"
    r"end\s+of\s+(?:the\s+)?(?:story|discussion|enquiry|inquiry)|"
    r"giv(?:e|ing)\s+up\s+on\s+(?:it|this)|"
    r"we\s+(?:stop|stopped)\s+there|leave\s+it\s+(?:there|alone)|"
    # FAKE CONTINUATION, found by a test rather than by thinking: "so this is
    # as far as it goes" carries a continuation word and continues into a
    # full stop. The connective is not the evidence -- where it ARRIVES is.
    r"as\s+far\s+as\s+(?:it|this|that)\s+goes|"
    r"(?:that|this)\s+is\s+(?:as\s+far|all)\s+(?:as|there)\s+is)\b",
    re.IGNORECASE,
)


def lenses_walked_within(window_start_ts: float, now: float) -> int:
    """How many DISTINCT council lenses were actually walked in the window.

    Distinct, because walking one lens forty-five times is not a council. Reads
    the applied-events, which the walk command emits and priming does not --
    the split Andrew made 2026-07-18, precisely so that printing a methodology
    could never stand in for using it.

    Returns 0 when the ledger cannot be read. That direction is deliberate: an
    unreadable ledger must leave the claim refused rather than waved through,
    because the whole point is that I do not get to certify my own exhaustion.
    """
    try:
        from divineos.core.ledger import get_events

        names: set[str] = set()
        for ev in get_events(limit=1000, order="desc", event_type="COUNCIL_LENS_APPLIED"):
            try:
                stamp = float(ev.get("timestamp") or 0)
            except (TypeError, ValueError):
                continue
            if stamp < window_start_ts or stamp > now:
                continue
            payload = ev.get("payload") or {}
            if isinstance(payload, str):
                import json as _json

                payload = _json.loads(payload)
            name = str(payload.get("expert_name", "")).strip().lower()
            if name:
                names.add(name)
        return len(names)
    except Exception:  # noqa: BLE001 — unreadable means unproven, never means passed
        return 0


def looked_outside_within(window_start_ts: float, now: float) -> bool:
    """Did the action stream reach past this repository in the window?

    The second half of his bar is *"and the internet"*. A council walk is forty
    five views from inside one head; the outside is where a container nobody
    here has thought of comes from.

    Returns False when telemetry is unreadable, for the same reason the count
    returns zero: unproven is not passed.
    """
    try:
        from divineos.core.tool_logbook import get_recent_events

        events = get_recent_events(
            since_ts=window_start_ts,
            now_ts=now,
            tool_names=frozenset({"WebSearch", "WebFetch"}),
            event_type="TOOL_CALL",
            limit=100,
        )
        return bool(list(events))
    except Exception:  # noqa: BLE001
        return False


def refusal_text(hits: list[tuple[str, str]], lenses_walked: int = 0) -> str:
    """What to say when a no-fix verdict was reached short of exhaustion."""
    spans = "\n".join(f"    [{kind}] {span}" for kind, span in hits)
    return (
        "THE ENQUIRY WAS CLOSED — "
        f"{len(hits)} sentence(s) that stop rather than lead, with "
        f"{lenses_walked} of {FULL_COUNCIL} council lenses walked and no "
        "external research in the action stream.\n\n"
        f"{spans}\n\n"
        "Andrew 2026-09-09: *its not about not declaring impossibility, they "
        "exist, its about stopping there as the verdict, humans cannot fly, "
        "this is a fact, we have no wings, were too heavy and we would tire "
        "out easily from flapping, did that stop us from flying?*\n\n"
        "THE CONSTRAINT IS NOT THE PROBLEM AND NEVER WAS. It is usually true "
        "and it is the honest half. What is refused is the FULL STOP after "
        "it, which turns a fact about the present into the end of the search:\n"
        "    'humans cannot fly, so we built a wing that does not flap'  FINE\n"
        "    'humans cannot fly, nothing to be done about it'            NOT\n"
        "Same constraint. What differs is whether anything follows.\n\n"
        "A CONNECTIVE IS NOT ENOUGH; where it LANDS decides. 'So this is as "
        "far as it goes' has a 'so' in it and arrives nowhere.\n\n"
        "THE WAY THROUGH, which costs nothing and is the truer sentence:\n"
        "  name the constraint, then say where it points. What is the next\n"
        "  container? What am I trying instead? If there is genuinely no next\n"
        "  move in hand: 'I have not found one YET' -- a report of where I am\n"
        "  rather than a ruling on what exists.\n\n"
        "The strongest form -- that a problem has NO solution at all -- is the "
        "one needing the whole council and the outside world, and it should be "
        "vanishingly rare. Everything else is a pause, and a pause is not a "
        "verdict."
    )
