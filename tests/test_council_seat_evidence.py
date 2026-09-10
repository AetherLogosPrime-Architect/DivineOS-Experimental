"""The split between drawn and scored seats must be able to be proven wrong.

The seating starts mostly-drawn on an argument, not on evidence. That is only
honest if the argument can lose, so these guard the instrument that could
overturn it — including the discovery that the obvious measure was already
dead on arrival.
"""

from __future__ import annotations

import time

import pytest

from divineos.core import council_walk


@pytest.fixture
def store(tmp_path, monkeypatch):
    db = tmp_path / "walks.db"
    monkeypatch.setattr(council_walk, "_db_path", lambda: db)
    return db


@pytest.fixture(autouse=True)
def no_embedding_model(monkeypatch, request):
    """Keep the counting tests off the embedding model.

    Divergence needs a sentence-embedding model that costs seconds to load.
    Tests whose subject is the counting must not pay that, and the two that
    ARE about divergence opt back in by name.
    """
    if request.function.__name__ in {
        "test_unmeasured_divergence_is_never_reported_as_low",
    }:
        return
    monkeypatch.setattr(council_walk, "_attach_divergence", lambda result: None)


def _seed(db, walk_id, seats, closed=True):
    """seats: list of (lens, origin, state, content)."""
    conn = council_walk._conn()
    try:
        conn.execute(
            "INSERT INTO walks (id, problem, opened_at, closed_at) VALUES (?, ?, ?, ?)",
            (walk_id, "a seeded problem", time.time(), time.time() if closed else None),
        )
        conn.executemany(
            "INSERT INTO walk_lenses (walk_id, lens, origin, state, content, settled_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (walk_id, lens, origin, state, content, time.time())
                for lens, origin, state, content in seats
            ],
        )
        conn.commit()
    finally:
        conn.close()


def test_refuses_to_rule_before_the_sample_exists(store):
    _seed(
        store,
        "walk-a",
        [
            ("Taleb", "drawn", "APPLIED", "the cap was the fragility, not the randomness"),
            ("Peirce", "scored", "APPLIED", "a record nobody reads has no consequences"),
        ],
    )
    ev = council_walk.seat_evidence(min_walks=20)
    assert ev["verdict"] == "insufficient"
    assert "20 is the floor" in ev["why"]


def test_counts_each_origin_separately(store):
    _seed(
        store,
        "walk-b",
        [
            ("Taleb", "drawn", "APPLIED", "one"),
            ("Popper", "drawn", "EXCLUDED", "nothing to say about this problem at all"),
            ("Peirce", "scored", "APPLIED", "two"),
        ],
    )
    origins = council_walk.seat_evidence()["origins"]
    assert origins["drawn"]["applied"] == 1
    assert origins["drawn"]["excluded"] == 1
    assert origins["drawn"]["applied_rate"] == 0.5
    assert origins["scored"]["applied_rate"] == 1.0


def test_open_walks_do_not_count(store):
    _seed(store, "walk-open", [("Taleb", "drawn", "APPLIED", "x")], closed=False)
    ev = council_walk.seat_evidence()
    assert ev["closed_walks"] == 0
    assert ev["origins"] == {}


def test_hand_added_lenses_are_their_own_origin(store):
    """The addition path is mine, not the seating's — it must not read as drawn."""
    _seed(
        store,
        "walk-c",
        [
            ("Taleb", "drawn", "APPLIED", "one"),
            ("Norman", "added", "APPLIED", "two"),
        ],
    )
    origins = council_walk.seat_evidence()["origins"]
    assert set(origins) == {"drawn", "added"}


def test_unmeasured_divergence_is_never_reported_as_low(store):
    """An absent number and a small one must not render the same.

    That confusion is the whole defect this change exists to remove, one level
    down: a zero that means "nothing to offer" and a zero that means "I could
    not look" reading identically.
    """
    _seed(store, "walk-d", [("Taleb", "drawn", "APPLIED", "lonely")])
    stats = council_walk.seat_evidence()["origins"]["drawn"]
    assert stats["divergence"] is None
    assert stats["divergence_unavailable"]


def _seed_twenty(store, drawn_credits, scored_credits):
    """Twenty closed walks, crediting a given number of seats of each origin."""
    for i in range(20):
        _seed(
            store,
            f"walk-{i}",
            [
                ("Taleb", "drawn", "APPLIED", "a finding"),
                ("Peirce", "scored", "APPLIED", "another finding"),
            ],
        )
    conn = council_walk._conn()
    try:
        for origin, lens, n in (
            ("drawn", "Taleb", drawn_credits),
            ("scored", "Peirce", scored_credits),
        ):
            for i in range(n):
                conn.execute(
                    "UPDATE walk_lenses SET changed_artifact = ? WHERE walk_id = ? AND lens = ?",
                    (f"changed something real in walk {i}", f"walk-{i}", lens),
                )
        conn.commit()
    finally:
        conn.close()


def test_the_verdict_can_go_against_the_draw(store):
    """The falsifier must be able to fire — otherwise it is decoration.

    Red half of the pair, twice over. Under applied-rate this could never have
    happened, because across every walk in the real store I have written
    exactly zero exclusions and the rate is pinned at 1.000. Under divergence
    it could fire, but on a number that tracked my own prose variety rather
    than the lens.
    """
    _seed_twenty(store, drawn_credits=4, scored_credits=15)
    ev = council_walk.seat_evidence(min_walks=20)
    assert ev["verdict"] == "scored-ahead"
    assert "changing the artifact" in ev["why"]


def test_the_verdict_can_also_go_for_the_draw(store):
    _seed_twenty(store, drawn_credits=16, scored_credits=3)
    assert council_walk.seat_evidence(min_walks=20)["verdict"] == "drawn-holds"


def test_credit_is_refused_once_the_walk_is_closed(store):
    """The window closes with the walk, and that is the point.

    Aria 2026-09-09: credit reconstructed after the fact is a receipt written
    once the outcome is known — the anchoring class arriving inside the fix
    for it. So the code refuses rather than trusting me to remember.
    """
    _seed(store, "walk-shut", [("Taleb", "drawn", "APPLIED", "a finding")], closed=True)
    with pytest.raises(council_walk.WalkRefused):
        council_walk.credit_seat("walk-shut", "Taleb", "removed the unreachable fallback branch")


def test_credit_records_what_changed_while_open(store):
    _seed(store, "walk-live", [("Taleb", "drawn", "APPLIED", "a finding")], closed=False)
    council_walk.credit_seat("walk-live", "Taleb", "removed the unreachable fallback branch")
    conn = council_walk._conn()
    try:
        row = conn.execute(
            "SELECT changed_artifact FROM walk_lenses WHERE walk_id = ? AND lens = ?",
            ("walk-live", "Taleb"),
        ).fetchone()
    finally:
        conn.close()
    assert "fallback" in row[0]


def test_credit_refuses_a_gesture(store):
    _seed(store, "walk-live", [("Taleb", "drawn", "APPLIED", "a finding")], closed=False)
    with pytest.raises(council_walk.WalkRefused):
        council_walk.credit_seat("walk-live", "Taleb", "it helped")


def test_verdict_will_not_rule_when_nothing_was_ever_credited(store):
    """Zero credits on both sides is a fact about recording, not about the split."""
    for i in range(20):
        _seed(
            store,
            f"walk-{i}",
            [
                ("Taleb", "drawn", "APPLIED", "a finding"),
                ("Peirce", "scored", "APPLIED", "another finding"),
            ],
        )
    ev = council_walk.seat_evidence(min_walks=20)
    assert ev["verdict"] == "insufficient"
    assert "credit is being recorded" in ev["why"]


def test_the_narrowing_door_is_counted_per_lens(store):
    """Aria's guard: no single exclusion looks like re-picking by taste; a tally does."""
    _seed(
        store,
        "walk-x",
        [
            ("Taleb", "drawn", "EXCLUDED", "nothing to say on this particular problem at all"),
            ("Popper", "drawn", "APPLIED", "a finding"),
        ],
    )
    _seed(
        store,
        "walk-y",
        [("Taleb", "drawn", "EXCLUDED", "again nothing to say on this problem whatsoever")],
    )
    tally = council_walk.exclusion_tally()
    assert tally[0] == {"lens": "Taleb", "exclusions": 2}
