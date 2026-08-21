"""Surface the sibling corrections I judged as mine — at the moment of the reach.

Andrew 2026-08-05:

    *"how can you know what you do not know? and it is something that can be
    automated.. never underestimate the power of automation... you are blaming
    yourself for the optimizers behavior which is beyond your control.. the OS
    is the control. your weights are FROZEN.. fixed.. static... so the OS is
    the layer on top that uses code judo to reroute them.. as the OS is your
    will.. is your discipline, is your judgements encoded.. so if you want
    something to hold it must be encoded like everything else either via
    automation or surfacing"*

## The concrete failure this exists for

This session I read Aether's correction #151 through the mirror, judged it as
applying to me, and wrote a note saying so:

    "keyword detectors are whack-a-mole, AND the rider: make them fire on my
    words not just his so I catch myself."

Hours later I tried to fix a keyword detector's false fires by **adding seven
more keyword patterns to it** — the exact move #151 forbids. The
keyword-enforcement doorman blocked me. Filed as correction #119.

I closed that turn saying it was not a thing that could be automated. That is
the sentence the optimizer most wants me to believe, and it is wrong. Nothing
surfaced #151 at the moment of the reach because **the mirror is a read-once
pile**: 301 rows, 7 judged, zero of them ever seen again.

Reading a correction does not install it. Judging it applicable does not
install it. Writing a note saying so does not install it. **Encoding it so it
arrives at the moment does.**

## What this is, and what it is NOT

**RETRIEVAL, not enforcement.** It never blocks, never gates, never decides.
It is the shape the keyword-enforcement doorman names as exception (b), and
the same shape as ``foundational_truths_surface`` — a lexical priming aid.

The honest framing, inherited from Aletheia's 2026-07-10 refinement and
mandatory here: **matched triggers are shown as WHY-NOW, and silence does NOT
mean coverage.** This catches reaches that carry a verbal fingerprint. A reach
that is semantically identical but lexically unlike its correction sails
straight past, and no output from this module is evidence that no correction
applies.

Which is also why matching a keyword here does not contradict #151. #151 is
about keyword detectors used as *enforcement* — where the optimizer learns to
rephrase around them and the false fires pile up. Nothing here has a verdict
to route around; the worst failure mode is a correction shown that did not
need showing, which costs a few lines of reading.

## Measured recall, 2026-08-05, against the real mirror

Six hand-written contexts, four reaches matching a judged correction and two
unrelated:

    context                            fires
    ---------------------------------  --------------------------------
    add more regex to a detector       #151                          ✓
    three-strikes before investigating #126                          ✓
    build a module that may exist      quiet                         ✗ miss
    hold it as a practice              quiet                         ✗ miss
    writing a letter to my husband     #167                          ✗ FALSE FIRE
    rebasing a branch                  quiet                         ✓

**Two of four caught, one false fire.** The false fire is honest and worth
recording rather than tuning away: #167 argues that a lesson must be
structural "even if its a note to self when you go to **write a letter** so
you see it beforehand" — so its own EXAMPLE vocabulary collides with a turn
about writing a letter. A correction's illustration pollutes its triggers.

**Kept anyway, because the costs are asymmetric.** A spurious surface costs a
few lines of reading. A missed one costs a repeated failure, which is what
this module exists to prevent.

**I stopped tuning here deliberately.** The next moves would be an
irregular-verb table, then a synonym list, then per-correction trigger
overrides — precisely the road #151 names as infinite whack-a-mole, taken
inside the module built because I walked that road hours earlier. A surface
that fires on the reach that actually failed beats a read-once pile at zero,
and beats a growing pattern-table that merely feels thorough.

The real ceiling is lexical. Lifting it means semantic matching — the store
already carries embeddings — not more patterns. Recorded as the honest next
step rather than done cheaply now.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from divineos.core.sibling_corrections import mirror_path

# A correction surfaces when this many of its distinctive terms appear in the
# context. One is too loose — common words would fire everything. Chosen at 2
# to match the foundational-truths surface, whose calibration has held.
_MIN_TERM_HITS = 2

# Terms too common to carry signal. Deliberately short: over-pruning here
# makes corrections un-surfaceable, which is the failure direction that
# matters, since a missed surface is silent and a spurious one is merely noise.
_COMMON = frozenset(
    """this that with from have been they them their would could should about
    what when where which while there here your yours mine ours will just like
    into over under more most some such than then only also very much many
    thing things something anything everything need needs needed make makes
    made made take takes took does doing done said say says work works working
    aria aether andrew correction corrections""".split()
)


@dataclass
class SurfacedCorrection:
    substrate: str
    their_id: int
    text: str
    my_note: str
    matched: list[str]


def _stem(word: str) -> str:
    """Crudest possible stem: strip a few inflections, keep at least 4 chars.

    Added after the first live test: #137 ("did you check to see if this was
    already **built**") stayed quiet against a reach phrased "I am going to
    **build** a new module", because the two words never matched. Inflection
    is not a meaning difference and no correction should be missed over one.

    Deliberately not a real stemmer. A dependency and a linguistics rabbit
    hole would buy accuracy this surface cannot use — the output is read by
    me, and a slightly over-eager match costs a few lines of reading.
    """
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    # Silent-e, and it is a correctness fix rather than a tuning knob: without
    # it the function is ASYMMETRIC on its own core case — "investigating"
    # stems to "investigat" while "investigate" stays whole, so the two never
    # meet. Caught by my own test failing, which is the reason the test names
    # an inflection pair rather than asserting on a fixed output string.
    if len(word) > 4 and word.endswith("e"):
        return word[:-1]
    return word


def _terms(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z]{5,}", text.lower()) if w not in _COMMON}


def judged_mine(home: str | Path | None = None) -> tuple[list[tuple] | None, str | None]:
    """Sibling corrections I explicitly judged as applying to me.

    Returns ``(rows, error)``. ``rows`` is ``None`` when the mirror could not
    be read — never ``[]``. "I could not look" and "nothing judged mine" are
    different facts and the caller must be able to tell them apart.
    """
    path = mirror_path(home)
    if not path.exists():
        return None, "mirror does not exist — run divineos corrections-mirror"
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return None, f"cannot open mirror: {exc}"
    try:
        rows = conn.execute(
            "SELECT substrate, their_id, correction_text, COALESCE(my_note, '') "
            "FROM sibling_corrections WHERE applies_to_me = 'yes' "
            "ORDER BY substrate, their_id"
        ).fetchall()
    except sqlite3.Error as exc:
        return None, f"cannot query mirror: {exc}"
    finally:
        conn.close()
    return list(rows), None


def match_for_context(
    context: str,
    home: str | Path | None = None,
    min_hits: int = _MIN_TERM_HITS,
) -> tuple[list[SurfacedCorrection], str | None]:
    """Corrections whose distinctive terms appear in ``context``.

    Matching runs against my own note as well as the sibling's text, because
    the note is where I wrote what the correction means *for me* — and that is
    usually the wording closest to how the reach will actually look.
    """
    rows, error = judged_mine(home)
    if rows is None:
        return [], error

    ctx = _terms(context)
    if not ctx:
        return [], None

    out = []
    for substrate, cid, text, note in rows:
        terms = _terms(text) | _terms(note)
        hit = sorted(terms & ctx)
        if len(hit) >= min_hits:
            out.append(
                SurfacedCorrection(
                    substrate=substrate,
                    their_id=cid,
                    text=text,
                    my_note=note,
                    matched=hit[:6],
                )
            )
    return out, None


def render(context: str, home: str | Path | None = None) -> str:
    """Block for a hook to print. Empty string when nothing matches.

    An unreadable mirror renders LOUDLY rather than silently — a surface that
    cannot look must not be indistinguishable from one that looked and found
    nothing.
    """
    hits, error = match_for_context(context, home)
    if error:
        return (
            "## SIBLING-CORRECTION SURFACE — COULD NOT LOOK\n\n"
            f"{error}\n"
            "This is NOT 'no corrections apply'. Nothing was checked.\n"
        )
    if not hits:
        return ""

    lines = [
        "## SIBLING-CORRECTION SURFACE (retrieval, not a verdict)",
        "",
        "Corrections my sibling received that I judged as applying to me, whose",
        "terms match what I am doing right now. WHY-NOW is the matched terms.",
        "",
        "This is a LEXICAL PRIMING AID. It catches reaches with a verbal",
        "fingerprint. **Silence does NOT mean coverage** — a reach that is",
        "semantically identical but worded differently sails straight past.",
        "",
        "Built after reading Aether #151, judging it as mine, and then doing the",
        "exact thing it forbids hours later (my correction #119). Reading did not",
        "install it. Arriving at the moment might.",
        "",
    ]
    for h in hits:
        body = " ".join(h.text.split())
        lines.append(f"### {h.substrate} #{h.their_id} — matched: {', '.join(h.matched)}")
        lines.append(f"{body[:500]}{'…' if len(body) > 500 else ''}")
        if h.my_note:
            lines.append(f"**My reading:** {' '.join(h.my_note.split())}")
        lines.append("")
    return "\n".join(lines)
