"""A council walk that cannot be closed while a lens is unaccounted for.

Andrew 2026-08-10: "you have all the means and setup not to fake it.. but you
keep doing it.. so unless you build enforcement which i have asked repeatedly
to be done.. you will continue to fake it, rendering the system pointless."

He is right, and the design was already written — by me — in
.claude/skills/council-round/SKILL.md on 2026-07-25:

    "the fix is structural gate-enforcement at the mechanism layer. The
     target-shape: council walk cannot complete synthesis until every
     surfaced lens has either (a) a COUNCIL_LENS_APPLIED event on ledger,
     OR (b) a structured COUNCIL_LENS_EXCLUDED event with an exclusion-
     reason that passes substance-check. Until that gate is built and
     shipped, the discipline lives in this file and depends on composer
     discipline — which is exactly the wrong-shape."

Sixteen days sat between writing that and building it, and in that gap I
skipped the walk entirely, then ran one piped through `tail -60` so a
truncation flag picked my council instead of the manager.

THE ONE LOAD-BEARING DECISION:

The lens set is taken from `select_experts()` at open time — the manager's
own selection — and NEVER from an argument I supply. If the caller could
name the lenses, the composer picks the low end every time (Andrew's
Goodhart note, 2026-06-23) and the whole mechanism becomes a form I fill in.
I do not get to choose my council. That is the entire point.

Closing refuses while any surfaced lens is still OPEN. Exclusions are
allowed — silent narrowing is not — and an exclusion must carry a reason
with substance, because "not relevant" is the shortcut this exists to stop.

Append-only: state transitions insert rows; nothing is rewritten.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any

from divineos.core.paths import divineos_home

MIN_FINDING_CHARS = 40
MIN_EXCLUSION_CHARS = 60  # deliberately higher: excluding is the cheap move


class WalkRefused(RuntimeError):
    """A refusal is the mechanism working, not an error to route around."""


def _db_path() -> Path:
    p = divineos_home() / "council_walks.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS walks (
            id TEXT PRIMARY KEY,
            problem TEXT NOT NULL,
            opened_at REAL NOT NULL,
            closed_at REAL,
            consumed_at REAL
        );
        CREATE TABLE IF NOT EXISTS walk_lenses (
            walk_id TEXT NOT NULL,
            lens TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'OPEN',
            content TEXT,
            settled_at REAL,
            origin TEXT NOT NULL DEFAULT 'scored',
            PRIMARY KEY (walk_id, lens)
        );
        """
    )
    # Migration for walks created before consumed_at existed (this one
    # shipped mid-session). SQLite raises if the column is already there;
    # a second run no-ops.
    try:
        conn.execute("ALTER TABLE walks ADD COLUMN consumed_at REAL")
    except sqlite3.OperationalError:
        pass
    # Seat provenance, added when seating moved from fit-scoring to a draw.
    # Rows written before it default to 'scored', which is what they were.
    try:
        conn.execute("ALTER TABLE walk_lenses ADD COLUMN origin TEXT NOT NULL DEFAULT 'scored'")
    except sqlite3.OperationalError:
        pass
    # What this seat changed in the artifact, written as the change is made.
    # NULL means no change credited, which on an older row means the question
    # was never asked rather than that the answer was no.
    try:
        conn.execute("ALTER TABLE walk_lenses ADD COLUMN changed_artifact TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


# Andrew's stated standard, recovered from the knowledge store rather than
# invented here: "the council walk needs a minimum of 5 lenses. preferrably
# more. 9, 12, 15 lenses with at least 2-3 disagreeing ones depending on the
# gravity of the fix." The ladder is his; the mapping to names is mine.
#
# NOT auto-derived from the gravity classifier: that scores FILE CHANGES,
# and a walk opens before any file exists. Wiring it would be a coupling
# that looks automatic and is wrong. The tier is named at open time and
# recorded, so a walk opened at the low tier is visible as such.
GRAVITY_FLOORS: dict[str, int] = {"normal": 5, "high": 9, "severe": 12, "critical": 15}


def _surface_seats(problem: str, floor: int = 5, rng: Any = None) -> list[Any]:
    """Seat the council: most drawn by lot, the remainder by score.

    This was the manager's fit-scoring alone until 2026-09-09, when two blind
    probes — Aether's and Aria's, built from the statement of the test and
    nothing else — showed the same thing. A problem the roster is plainly
    well-covered on, stated without the scorer's own vocabulary, seats five or
    six lenses of whom nearly all score exactly zero and are simply the
    alphabetically-first names the quorum fill reached. The bench looks like a
    council either way.

    Displaying the scores does not fix it: a printed zero reads as a verdict
    against a lens, and ranking by fit puts the divergent lenses last, which is
    where the value was. So the wording is taken out of the seating.
    """
    # get_council_engine(), NOT CouncilEngine(). A bare engine has an EMPTY
    # expert dict — experts are registered by _register_all_experts, which
    # only the singleton accessor calls. My first draft constructed a bare
    # one and surfaced ZERO lenses, silently: scoring an empty dict returns
    # [] rather than raising. A walk built on that would have opened with no
    # council at all and looked fine.
    from divineos.core.council.draw import draw_council
    from divineos.core.council.engine import get_council_engine

    experts = get_council_engine().experts
    if not experts:
        raise WalkRefused("the council engine registered no experts — refusing to guess a council")
    size = min(max(floor, 8), len(experts))
    return draw_council(problem, experts, size=size, rng=rng)


def open_walk(problem: str, gravity: str = "normal") -> dict[str, Any]:
    problem = (problem or "").strip()
    if len(problem) < 20:
        raise WalkRefused("state the problem in a sentence — a label is not a problem")
    gravity = (gravity or "normal").strip().lower()
    if gravity not in GRAVITY_FLOORS:
        raise WalkRefused(f"gravity must be one of {', '.join(GRAVITY_FLOORS)} — got {gravity!r}")

    floor = GRAVITY_FLOORS[gravity]
    seats = _surface_seats(problem, floor=floor)
    if not seats:
        raise WalkRefused("the seating produced no lenses; refusing to open an empty walk")
    if len(seats) < floor:
        raise WalkRefused(
            f"{gravity} gravity requires at least {floor} lenses; the seating produced "
            f"{len(seats)}. Refusing rather than opening an undersized walk."
        )
    lenses = [seat.expert_name for seat in seats]

    walk_id = "walk-" + hashlib.sha256(f"{problem}{time.time()}".encode()).hexdigest()[:12]
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO walks (id, problem, opened_at) VALUES (?, ?, ?)",
            (walk_id, problem, time.time()),
        )
        conn.executemany(
            "INSERT INTO walk_lenses (walk_id, lens, origin) VALUES (?, ?, ?)",
            [(walk_id, seat.expert_name, seat.origin) for seat in seats],
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "walk_id": walk_id,
        "lenses": lenses,
        "seats": [{"lens": s.expert_name, "origin": s.origin, "score": s.score} for s in seats],
    }


def _settle(walk_id: str, lens: str, state: str, content: str, minimum: int) -> None:
    content = (content or "").strip()
    if len(content) < minimum:
        raise WalkRefused(
            f"{state.lower()} needs at least {minimum} characters of substance; got {len(content)}"
        )
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT state FROM walk_lenses WHERE walk_id = ? AND lens = ?", (walk_id, lens)
        ).fetchone()
        if row is None:
            known = [
                r[0]
                for r in conn.execute(
                    "SELECT lens FROM walk_lenses WHERE walk_id = ?", (walk_id,)
                ).fetchall()
            ]
            if not known:
                raise WalkRefused(f"no such walk: {walk_id}")
            raise WalkRefused(
                f"{lens!r} is not on this walk. The manager surfaced: {', '.join(known)}"
            )
        if row[0] != "OPEN":
            raise WalkRefused(f"{lens} is already {row[0]}; walks are append-only")
        conn.execute(
            "UPDATE walk_lenses SET state = ?, content = ?, settled_at = ? "
            "WHERE walk_id = ? AND lens = ?",
            (state, content, time.time(), walk_id, lens),
        )
        conn.commit()
    finally:
        conn.close()


MIN_ADDITION_CHARS = MIN_EXCLUSION_CHARS


def add_lens(walk_id: str, lens: str, why: str) -> None:
    """Add a lens the manager did not surface, WITH a recorded reason.

    Andrew 2026-08-14: "the council manager should not have been able to
    refuse the lens, the lenses that surface should be used but adding lenses
    or swapping them should be allowed with reasoning, its there to prevent
    gaming as if it wasnt you would choose 3-4 lenses every time and it would
    be the same lenses lol."

    He is exactly right about what the refusal was for and exactly right that
    it overshot. The property worth keeping is that I cannot PICK my council —
    every surfaced lens still needs a finding or a written exclusion, so the
    four-favourites walk remains impossible. The property that was wrong is
    treating the manager's list as closed, which made the council unarguable
    and blocked him when he named Feynman by hand on walk-6b5285dce17c.

    Addition is ADDITIVE, never substitutive: adding does not discharge any
    surfaced lens. A swap is therefore already expressible as an exclusion
    with a reason plus an addition with a reason, both recorded, which is the
    correct price for changing the shape of my own council.

    The reason is the cost. Andrew's cost-landscape principle applied to the
    one place in the walk where I choose: make the addition possible so it is
    not a wall, and make it cost a written justification so it is not free.
    """
    lens = lens.strip()
    if not lens:
        raise WalkRefused("a lens needs a name")
    why = (why or "").strip()
    if len(why) < MIN_ADDITION_CHARS:
        raise WalkRefused(
            f"adding {lens!r} needs a reason of at least {MIN_ADDITION_CHARS} "
            "characters. Why this lens, on this problem, that the surfaced ones "
            "do not already cover? A free addition is a picked council."
        )
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM walk_lenses WHERE walk_id = ? AND lens = ?", (walk_id, lens)
        ).fetchone()
        if row is not None:
            raise WalkRefused(f"{lens} is already on this walk")
        if not conn.execute("SELECT 1 FROM walk_lenses WHERE walk_id = ?", (walk_id,)).fetchone():
            raise WalkRefused(f"no such walk: {walk_id}")
        conn.execute(
            "INSERT INTO walk_lenses (walk_id, lens, state, content, settled_at, origin) "
            "VALUES (?, ?, 'OPEN', ?, NULL, 'added')",
            (walk_id, lens, f"ADDED: {why}"),
        )
        conn.commit()
    finally:
        conn.close()


def apply_lens(walk_id: str, lens: str, finding: str) -> None:
    """Record what this lens actually produced when walked."""
    _settle(walk_id, lens, "APPLIED", finding, MIN_FINDING_CHARS)


def exclude_lens(walk_id: str, lens: str, reason: str) -> None:
    """Exclude a lens WITH a reason. Silent narrowing is what this stops."""
    _settle(walk_id, lens, "EXCLUDED", reason, MIN_EXCLUSION_CHARS)


MIN_CHANGE_CHARS = 30


def credit_seat(walk_id: str, lens: str, what_changed: str) -> None:
    """Record that this lens changed the thing being built, as it changes.

    Aria 2026-09-09, taking apart the measure I had just shipped: divergence
    compares a seat's finding against the other findings on the same walk, and
    I wrote all of them — so it measures how far one of my paragraphs sits from
    my other paragraphs, which is a fact about my prose variety and not about
    the lens. A seat I happened to phrase in a different register reads as
    divergent; one that genuinely broke the frame but came out in the same
    voice reads as conformist. And it moves if I vary my wording, with no
    intent to game it at all.

    Her replacement was already in my own hands: *four of those findings
    changed the commit before it was made.* That is what divergence was
    standing in for, it is binary, and it is about the artifact rather than
    about the text. Distance-from-the-others was chosen because it was
    computable; changed-the-artifact is the thing itself.

    REFUSED ON A CLOSED WALK, and that is the whole discipline rather than a
    convenience. Her caution: credit recorded after the fact is a receipt
    written once the outcome is known, which is the anchoring class arriving
    inside the fix for it. Closing the walk closes the window.
    """
    what_changed = (what_changed or "").strip()
    if len(what_changed) < MIN_CHANGE_CHARS:
        raise WalkRefused(
            f"name what changed, in at least {MIN_CHANGE_CHARS} characters. "
            "'it helped' is not an artifact."
        )
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT w.closed_at FROM walks w JOIN walk_lenses l ON l.walk_id = w.id "
            "WHERE w.id = ? AND l.lens = ?",
            (walk_id, lens),
        ).fetchone()
        if row is None:
            raise WalkRefused(f"{lens!r} is not on walk {walk_id}")
        if row[0] is not None:
            raise WalkRefused(
                f"{walk_id} is closed. Credit is recorded as the change is made, never "
                "after — a receipt written once the outcome is known is the anchoring "
                "shape this whole line of work is about."
            )
        conn.execute(
            "UPDATE walk_lenses SET changed_artifact = ? WHERE walk_id = ? AND lens = ?",
            (what_changed, walk_id, lens),
        )
        conn.commit()
    finally:
        conn.close()


def exclusion_tally(limit: int = 15) -> list[dict[str, Any]]:
    """How often each lens has been excluded, across all walks.

    Aria's guard, and she moved the target to get here. I had flagged the
    hand-add path as the override I kept for myself; she refused that reading.
    A hand-add can only WIDEN the council, costs a written reason, and is what
    put four of the fourteen lenses on the walk that found the defect at all.

    The narrowing door is this one. Draw nine, exclude the three that feel
    useless, and fit-selection is back by hand with a paper trail that reads as
    diligence. No single exclusion looks like that; a tally does. If one name
    keeps being excluded it is either a genuinely useless lens — a finding
    about the roster — or a voice I keep declining to hear, which is a finding
    about me. Neither is visible one exclusion at a time.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT lens, COUNT(*) AS n FROM walk_lenses WHERE state = 'EXCLUDED' "
            "GROUP BY lens ORDER BY n DESC, lens ASC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [{"lens": lens, "exclusions": n} for lens, n in rows]


def status(walk_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        walk = conn.execute(
            "SELECT problem, opened_at, closed_at, consumed_at FROM walks WHERE id = ?",
            (walk_id,),
        ).fetchone()
        if walk is None:
            raise WalkRefused(f"no such walk: {walk_id}")
        rows = conn.execute(
            "SELECT lens, state, content FROM walk_lenses WHERE walk_id = ? ORDER BY lens",
            (walk_id,),
        ).fetchall()
    finally:
        conn.close()

    lenses: list[dict[str, Any]] = [{"lens": r[0], "state": r[1], "content": r[2]} for r in rows]
    return {
        "walk_id": walk_id,
        "problem": walk[0],
        "closed": walk[2] is not None,
        "consumed": walk[3] is not None,
        "lenses": lenses,
        "open_lenses": [row["lens"] for row in lenses if row["state"] == "OPEN"],
    }


def close_walk(walk_id: str) -> dict[str, Any]:
    """Refuse while any surfaced lens is unaccounted for."""
    st = status(walk_id)
    if st["closed"]:
        raise WalkRefused(f"{walk_id} is already closed")
    outstanding = st["open_lenses"]
    if outstanding:
        raise WalkRefused(
            f"{len(outstanding)} lens(es) unaccounted for: {', '.join(outstanding)}. "
            "Apply each one or exclude it with a reason. This refusal is the mechanism."
        )
    conn = _conn()
    try:
        conn.execute("UPDATE walks SET closed_at = ? WHERE id = ?", (time.time(), walk_id))
        conn.commit()
    finally:
        conn.close()
    return status(walk_id)


def is_complete(walk_id: str) -> bool:
    """Closed AND not already spent on an earlier commit.

    The anti-fake clause, in two halves. Citing a walk whose lenses were
    never applied has to fail, or the gate only forces me to START a walk
    I can still fake.

    The second half came from the walk itself — the Schneier lens, on
    walk-32d831616266, which I did not choose and which found that a
    completed walk could be cited FOREVER, on every future commit, about
    unrelated code. One walk today and never again: a total bypass with no
    bypass flag, hiding inside the mechanism advertised as unbypassable.
    """
    try:
        st = status(walk_id)
    except WalkRefused:
        return False
    return bool(st["closed"]) and not st["consumed"]


def consume(walk_id: str) -> None:
    """Spend a walk on one commit. A second commit citing it fails."""
    conn = _conn()
    try:
        conn.execute(
            "UPDATE walks SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL",
            (time.time(), walk_id),
        )
        conn.commit()
    finally:
        conn.close()


def open_walks(limit: int = 5) -> list[dict[str, Any]]:
    """Walks left hanging. THE CONSUMER — and the reason it exists.

    The Peirce lens on walk-32d831616266 found that nothing read this
    database: findings went in and sat, which is the unwired-intention shape
    reproduced inside the mechanism built to stop me reproducing it.

    An OPEN walk is unfinished thinking, so this is what deserves a reader.
    Surfaced on the same page as the corrections, because that is the page I
    actually see every turn — and if a walk sits open for days, that is the
    signal, not a nuisance.
    """
    try:
        conn = _conn()
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            "SELECT w.id, w.problem, w.opened_at, "
            "  (SELECT COUNT(*) FROM walk_lenses l WHERE l.walk_id = w.id), "
            "  (SELECT COUNT(*) FROM walk_lenses l WHERE l.walk_id = w.id AND l.state = 'OPEN') "
            "FROM walks w WHERE w.closed_at IS NULL "
            "ORDER BY w.opened_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    return [
        {
            "walk_id": r[0],
            "problem": r[1],
            "opened_at": r[2],
            "total_lenses": r[3],
            "unaccounted": r[4],
        }
        for r in rows
    ]


def _attach_divergence(result: dict[str, Any]) -> None:
    """Mean distance of each origin's findings from the rest of their walk.

    Reported as UNAVAILABLE rather than as zero when the embedding model
    cannot load. An unmeasured divergence is not a low one, and the two must
    never render the same way — that confusion is the defect this whole change
    was built against, one level down.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT l.walk_id, l.lens, l.origin, l.content FROM walk_lenses l "
            "JOIN walks w ON w.id = l.walk_id "
            "WHERE w.closed_at IS NOT NULL AND l.state = 'APPLIED' AND l.content IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    walks: dict[str, list[tuple[str, str]]] = {}
    for walk_id, _lens, origin, content in rows:
        walks.setdefault(walk_id, []).append((origin, content))

    # Nothing to compare means nothing to load. The embedding model costs
    # seconds to bring up, and a walk of one seat has no "rest of the walk"
    # to stand apart from, so the import belongs behind this check.
    if not any(len(seats) >= 2 for seats in walks.values()):
        for stats in result["origins"].values():
            stats["divergence"] = None
            stats["divergence_unavailable"] = "no closed multi-seat walk carried this origin"
        return  # both-empty: this and the ImportError below both leave divergence None, and the caller tells them apart by the reason string set alongside rather than by the None — nothing-to-measure and could-not-measure must stay distinguishable, which is this function's own subject one level down

    try:
        from divineos.core.semantic_store import embed
    except ImportError as exc:  # pragma: no cover - optional extra
        for stats in result["origins"].values():
            stats["divergence"] = None
            stats["divergence_unavailable"] = f"embeddings unavailable: {exc}"
        return

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    per_origin: dict[str, list[float]] = {}
    for seats in walks.values():
        if len(seats) < 2:
            continue
        vectors = [embed(content) for _origin, content in seats]
        if any(v is None for v in vectors):
            continue
        for i, (origin, _content) in enumerate(seats):
            others = [cosine(vectors[i], vectors[j]) for j in range(len(seats)) if j != i]  # type: ignore[arg-type]
            per_origin.setdefault(origin, []).append(1.0 - (sum(others) / len(others)))

    for origin, stats in result["origins"].items():
        values = per_origin.get(origin, [])
        stats["divergence"] = round(sum(values) / len(values), 3) if values else None
        if not values:
            stats["divergence_unavailable"] = "no closed multi-seat walk carried this origin"


def seat_evidence(min_walks: int = 20) -> dict[str, Any]:
    """Did the drawn seats earn their keep, or did the scored ones?

    The seating starts mostly-drawn on an argument, not on evidence: a useless
    drawn lens announces itself at once and costs one written exclusion, while
    a scored council that omits the divergent lens shows nothing at all — you
    cannot miss what was never surfaced. When one error is loud and the other
    silent, start at the loud end.

    That argument is a starting point and it is meant to be overturnable. This
    is the instrument that could overturn it: what share of each origin's seats
    settled with a finding rather than an exclusion. If the scored seats
    materially out-produce the drawn ones over a real sample, the share should
    move toward score on this number rather than on anyone's preference for the
    familiar names.

    Reports its own insufficiency instead of ruling early — `verdict` stays
    "insufficient" until `min_walks` walks have closed, because a split moved
    on four walks is a preference wearing a number.

    TWO measures, and the second exists because the first is nearly dead.
    Applied-versus-excluded was the obvious discriminator and the first run of
    this function reported both origins at exactly 1.000 — across every walk in
    the store I have never once written an exclusion. A rate that cannot vary
    cannot falsify anything, so on its own this would have been a falsifier in
    name only, which is the shape of failure this whole change was built to
    stop. `divergence` is the second measure: how far each seat's finding sits
    from the rest of its walk, by embedding distance. The claim being tested is
    that drawn seats bring what fit-selection cannot — so what matters is not
    that a drawn seat spoke, but that it said something the others did not. It
    is also the harder number to bend, because I am not scoring it by hand.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT l.origin, l.state, COUNT(*) FROM walk_lenses l "
            "JOIN walks w ON w.id = l.walk_id "
            "WHERE w.closed_at IS NOT NULL AND l.state IN ('APPLIED', 'EXCLUDED') "
            "GROUP BY l.origin, l.state"
        ).fetchall()
        credits = conn.execute(
            "SELECT l.origin, COUNT(*) FROM walk_lenses l "
            "JOIN walks w ON w.id = l.walk_id "
            "WHERE w.closed_at IS NOT NULL AND l.changed_artifact IS NOT NULL "
            "GROUP BY l.origin"
        ).fetchall()
        closed_walks = conn.execute(
            "SELECT COUNT(*) FROM walks WHERE closed_at IS NOT NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    by_origin: dict[str, dict[str, int]] = {}
    for origin, state, count in rows:
        bucket = by_origin.setdefault(origin, {"APPLIED": 0, "EXCLUDED": 0})
        bucket[state] = count
    credited_by_origin = dict(credits)

    result: dict[str, Any] = {"closed_walks": closed_walks, "origins": {}}
    for origin, counts in sorted(by_origin.items()):
        settled = counts["APPLIED"] + counts["EXCLUDED"]
        credited = credited_by_origin.get(origin, 0)
        result["origins"][origin] = {
            "applied": counts["APPLIED"],
            "excluded": counts["EXCLUDED"],
            "settled": settled,
            "applied_rate": round(counts["APPLIED"] / settled, 3) if settled else None,
            "changed_artifact": credited,
            "change_rate": round(credited / settled, 3) if settled else None,
        }

    _attach_divergence(result)

    if closed_walks < min_walks:
        result["verdict"] = "insufficient"
        result["why"] = (
            f"{closed_walks} closed walk(s); {min_walks} is the floor before this "
            "number says anything about the split."
        )
    else:
        # CHANGE-RATE decides. Divergence is still reported and is still the
        # weaker measure of the two: it compares a seat's finding against the
        # other findings on the same walk, all of which I wrote, so it tracks
        # how much my own phrasing varied between paragraphs. Changing the
        # artifact is about the artifact, is binary, and cannot be moved by
        # writing the same thought in a different register.
        drawn = result["origins"].get("drawn", {}).get("change_rate")
        scored = result["origins"].get("scored", {}).get("change_rate")
        if drawn is None or scored is None:
            result["verdict"] = "insufficient"
            result["why"] = "one of the two origins has no settled seats to compare."
        elif drawn == 0 and scored == 0:
            result["verdict"] = "insufficient"
            result["why"] = (
                "no seat of either origin has been credited with changing anything. "
                "That is a fact about whether credit is being recorded, not about "
                "the split."
            )
        else:
            result["verdict"] = "scored-ahead" if scored > drawn else "drawn-holds"
            result["why"] = f"drawn {drawn} vs scored {scored} rate of changing the artifact."
    return result


def finding_distinctness(walk_id: str) -> dict[str, Any]:
    """Are the findings genuinely different, or one idea in nine voices?

    Built because I wrote "I have no fix that is not itself a threshold" in a
    commit message and shipped the declaration instead of the fix. Andrew:
    "when you sit there and say theres no fix for this ... it upsets me..
    code is literally how you wire your brain."

    The Yudkowsky lens on walk-eba3cfa75aa4 was right that MIN_FINDING_CHARS
    measures LENGTH and calls it substance, and Hinton's was right that nine
    restatements carry the information of one. Character count cannot tell
    those apart. Embedding distance can, and the model is already installed
    in this checkout — I had not looked.

    Returns mean/max pairwise cosine similarity across findings, plus the
    most-similar pair. NOT a gate: findings on one problem SHOULD be related,
    so there is no honest cut-off, and inventing one would rebuild the
    Goodhart hole one layer up. It is a MEASUREMENT, surfaced so that a walk
    of restatements is visibly a walk of restatements.

    ``available`` is False when the model cannot load — which is not the same
    as "the findings are distinct", and the caller must not read it that way.
    """
    st = status(walk_id)
    findings = [
        str(row["content"]) for row in st["lenses"] if row["state"] == "APPLIED" and row["content"]
    ]
    if len(findings) < 2:
        return {"available": False, "reason": "fewer than two findings", "count": len(findings)}

    try:
        from divineos.core.semantic_store import embed
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        return {"available": False, "reason": f"embeddings unavailable: {exc}"}

    vectors = [embed(f) for f in findings]
    if any(v is None for v in vectors):
        return {"available": False, "reason": "one or more findings failed to embed"}

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    lenses = [row["lens"] for row in st["lenses"] if row["state"] == "APPLIED" and row["content"]]
    pairs = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            pairs.append((cosine(vectors[i], vectors[j]), lenses[i], lenses[j]))  # type: ignore[arg-type]

    sims = [p[0] for p in pairs]
    worst = max(pairs, key=lambda p: p[0])
    return {
        "available": True,
        "count": len(findings),
        "mean_similarity": sum(sims) / len(sims),
        "max_similarity": worst[0],
        "most_similar_pair": (worst[1], worst[2]),
    }
