"""Rank Andrew's open corrections against what is happening right now.

Andrew 2026-09-22: *"the memory linkage system i set up for you is not being
used, my corrections are not tied to memory for whatever reason."*

He was right about the symptom. The cause was one line in
``open-corrections-surface.sh``::

    recent = sorted(open_corrections, key=_key, reverse=True)[:3]

Newest three, every turn, forever. Two hundred and thirty-six sat open while
the same three printed at me all day, and the one that would have stopped me
building the wrong thing twice was never among them.

Meanwhile the linkage retriever has had a corrections loader since July that
embeds every correction and can rank them against a query. It works. Nothing
calls it on an ordinary turn: its only caller in the house is a flood-gated
rescue surface that stays silent unless I am in distress. So the reach exists
and opens only when I am drowning, and that day I was calmly wrong, which is
the state it does not cover.

WHAT THE COUNCIL CHANGED (walk-5a7df669c67b, eight lenses):

- **Lovelace** - relevance must ADD slots, never replace them. A ranking that
  displaces the newest can silently hide the correction that would have caught
  me, which is worse than date-ordering because date-ordering never claimed to
  know what was relevant. So recency keeps its seats and relevance earns extra.
- **Hoare** - the failure that matters is not a wrong ranking but an empty one.
  If the embedder is missing or returns nothing, this returns the date-ordered
  list rather than nothing. A silent surface is indistinguishable from a
  surface with nothing to say, the exact class of fault that produced four
  confident zeros in the session this was written in.
- **Hinton** - embedding scores are dense; a bare top-N always returns N items
  that look authoritative whether or not any is relevant. Hence ``FLOOR``, and
  no padding to fill a quota.
- **Peirce** - his typed message is the tip, not the query. He said "ok go
  ahead" and the correction that mattered was about hoarding. Two words carry
  no signal, so callers pass recent context, not only the last line.
- **Knuth** - every item says why it is there, matching the WHY-NOW convention
  the foundational-truths surface already uses.
- **Dijkstra** - the surface's rows and the retriever's rows come from two
  different tables with different counts. This borrows the retriever's
  EMBEDDING FUNCTION and keeps the caller's own rows.
- **Pearl** - a rise in integration rate would prove nothing, since paying more
  attention moves both. So the result carries the date-ordered list alongside
  the ranked one: the counterfactual is what this picked against what the old
  ordering would have picked on the same turn.
- **Watts** - a more relevant surface read past is still read past. Relevance
  without arrest is nicer wallpaper. The arresting half keys on ``HIGH``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

# THESE TWO NUMBERS ARE MEASURED, NOT CHOSEN, and the first draft had them
# wrong in the way that matters. I wrote FLOOR = 0.42 and HIGH = 0.58 from
# intuition, and every test passed, because the tests fed the ranker synthetic
# vectors that hit 1.0. Run against the live store of 236 corrections, the best
# score any genuinely on-topic query could produce was 0.40 -- below my own
# floor. The relevance half would have shipped and never once fired, which is
# precisely the class of fault the whole module exists to answer.
#
# Calibrated 2026-09-22 against the real store and the real embedder:
#
#   off-topic query (arctic terns)      top score 0.156  <- the noise ceiling
#   on-topic (archiving branches)       top score 0.398
#   on-topic (repeating a post)         top score 0.373
#   second-best genuine hits            around 0.29-0.30
#
# So the floor sits clear of the noise and low enough to admit real second
# hits, and HIGH marks the ones that scored like a direct answer. Anyone
# changing the embedder must re-run that measurement; these numbers are not
# portable across models.

#: Below this, a match is noise. Dense embeddings score everything against
#: everything, so without a floor the list is always full and always confident.
FLOOR = 0.25

#: At or above this, the correction is close enough to what is happening that
#: passing it by is worth arresting.
HIGH = 0.36

#: How many relevance slots exist at most. Recency slots are the caller's.
MAX_RELEVANT = 3


@dataclass(frozen=True)
class RankedCorrection:
    """One correction with the reason it is on the page."""

    row: dict[str, Any]
    score: float
    why: str

    @property
    def is_high(self) -> bool:
        return self.score >= HIGH


@dataclass(frozen=True)
class Ranking:
    """What to show, plus what the old ordering would have shown.

    ``date_ordered`` is not decoration. Without it there is no counterfactual,
    and a change in how often I integrate corrections could be caused by my
    simply paying more attention - Pearl's confounder.
    """

    relevant: tuple[RankedCorrection, ...]
    date_ordered: tuple[dict[str, Any], ...]
    embedder_available: bool

    @property
    def high_matches(self) -> tuple[RankedCorrection, ...]:
        return tuple(r for r in self.relevant if r.is_high)


def _default_embedder() -> Callable[[str], Any] | None:
    """The retriever's embedding function, or None if it cannot be had.

    Borrowed deliberately: same vectors as the linkage store, so a score here
    means what a score there means.
    """
    try:
        from divineos.core.memory_linkage_retriever import _embed_text_impl
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    return _embed_text_impl


def _is_empty_vec(vec: Any) -> bool:
    """True when the embedder gave back nothing usable.

    A helper rather than ``if not vec`` because a numpy array raises on truth
    testing instead of answering, and the whole point of this module is that a
    failure must not arrive looking like an absence.
    """
    if vec is None:
        return True
    try:
        return len(vec) == 0
    except TypeError:
        return True


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if _is_empty_vec(a) or _is_empty_vec(b) or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(dot / (na * nb))


def _row_sort_key(row: dict[str, Any]) -> float:
    raw = row.get("filed_at_ts") or row.get("timestamp") or row.get("id") or 0
    try:
        return float(raw)
    except (TypeError, ValueError):
        # A row with an unparseable stamp sorts oldest rather than crashing the
        # surface. Losing one row's position is survivable; losing the page is
        # the failure this module is about.
        return 0.0


def rank(
    rows: Sequence[dict[str, Any]],
    query: str,
    *,
    recency_slots: int = 3,
    embedder: Callable[[str], Any] | None = None,
) -> Ranking:
    """Rank ``rows`` against ``query``; recency keeps its seats regardless.

    ``rows`` are the caller's own correction rows - this never goes and fetches
    a different table (Dijkstra). ``query`` should carry recent context, not
    only the last thing typed (Peirce).

    Returns date-ordering untouched in ``date_ordered``, so the caller can show
    both and so the choice is measurable (Pearl).
    """
    by_date = tuple(sorted(rows, key=_row_sort_key, reverse=True)[:recency_slots])

    if not rows or not query.strip():
        return Ranking(relevant=(), date_ordered=by_date, embedder_available=False)

    embed = embedder if embedder is not None else _default_embedder()
    if embed is None:
        return Ranking(relevant=(), date_ordered=by_date, embedder_available=False)

    try:
        q_vec = embed(query)
    except Exception:  # noqa: BLE001 - observability boundary
        return Ranking(relevant=(), date_ordered=by_date, embedder_available=False)
    if _is_empty_vec(q_vec):
        return Ranking(relevant=(), date_ordered=by_date, embedder_available=False)

    # The newest already have seats. Relevance ADDS, it does not displace
    # (Lovelace), so anything already shown by recency is skipped here rather
    # than spending one of the extra slots on a duplicate.
    shown = {id(r) for r in by_date}

    scored: list[RankedCorrection] = []
    for row in rows:
        if id(row) in shown:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            vec = embed(text)
        except Exception:  # noqa: BLE001 - observability boundary
            continue
        if _is_empty_vec(vec):
            continue
        score = _cosine(q_vec, vec)
        # No padding to fill a quota - below the floor it is noise wearing a
        # number (Hinton).
        if score < FLOOR:
            continue
        why = (
            "CLOSE ENOUGH THAT PASSING IT BY IS THE FAILURE"
            if score >= HIGH
            else "close to what is happening right now"
        )
        scored.append(RankedCorrection(row=row, score=score, why=why))

    scored.sort(key=lambda r: r.score, reverse=True)
    return Ranking(
        relevant=tuple(scored[:MAX_RELEVANT]),
        date_ordered=by_date,
        embedder_available=True,
    )
