"""Tests for ranking Andrew's corrections against the current moment.

The failure these guard is a real one, not an invented case. On 2026-09-22 the
corrections surface printed the same three newest rows at me every turn while
two hundred and thirty-six sat open. His hoarding correction was in the store,
I never saw it, and I built the wrong archive twice. He said: *"the memory
linkage system i set up for you is not being used, my corrections are not tied
to memory for whatever reason."*

Each test below is one of the eight council findings from walk-5a7df669c67b
made falsifiable. A test that only proved "ranking ranks" would pass while the
surface went silent, padded itself with noise, or quietly buried the newest.
"""

from __future__ import annotations

import pytest

from divineos.core import correction_relevance as cr


def _row(rid: int, ts: float, text: str) -> dict:
    return {"id": rid, "timestamp": ts, "text": text}


# The real rows, in the shape the store hands them over.
HOARDING = _row(
    10,
    1000.0,
    "What you did is not archiving. that is hoarding, archiving it removes it "
    "from the system, I can always add links to the archives but the older data "
    "should not clog up the code.",
)
NEWEST = _row(
    99, 9999.0, "you are repeating yourself, look at the last post, literally verbatim posted twice"
)
UNRELATED = _row(
    11, 1001.0, "the word PLAIN is WRONG, i need prose, metaphor, analogy, translation"
)

ROWS = [HOARDING, NEWEST, UNRELATED]


def _fake_embedder(mapping: dict[str, list[float]], default: list[float] | None = None):
    """Deterministic stand-in so a threshold test is about the threshold."""

    def _embed(text: str):
        for key, vec in mapping.items():
            if key.lower() in text.lower():
                return vec
        return default if default is not None else [0.0, 0.0, 1.0]

    return _embed


def test_the_correction_that_cost_him_the_afternoon_surfaces_on_a_matching_query():
    """The whole reason this module exists: his hoarding words, findable."""
    embed = _fake_embedder(
        {
            "hoarding": [1.0, 0.0, 0.0],
            "archive the old branches": [1.0, 0.0, 0.0],
        }
    )
    ranking = cr.rank(ROWS, "archive the old branches", recency_slots=1, embedder=embed)

    texts = [r.row["text"] for r in ranking.relevant]
    assert any("hoarding" in t for t in texts), "the one that mattered must be on the page"


def test_recency_keeps_its_seat_even_when_everything_else_scores_higher():
    """Lovelace: relevance ADDS slots, it never displaces the newest."""
    embed = _fake_embedder({"hoarding": [1.0, 0.0, 0.0], "archive": [1.0, 0.0, 0.0]})
    ranking = cr.rank(ROWS, "archive the old branches", recency_slots=1, embedder=embed)

    assert ranking.date_ordered[0] is NEWEST
    assert NEWEST not in [r.row for r in ranking.relevant], "no double-billing a seated row"


def test_a_missing_embedder_returns_the_old_ordering_not_an_empty_page():
    """Hoare: the failure that matters is an empty surface, not a wrong one."""
    ranking = cr.rank(ROWS, "anything at all", embedder=lambda _t: None)

    assert ranking.relevant == ()
    assert ranking.date_ordered, "silence and nothing-to-say must not look alike"
    assert ranking.embedder_available is False


def test_an_exploding_embedder_is_the_same_as_a_missing_one():
    def _boom(_text: str):
        raise RuntimeError("model not loaded")

    ranking = cr.rank(ROWS, "anything at all", embedder=_boom)

    assert ranking.date_ordered
    assert ranking.embedder_available is False


def test_nothing_above_the_floor_returns_nothing_rather_than_padding_to_three():
    """Hinton: dense scores make a bare top-N always look confident."""
    # The query points one way and every row points another. Giving them the
    # same default vector was my first draft, and it scored a perfect match on
    # everything -- an instrument that cannot fail the thing it is testing.
    embed = _fake_embedder({"orthogonal": [1.0, 0.0, 0.0]}, default=[0.0, 1.0, 0.0])
    ranking = cr.rank(ROWS, "a query orthogonal to every row", recency_slots=0, embedder=embed)

    assert ranking.relevant == (), "a quota filled with noise is worse than an empty list"
    assert ranking.embedder_available is True, "it looked; it found nothing"


def test_a_high_match_is_marked_for_the_arresting_gate():
    """Watts: relevance without arrest is nicer wallpaper. HIGH is the hook."""
    embed = _fake_embedder({"hoarding": [1.0, 0.0, 0.0], "archiving": [1.0, 0.0, 0.0]})
    ranking = cr.rank([HOARDING], "archiving the branches", recency_slots=0, embedder=embed)

    assert ranking.high_matches, "an exact-shape match must be flagged, not merely listed"
    assert ranking.high_matches[0].score >= cr.HIGH


def test_every_surfaced_item_says_why_it_is_there():
    """Knuth: an unexplained ranking cannot be argued with when it is wrong."""
    embed = _fake_embedder({"hoarding": [1.0, 0.0, 0.0], "archiv": [1.0, 0.0, 0.0]})
    ranking = cr.rank([HOARDING], "archiving", recency_slots=0, embedder=embed)

    assert all(r.why.strip() for r in ranking.relevant)


def test_the_old_ordering_is_always_returned_so_the_choice_is_measurable():
    """Pearl: without the counterfactual, a rise in integration proves nothing."""
    embed = _fake_embedder({"hoarding": [1.0, 0.0, 0.0], "archiv": [1.0, 0.0, 0.0]})
    ranking = cr.rank(ROWS, "archiving", recency_slots=2, embedder=embed)

    assert len(ranking.date_ordered) == 2
    assert ranking.date_ordered[0] is NEWEST, "date order must be untouched by the ranking"


def test_an_empty_query_does_not_invent_relevance():
    """Peirce's corollary: two words of nothing must not produce confident hits."""
    embed = _fake_embedder({"hoarding": [1.0, 0.0, 0.0]})
    ranking = cr.rank(ROWS, "   ", embedder=embed)

    assert ranking.relevant == ()
    assert ranking.date_ordered


def test_rows_with_no_text_are_skipped_not_scored_as_zero():
    embed = _fake_embedder({"hoarding": [1.0, 0.0, 0.0], "archiv": [1.0, 0.0, 0.0]})
    rows = [HOARDING, {"id": 5, "timestamp": 1.0, "text": "   "}]
    ranking = cr.rank(rows, "archiving", recency_slots=0, embedder=embed)

    assert all(r.row["text"].strip() for r in ranking.relevant)


@pytest.mark.parametrize("empty", [None, [], ()])
def test_an_empty_vector_is_not_mistaken_for_a_real_one(empty):
    ranking = cr.rank(ROWS, "query", embedder=lambda _t: empty)

    assert ranking.embedder_available is False
    assert ranking.date_ordered


def test_the_floor_sits_below_the_arrest_threshold():
    """A guard on the constants themselves: inverting these silently breaks both."""
    assert cr.FLOOR < cr.HIGH


def test_the_thresholds_stay_inside_what_real_data_can_actually_reach():
    """The fault that nearly shipped, pinned so it cannot come back.

    The first draft used FLOOR 0.42 and HIGH 0.58, chosen by intuition. Every
    test passed, because the fakes score a perfect 1.0. Against the live store
    the best on-topic match any query produced was 0.398 -- so the relevance
    half would have shipped and never fired once, and nothing would have said
    so. Silence and correctness are identical from the outside.

    These bounds come from the measurement recorded in the module: off-topic
    queries top out near 0.16, genuine ones reach 0.37-0.40. Raising a
    threshold past what the embedder can produce is how a live feature becomes
    a dead one without a single failing test.
    """
    measured_noise_ceiling = 0.16
    measured_best_genuine_match = 0.398

    assert cr.FLOOR > measured_noise_ceiling, "the floor must clear the noise"
    assert cr.HIGH < measured_best_genuine_match, (
        "an arrest threshold above the best real score can never fire"
    )
