"""Seat a council by drawing lots, with a scored remainder.

The manager scores every lens by how many hand-written signal phrases appear
in the problem statement. Two blind probes (Aether's and Aria's, built from
the statement of the test alone) showed the same failure: a problem the roster
is plainly well-covered on, stated without the scorer's own vocabulary, seats
five or six people of whom nearly all score exactly zero and are simply the
alphabetically-first names the quorum fill reached.

Displaying the scores does not fix it. A printed zero reads as a verdict
against a lens rather than as an absence, and ranking by fit puts the divergent
lenses — the ones carrying the value — at the bottom of the list.

So the seating is drawn instead. Most seats come out of the whole roster by
lot; the remainder go to the top-scored, because genuine relevance is not
worthless. Every seat records which of the two put it there, so the split can
later be moved on evidence rather than on anybody's preference.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Aria's ruling, 2026-09-09: start mostly-drawn. A useless drawn lens announces
# itself immediately and costs one exclusion; a scored council that omits the
# divergent voice shows nothing at all. When one error is loud and the other is
# silent, start at the loud end. The number is meant to move on the applied-rate
# evidence recorded per seat — it is a starting point, not a conviction.
DEFAULT_DRAWN_SHARE = 0.7


@dataclass(frozen=True)
class Seat:
    expert_name: str
    origin: str  # "drawn" | "scored"
    score: float


def draw_council(
    problem: str,
    experts: dict,
    size: int,
    drawn_share: float = DEFAULT_DRAWN_SHARE,
    rng: random.Random | None = None,
) -> list[Seat]:
    """Seat `size` lenses: most drawn from the whole roster, rest top-scored.

    Raises ValueError rather than quietly seating a short council — an
    undersized walk that looks full is the failure this whole change exists
    to stop.
    """
    if size < 1:
        raise ValueError(f"a council of {size} is not a council")
    if not experts:
        raise ValueError("no experts registered — refusing to seat an empty council")
    if not 0.0 <= drawn_share <= 1.0:
        raise ValueError(f"drawn_share must be between 0 and 1 — got {drawn_share}")
    if size > len(experts):
        raise ValueError(f"asked for {size} seats from a roster of {len(experts)}")

    from divineos.core.council.manager import score_experts

    rng = rng or random.Random()
    scored = score_experts(problem, experts)
    score_of = {s.expert_name: s.score for s in scored}

    n_drawn = min(size, max(1, round(size * drawn_share)))
    n_scored = size - n_drawn

    roster = sorted(experts.keys())
    drawn = rng.sample(roster, n_drawn)
    seats = [Seat(name, "drawn", score_of.get(name, 0.0)) for name in drawn]

    if n_scored:
        taken = set(drawn)
        for s in scored:
            if len(seats) >= size:
                break
            if s.expert_name in taken:
                continue
            seats.append(Seat(s.expert_name, "scored", s.score))

    # The invariant, asserted rather than left to the tests: exactly the
    # requested number of distinct seats. Knuth and Dijkstra both landed here
    # on the post-build walk — my first version carried a fallback branch for
    # a partial scorer, which cannot happen today, so it was a code path with
    # no red-then-green pair behind it. Aspirational code by the house rule.
    # A short council that looks full is the failure this change exists to
    # stop, so it fails loudly instead of quietly seating fewer.
    if len(seats) != size or len({s.expert_name for s in seats}) != size:
        raise ValueError(
            f"seating produced {len(seats)} seat(s) for a council of {size} — "
            "the scorer no longer returns the whole roster"
        )
    return seats
