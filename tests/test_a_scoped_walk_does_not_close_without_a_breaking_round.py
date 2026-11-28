"""A walk that is FOR some files does not close until a breaking round has been walked.

Dad, 2026-11-13: *"overlap is not a metric to meet its just a metric.. if something has low overlap there will be less to
disagree.. so you do not create them instead you just go harder on the breaking council phase with the 12 members that
tear it apart, demand proof, or falsification etc etc"*, and, asked which lenses those are: *"look at the lenses
themselves.. it may be more than 12.. which lenses provide the most scrutiny.. Feynman, Schneier, Popper, Dillahunty,
Beer, Kahneman and im sure there are more"*. Design: docs/drafts/a_walk_finding_must_show_contact_with_the_template_draft_2026-11-12.md.

What this pins: a walk opened with a scope cannot close unless the Breaker lens (built for adversarial self-review) and at
least MIN_SCRUTINY_BESIDES_BREAKER other lenses from SCRUTINY_LENSES have a finding. What it does NOT pin: that the
breaking was real. That stays his to see; the check only makes the walk with no breaking at all impossible. It never reads
overlap and never forces a disagreement.
"""

from __future__ import annotations

import pytest

from divineos.core import council_walk as cw
from divineos.core.council.engine import get_council_engine
from tests._walk_helpers import apply_delivered, contact_finding

PROBLEM = "Whether a walk that changes how walks work must be broken on purpose before it is allowed to close"
LONG_WHY = (
    "added by the test so the breaking round exists; a free addition would be a picked council"
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(cw, "divineos_home", lambda: tmp_path)
    yield


def _settle_all(walk_id: str, leave_out: tuple[str, ...] = ()) -> None:
    for lens in cw.status(walk_id)["open_lenses"]:
        if lens in leave_out:
            cw.deliver_lens(
                lens, walk_id
            )  # an exclusion, like a finding, needs the lens delivered first
            cw.exclude_lens(
                walk_id,
                lens,
                contact_finding(
                    cw,
                    lens,
                    "left out on purpose in this test so the missing breaking round can be seen",
                ),
                question=1,
            )
        else:
            apply_delivered(cw, walk_id, lens, "a finding written inside the test")


def test_the_scrutiny_set_names_only_lenses_that_exist():
    engine = get_council_engine()
    for name in cw.SCRUTINY_LENSES:
        assert engine.get_expert(name) is not None, (
            f"{name} is in the scrutiny set but not on the roster"
        )


def test_breaker_is_in_the_scrutiny_set_and_is_the_one_that_must_be_present():
    assert "Breaker" in cw.SCRUTINY_LENSES
    assert cw.REQUIRED_BREAKER == "Breaker"


def test_a_scoped_walk_does_not_close_without_the_breaker():
    opened = cw.open_walk(PROBLEM, scope=("src/divineos/core/council_walk.py",))
    _settle_all(opened["walk_id"], leave_out=("Breaker",))
    with pytest.raises(cw.WalkRefused) as refused:
        cw.close_walk(opened["walk_id"])
    assert "Breaker" in str(refused.value)


def test_a_scoped_walk_does_not_close_with_the_breaker_alone():
    opened = cw.open_walk(PROBLEM, scope=("src/divineos/core/council_walk.py",))
    walk = opened["walk_id"]
    _settle_all(walk, leave_out=tuple(n for n in cw.SCRUTINY_LENSES if n != "Breaker"))
    if "Breaker" not in {row["lens"] for row in cw.status(walk)["lenses"]}:
        cw.add_lens(walk, "Breaker", LONG_WHY)
        _settle_all(walk, leave_out=tuple(n for n in cw.SCRUTINY_LENSES if n != "Breaker"))
    with pytest.raises(cw.WalkRefused) as refused:
        cw.close_walk(walk)
    assert str(cw.MIN_SCRUTINY_BESIDES_BREAKER) in str(refused.value)


def test_a_scoped_walk_closes_once_the_breaker_and_enough_scrutiny_have_findings(tmp_path):
    opened = cw.open_walk(PROBLEM, scope=("src/divineos/core/council_walk.py",))
    walk = opened["walk_id"]
    _settle_all(walk)
    present = {row["lens"] for row in cw.status(walk)["lenses"]}
    for name in ("Breaker", "Popper", "Schneier", "Feynman"):
        if name not in present:
            cw.add_lens(walk, name, LONG_WHY)
    _settle_all(walk)
    result = cw.close_walk(walk, repo=tmp_path)
    assert result["closed"] is True


def test_an_unscoped_walk_is_not_held_to_the_breaking_round():
    """A walk about something that is not a code change is still a walk; refusing it would push toward the weak path."""
    opened = cw.open_walk(PROBLEM)
    _settle_all(opened["walk_id"], leave_out=tuple(cw.SCRUTINY_LENSES))
    if cw.status(opened["walk_id"])["findings"] == 0:
        pytest.skip(
            "every surfaced lens was a scrutiny lens, so nothing was applied; the draw, not the rule"
        )
    assert cw.close_walk(opened["walk_id"])["closed"] is True


def test_the_refusal_says_how_to_get_a_breaking_round_so_the_right_path_is_the_cheap_one():
    opened = cw.open_walk(PROBLEM, scope=("src/divineos/core/council_walk.py",))
    _settle_all(opened["walk_id"], leave_out=("Breaker",))
    with pytest.raises(cw.WalkRefused) as refused:
        cw.close_walk(opened["walk_id"])
    assert "walk add" in str(refused.value) or "add_lens" in str(refused.value)
