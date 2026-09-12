"""Controls for the walk state machine (Aria 2026-08-10).

The refusals ARE the mechanism, so the refusals are what get pinned.
"""

from __future__ import annotations

import pytest

from divineos.core import council_walk as cw

PROBLEM = (
    "Whether a walk that refuses to close produces thinking or a form I fill in with restatements"
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(cw, "divineos_home", lambda: tmp_path)
    yield


def test_lens_set_comes_from_the_manager_not_from_me():
    """The one load-bearing decision: I cannot name my own council.

    WIDENED 2026-09-11, and widening a guard to admit my own change is exactly
    the move that deserves suspicion, so here is the reasoning in full.

    This pinned the signature to {problem, gravity}, which is stronger than the
    property it protects and caught a ``scope`` parameter naming FILES rather
    than lenses. Scope is what lets the build-flow board find a walk at all --
    without it a walk knows its problem and nothing about the work, which is
    why the board counted lens events instead and why four self-chosen ones
    satisfied it.

    A signature pin is a proxy. The property is that NOTHING I pass can change
    which lenses I face. So the allowlist is named explicitly here, and the
    test below proves the property behaviourally rather than by shape -- which
    is the stronger guard, not the weaker one.
    """
    import inspect

    sig = inspect.signature(cw.open_walk)
    assert set(sig.parameters) <= {"problem", "gravity", "scope"}, (
        "open_walk gained a parameter that is not problem/gravity/scope. If it "
        "can carry lenses, I pick the low end every time and the mechanism "
        "becomes a form I fill in."
    )


def test_scope_cannot_change_which_lenses_i_face():
    """The property the signature pin was standing in for.

    Same problem and gravity, wildly different scope: the manager's selection
    must be identical, because it is derived from the PROBLEM and nothing I
    hand it may steer it.
    """
    bare = cw.open_walk(PROBLEM, gravity="normal")
    scoped = cw.open_walk(
        PROBLEM,
        gravity="normal",
        scope=("src/anything.py", "tests/whatever.py", "docs/a.md"),
    )
    assert bare["lenses"] == scoped["lenses"]


def test_close_refuses_while_a_lens_is_open():
    w = cw.open_walk(PROBLEM)
    with pytest.raises(cw.WalkRefused, match="unaccounted"):
        cw.close_walk(w["walk_id"])


def test_exclusion_needs_more_substance_than_a_finding():
    """Excluding is the cheap move, so it costs more words."""
    assert cw.MIN_EXCLUSION_CHARS > cw.MIN_FINDING_CHARS
    w = cw.open_walk(PROBLEM)
    with pytest.raises(cw.WalkRefused):
        cw.exclude_lens(w["walk_id"], w["lenses"][0], "not relevant")


def test_a_lens_not_on_the_walk_is_refused():
    w = cw.open_walk(PROBLEM)
    with pytest.raises(cw.WalkRefused, match="not on this walk"):
        cw.apply_lens(w["walk_id"], "Gandalf", "x" * 60)


def test_completed_walk_is_spent_once():
    """Schneier: a completed walk must not be a permanent pass."""
    w = cw.open_walk(PROBLEM)
    for lens in w["lenses"]:
        cw.apply_lens(w["walk_id"], lens, f"{lens}: a real finding of sufficient length to pass")
    cw.close_walk(w["walk_id"])
    assert cw.is_complete(w["walk_id"]) is True
    cw.consume(w["walk_id"])
    assert cw.is_complete(w["walk_id"]) is False


def test_open_walks_has_a_reader():
    """Peirce: the store had no consumer, which is the disease it treats."""
    assert cw.open_walks() == []
    w = cw.open_walk(PROBLEM)
    rows = cw.open_walks()
    assert len(rows) == 1
    assert rows[0]["walk_id"] == w["walk_id"]
    assert rows[0]["unaccounted"] == len(w["lenses"])


def test_gravity_floor_is_andrews_ladder():
    assert cw.GRAVITY_FLOORS == {"normal": 5, "high": 9, "severe": 12, "critical": 15}


def test_distinctness_needs_two_findings_and_says_so():
    """Unavailable must never read as 'the findings are distinct'."""
    w = cw.open_walk(PROBLEM)
    d = cw.finding_distinctness(w["walk_id"])
    assert d["available"] is False
    assert "fewer than two" in d["reason"]

    cw.apply_lens(w["walk_id"], w["lenses"][0], "a single finding of sufficient length to store")
    d = cw.finding_distinctness(w["walk_id"])
    assert d["available"] is False, "one finding cannot have a pairwise similarity"


def test_distinctness_reports_rather_than_gates():
    """A cut-off here would rebuild the Goodhart hole one layer up.

    Findings on one problem SHOULD be related, so no honest threshold exists.
    Measured 2026-08-10: two real walks 0.208 and 0.270 mean; a fabricated
    walk of nine restatements 0.436. A clear gap, not a bright line.
    """
    import inspect

    src = inspect.getsource(cw.close_walk)
    assert "distinct" not in src.lower(), (
        "close_walk must not consult distinctness — it reports, it does not gate"
    )
