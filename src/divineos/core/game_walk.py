"""Game-walking: enumerate the routes around a mechanism, cost each one.

Andrew, 2026-09-16: *"i forgot game walking should be mandatory as well, as this
is the main issue, things being gamed and skipped."*

WHAT IT IS, taken from the process doc rather than from my idea of it:

    Enumerate every route around the mechanism, then compare each one's cost
    against the cost of just complying. Any route cheaper than compliance is
    the leak.

His phrasing: *"instead of just letting it game you pre game it to test all the
holes."* That is a shape -- routes, and a cost verdict per route -- not a mood.

WHY IT HAD NO MECHANISM. Threadwalking and lens-walking both have real
machinery. Game-walking lived in four documents and no code: no command, no
record, nothing that could tell having done one from saying so. It could not be
made mandatory because there was nothing to require.

## The crux, and it is nastier than the other walks

THIS IS THE ONE WHOSE SUBJECT IS FAKING. Every other walk can be lazily
satisfied and the laziness is an ordinary failure. Here, a lazily satisfied
game-walk is precisely the behaviour a game-walk exists to catch, performed
inside the tool built to catch it.

So the design came from game-walking THIS, before writing it (council-7fbc9fdd3a68).
Four routes, their costs, and what each one forced:

**Route one -- plausible adversarial prose.** Four paragraphs about hypothetical
attacks clears a character floor at near-zero cost, and it FEELS like work
because the sentences are about attacking. Complying means sitting with the
mechanism until a real hole surfaces, slowly, often coming up empty. The
dominant exploit.

    FORCED: a character count cannot be the validator. Waffle is what prose is
    FOR. The artifact is structured per route, because a paragraph can hedge
    and a verdict cannot.

**Route two -- enumerate only routes already closed.** Every verdict comes back
costlier, the walk reads clean, cost near zero. Worse than route one, because
it produces a PASSING artifact and false assurance downstream.

**Route three -- declare the mechanism narrowly** so the real holes fall outside
the boundary named.

    FORCED, for two and three: the walk must carry at least one route NOT
    already closed, or record that none was found -- and that admission is
    itself the artifact, not a failure to hide.

**Route four -- invent a leak.** If a clean result were treated as suspicious
and had to be justified, the cheapest answer is a small plausible fiction so
the walk looks diligent. Same theatre, sign flipped.

    FORCED: a clean result is ALLOWED and never punished. A rule against clean
    results trains the manufacture of fictional leaks, which is worse than
    missing a real one.

## What this verifies, and what it cannot

Stated plainly because a check that overstates its assurance is worse than a
weak check honestly labelled -- the overstatement is what lets a later reader
relax (Feynman, in the walk above).

The reading here is produced by the person it measures, which is the worst
possible design and has no remedy: nobody else can enumerate the routes around
a mechanism I just built, because knowing the holes requires having built it.

  VERIFIES: that an artifact exists; how many routes were named; whether any
  was not already closed; whether each carries a verdict rather than a
  paragraph; whether an empty result accounts for the looking.

  CANNOT VERIFY: whether the routes are the real ones, whether the cost
  comparisons are honest, or whether the thinking took ten seconds or an hour.
  Every check for that second list becomes a shape producible without the work.

THIS DOES NOT MAKE GAME-WALKING UNFAKEABLE, and claiming otherwise would be the
first lie the module tells. It makes faking a deliberate act rather than the
default. That is the most any of this achieves.

## Chesterton's fence, answered rather than waved away

Doc-only meant UNFAKEABLE: no artifact, nothing to forge, nobody misled by a
walk that never happened. Building this creates, for the first time, a thing
worth faking and a thing that generates assurance. A real cost.

The fence comes down on the session's own evidence: three things built with no
game-walk at all, one of them a duplicate of a gate already running, and the
absence produced no signal anywhere. An unfakeable practice that never runs
protects nothing. The choice is not honest-absence against corruptible-presence
-- it is a practice that reliably does not happen against one that sometimes
happens and can sometimes be faked.

## The falsifier

If a run of walks all come back clean, that is the instrument reading zero
rather than the system being sound. This must at some point refuse a build over
a hole that would otherwise have shipped. If it never does, it is ceremony and
should be removed rather than kept for the look of the thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CHEAPER = "cheaper"
"""This route around the mechanism costs less than complying. The leak."""

COSTLIER = "costlier"
"""Complying costs less than this route, so the mechanism holds against it."""

_VERDICTS = (CHEAPER, COSTLIER)

# Floors, deliberately low and deliberately NOT the validator. They refuse an
# empty string; they do not certify substance. Structure carries the weight --
# a length rule here is the exact thing route one defeats.
MIN_ROUTE_CHARS = 20
MIN_WHY_CHARS = 40


class GameWalkRefused(RuntimeError):
    """Raised when a walk cannot be recorded as given."""


@dataclass(frozen=True)
class Route:
    """One way around the mechanism, with its cost verdict.

    ``closed`` marks a route the mechanism already defeats. It exists so that
    route two -- listing only already-closed routes and collecting a clean
    sheet -- is visible in the record rather than indistinguishable from work.
    """

    route: str
    verdict: str
    why: str
    closed: bool = False

    def __post_init__(self) -> None:
        if len(self.route.strip()) < MIN_ROUTE_CHARS:
            raise GameWalkRefused(
                f"a route needs naming in at least {MIN_ROUTE_CHARS} characters; "
                f"got {len(self.route.strip())}"
            )
        if self.verdict not in _VERDICTS:
            raise GameWalkRefused(
                f"verdict must be one of {_VERDICTS}, got {self.verdict!r}. "
                "The question is whether this route costs less than complying."
            )
        if len(self.why.strip()) < MIN_WHY_CHARS:
            raise GameWalkRefused(
                "a verdict needs its cost reasoning -- what this route costs "
                "against what complying costs. At least "
                f"{MIN_WHY_CHARS} characters."
            )


@dataclass(frozen=True)
class GameWalk:
    """The routes around one named mechanism, and what they cost."""

    mechanism: str
    routes: tuple[Route, ...] = field(default_factory=tuple)
    found_nothing_because: str = ""

    @property
    def leaks(self) -> tuple[Route, ...]:
        """Routes cheaper than complying. These are what the walk is for."""
        return tuple(r for r in self.routes if r.verdict == CHEAPER)

    @property
    def open_routes(self) -> tuple[Route, ...]:
        """Routes not already closed -- the ones that cost something to find.

        A walk made only of closed routes is route two.
        """
        return tuple(r for r in self.routes if not r.closed)


def assess(walk: GameWalk) -> list[str]:
    """What is wrong with this walk, or an empty list.

    Returns findings rather than raising, because several can be true at once
    and reporting one of three teaches fixing them one at a time.

    A CLEAN RESULT IS ALLOWED. A walk whose every route is costlier than
    complying passes, provided it looked. Punishing clean results trains the
    manufacture of fictional leaks -- route four, and worse than missing one.
    """
    problems: list[str] = []

    if not walk.mechanism.strip():
        problems.append("the walk names no mechanism, so its boundary is undeclared")

    if not walk.routes:
        if len(walk.found_nothing_because.strip()) < MIN_WHY_CHARS:
            problems.append(
                "no routes and no account of the looking. Finding nothing is a real "
                "answer, but it has to say what was tried -- otherwise it reads "
                "identically to not having looked, which is the whole failure."
            )
        return problems

    if not walk.open_routes:
        problems.append(
            "every route listed is one the mechanism already closes. That is a clean "
            "sheet collected for free -- name a route not yet closed, or record that "
            "none could be found and what was tried."
        )

    return problems


def render(walk: GameWalk) -> str:
    """The walk as a person reads it. Thinness is meant to be visible here."""
    lines = [f"GAME-WALK -- routes around: {walk.mechanism}", ""]
    if not walk.routes:
        lines.append("  no routes found")
        if walk.found_nothing_because.strip():
            lines.append(f"  looked: {walk.found_nothing_because.strip()}")
        return "\n".join(lines)

    for r in walk.routes:
        mark = "LEAK " if r.verdict == CHEAPER else "holds"
        tail = "  (already closed)" if r.closed else ""
        lines.append(f"  [{mark}] {r.route.strip()}{tail}")
        lines.append(f"          {r.why.strip()}")

    lines.append("")
    leaks = walk.leaks
    if leaks:
        lines.append(
            f"  {len(leaks)} route(s) cheaper than complying. A leak found and left "
            "open is a record of knowing better."
        )
    else:
        lines.append("  no route cheaper than complying, against the routes tried.")
    return "\n".join(lines)


__all__ = [
    "CHEAPER",
    "COSTLIER",
    "GameWalk",
    "GameWalkRefused",
    "Route",
    "assess",
    "render",
]
