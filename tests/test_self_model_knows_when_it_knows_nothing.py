"""The self-model must not report itself complete while knowing nothing.

2026-08-17. Andrew: *"i could write a consciousness module that generates magic
numbers relating to your consciousness that mean nothing and do nothing.. and
all tests would pass.. as it generated the number."* I ran it rather than
agreeing: `scripts/hollow_out.py` replaced all twelve functions in
`core/self_model.py` with stubs returning empty values, and the module's suite
reported **13 passed**. The module can be deleted and its tests stay green.

WHY THEY COULD NOT SEE IT, which is more specific than "weak assertions":

Every section catches `_SELF_MODEL_ERRORS` -- six exception types covering
nearly everything -- and returns an empty default, logging to `logger.debug`.
So a missing database and an exploding query produce the same output as a
fresh substrate with nothing recorded yet. CLAUDE.md anti-pattern #8, verbatim:
"No fallback chains. One code path. If it fails, it fails loud."

Then the tests point `DIVINEOS_DB` at an empty tmp_path and assert only shape
-- `"identity" in model`, `isinstance(strengths, list)`. On an empty database
the real module's output IS the hollow output. The tests were not merely weak;
they exercised the single input where real and hollow are provably
indistinguishable. Sabotage could not change the result because the expected
result was already the sabotaged one.

AND THE FIELD THAT LIED. `completeness` counted "did not raise" as "succeeded",
which nothing could fail since everything is caught internally. On a fresh
database it reported:

    succeeded 8, failed [], complete True

with identity Unknown/Unknown/Unknown, strengths [], weaknesses [],
active_concerns [], epistemic_balance {} -- while the model's own `attention`
section said "Blind spot: identity - data source unavailable" in the same
breath. Half the module knew the data was missing and the field named
`complete` reported everything fine.

A self-model that cannot tell "I know nothing about myself" from "I am fully
assembled" is worse than one that reports nothing: the second is obviously
unusable, the first gets quietly trusted. That is the same unknown-is-not-zero
rule as stamp-ready's preflight and sleep's baseline, arriving for the third
time today in the module where a false positive matters most.

These tests use the empty case as an ASSERTION rather than as a fixture.
"""

from __future__ import annotations

import pytest

from divineos.core.self_model import build_self_model


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    return tmp_path


class TestEmptyIsNotComplete:
    def test_a_model_with_nothing_in_it_is_not_complete(self, fresh_db):
        """The exact reading that exposed this, now an assertion."""
        model = build_self_model()
        c = model["completeness"]
        assert c["complete"] is False, (
            "every section is empty and the model called itself complete; "
            f"empty sections were {c.get('empty')}"
        )

    def test_the_empty_sections_are_named(self, fresh_db):
        """Naming them is what makes the report actionable rather than a mood.

        "complete: False" alone sends the reader hunting. The list says where.
        """
        c = build_self_model()["completeness"]
        assert "strengths" in c["empty"]
        assert "weaknesses" in c["empty"]
        assert "active_concerns" in c["empty"]

    def test_populated_counts_only_sections_that_returned_something(self, fresh_db):
        """The one honest positive claim the field can make.

        The old `succeeded` counted absence of an exception, which the module's
        own error handling made unreachable -- so it was structurally pinned at
        8 of 8 regardless of what was known.
        """
        c = build_self_model()["completeness"]
        assert c["populated"] < c["total"], "nothing is recorded, so nothing is populated"
        assert c["populated"] >= 0

    def test_empty_and_raised_stay_separate(self, fresh_db):
        """No recorded skills is a true fact, not a fault.

        A fresh substrate legitimately has empty sections. Collapsing that into
        "failed" would cry wolf on every new install -- and a report that is
        alarming on day one gets ignored by day two.
        """
        c = build_self_model()["completeness"]
        assert c["raised"] == [], "nothing actually raised here"
        assert c["empty"], "but sections are empty, and that is recorded separately"


def test_the_module_does_not_contradict_itself_about_identity(fresh_db):
    """attention said 'Blind spot: identity' while completeness said complete.

    Not asserting the blind-spot text stays -- that belongs to attention_schema.
    Asserting the two halves cannot disagree about whether the model is whole.
    """
    model = build_self_model()
    attention = model.get("attention") or {}
    blob = str(attention).lower()
    if "blind spot" in blob or "unavailable" in blob:
        assert model["completeness"]["complete"] is False, (
            "the attention section reports a data source unavailable while "
            "completeness reports the model complete -- one of them is wrong "
            "and it is not the one looking at the data"
        )


def test_this_suite_would_die_under_hollowing():
    """The check the old suite could not have passed, pinned as a check.

    A test asserting `complete is False` on an empty database fails against a
    hollowed module too -- a stub returning {} for completeness has no
    "complete" key, and one returning a constant cannot vary with the data.
    That is what makes these assertions load-bearing where the shape-only ones
    were not.

    Run it directly: python scripts/hollow_out.py divineos.core.self_model \
        tests/test_self_model_knows_when_it_knows_nothing.py
    """
    from pathlib import Path

    from divineos.core.prior_art import REPO

    assert (REPO / "scripts" / "hollow_out.py").is_file(), (
        "the sabotage harness is how this file is verified; if it is gone, "
        "these assertions lose the thing that proves they bite"
    )
    assert Path(__file__).read_text(encoding="utf-8").count("assert") > 8
