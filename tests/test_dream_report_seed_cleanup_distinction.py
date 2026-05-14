"""Regression-pin tests for dream-report seed-cleanup distinction
(Aletheia round-ba785844a791 Finding 30).

The bug-shape: auto_resolve_lessons handles two distinct cases under
the same return shape — (1) seeded placeholders that never fired
(noise cleanup), and (2) improving lessons that earned resolution
through positive evidence. The dream report previously listed both
under "Lessons resolved" indistinguishably; operator couldn't tell
whether N marked resolved meant N real merges or N seed cleanups.

Fix: each transition is marked with ``_transition_origin`` —
"seed_cleanup", "evidence_resolved", "evidence_resolved_with_history",
or "dormant_cooldown". The dream report splits seed_cleanup into its
own field and labels it clearly.

If these tests fail, the seed-vs-real distinction has been removed
and the report has reverted to lumping noise-removal with real
resolution.
"""

from __future__ import annotations

import time

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.lessons import (
    STATUS_ACTIVE,
    auto_resolve_lessons,
    record_lesson,
)


def test_seeded_placeholder_marked_seed_cleanup_origin() -> None:
    """LOAD-BEARING: when auto_resolve_lessons resolves a (seeded)
    placeholder, the returned dict carries
    _transition_origin='seed_cleanup' so callers can distinguish noise
    cleanup from real resolution."""
    init_knowledge_table()

    # Insert a (seeded) lesson directly (occ=1)
    record_lesson(
        category="test_seed_cleanup_cat",
        description="(seeded) placeholder lesson for regression-pin",
        session_id="test-seed-session",
    )

    transitions = auto_resolve_lessons()

    # Find our transitioned lesson
    matching = [
        t for t in transitions if t.get("category") == "test_seed_cleanup_cat"
    ]
    assert matching, (
        "Seeded placeholder was not transitioned by auto_resolve_lessons. "
        "Either Phase 1 (seed cleanup) regressed or the test setup is wrong."
    )
    transitioned = matching[0]
    assert transitioned.get("_transition_origin") == "seed_cleanup", (
        f"Seeded transition has _transition_origin={transitioned.get('_transition_origin')!r}; "
        "expected 'seed_cleanup'. The marker has regressed; dream report "
        "will lump seed cleanup with real resolution again."
    )


def test_dream_report_distinguishes_seed_cleanup_from_evidence_resolution() -> None:
    """LOAD-BEARING: DreamReport's render output distinguishes seeded-
    placeholder cleanup ("Seed placeholders cleaned") from evidence-
    based resolution ("Lessons resolved (evidence-based)"). If the
    labels merge again, the operator-facing display reverts to the
    misleading lumped state Finding 30 named."""
    from divineos.core.sleep import DreamReport

    report = DreamReport(duration_seconds=1.0)
    report.lessons_resolved = ["real_lesson_alpha", "real_lesson_beta"]
    report.lessons_resolved_seed_cleanup = ["seeded_lesson_gamma"]

    rendered = report.summary()
    # Real resolution line is distinct
    assert "evidence-based" in rendered, (
        "Dream report no longer labels real-resolution as evidence-based. "
        "The label distinction has been removed; seed-cleanup will look "
        "identical to real resolution again."
    )
    # Seed-cleanup line is distinct
    assert (
        "Seed placeholders cleaned" in rendered
        or "NOT earned resolution" in rendered
    ), (
        "Dream report no longer surfaces a separate line for seed-cleanup. "
        "Restore the lessons_resolved_seed_cleanup display block."
    )
    assert "real_lesson_alpha" in rendered
    assert "seeded_lesson_gamma" in rendered


def test_dream_report_dataclass_has_seed_cleanup_field() -> None:
    """The DreamReport must have a lessons_resolved_seed_cleanup field.
    Pin against accidental removal of the field that closes Finding 30."""
    from divineos.core.sleep import DreamReport

    report = DreamReport(duration_seconds=0.0)
    assert hasattr(report, "lessons_resolved_seed_cleanup"), (
        "DreamReport no longer has lessons_resolved_seed_cleanup field. "
        "Finding 30 distinction removed."
    )
    assert report.lessons_resolved_seed_cleanup == []


def test_empty_lessons_dont_surface_in_report() -> None:
    """When no lessons resolved (real OR seed), neither line should
    appear in the rendered report."""
    from divineos.core.sleep import DreamReport

    report = DreamReport(duration_seconds=1.0)
    # All lesson lists empty
    rendered = report.summary()
    assert "evidence-based" not in rendered
    assert "Seed placeholders cleaned" not in rendered
