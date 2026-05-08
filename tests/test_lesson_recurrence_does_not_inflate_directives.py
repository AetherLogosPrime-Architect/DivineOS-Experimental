"""Regression test for audit round 20 finding: lesson recurrence used to
inflate directive confidence (negative evidence as positive evidence).

The bug:
  ``record_lesson`` ran a "corroboration sweep" that boosted
  ``corroboration_count`` and called ``promote_maturity`` on every
  knowledge entry whose content matched the lesson's category text.
  Result: when the agent ignored a directive 7 times, the directive
  hit CONFIRMED maturity precisely because it failed 7 times — its
  failures were treated as positive evidence.

The fix:
  Delete the corroboration sweep entirely. Recurrence tracking still
  happens via the ``occurrences`` field on the lesson row; that's the
  right place for it. Directive confidence is no longer contaminated
  by lesson recurrences.

This test pins the invariant: filing the same recurring lesson
multiple times should NOT bump the corroboration_count of related
knowledge entries.
"""

from __future__ import annotations

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.crud import get_knowledge, store_knowledge
from divineos.core.knowledge.lessons import record_lesson


def _get_by_id(knowledge_id: str) -> dict | None:
    """Helper: fetch one knowledge entry by ID."""
    for entry in get_knowledge(limit=10000, include_superseded=True):
        if entry.get("knowledge_id") == knowledge_id:
            return entry
    return None


def test_record_lesson_does_not_inflate_directive_confidence_on_recurrence():
    """Recurring a lesson must NOT bump corroboration_count on
    knowledge entries whose content happens to match the category.
    record_lesson handles its own schema setup on first call."""
    init_knowledge_table()

    directive_id = store_knowledge(
        knowledge_type="DIRECTIVE",
        content="Always read files before editing. No blind edits ever.",
    )

    initial = _get_by_id(directive_id)
    assert initial is not None
    initial_corr = initial.get("corroboration_count", 0)
    initial_maturity = initial.get("maturity")

    # Record the lesson 10 times — the failure mode the audit caught
    for _ in range(10):
        record_lesson(
            category="no_blind_edits",
            description="I edited a file without reading it first.",
            session_id="test-session",
        )

    after = _get_by_id(directive_id)
    assert after is not None
    assert after.get("corroboration_count", 0) == initial_corr, (
        f"Directive corroboration inflated by lesson recurrence: "
        f"was {initial_corr}, now {after.get('corroboration_count', 0)}. "
        f"This means a FAILED directive is being credited as positive "
        f"evidence — the exact bug audit round 20 caught."
    )
    # And maturity must not have promoted from this signal alone
    assert after.get("maturity") == initial_maturity, (
        f"Directive maturity changed from {initial_maturity!r} to "
        f"{after.get('maturity')!r} after 10 lesson recurrences. The "
        f"recurrence sweep should have been deleted."
    )
