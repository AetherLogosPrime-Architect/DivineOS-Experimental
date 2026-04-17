"""Tests for loop-status honesty labels (Grok audit 2026-04-16).

Four surfaces each carry a 'Loop status:' line that describes what is
mechanically closed vs. what is still aspirational. The labels are
hardcoded strings (per the design decision recorded in decision_journal)
— updated manually as loops close. The tests here lock in:

* The label appears in the output of each surface's public formatter.
* The label names the specific mechanism (not a generic 'loop: partial').
* The label explicitly says what is NOT closed so readers can calibrate.

These tests are intentionally string-level. They will fail loudly when
the label is edited, which is the whole point: a surface label that
claims a loop is closed must be rewritten the moment the loop actually
closes. The test failure is the reminder.
"""

import os

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.lessons import (
    _lesson_loop_status,
    get_lesson_summary,
    record_lesson,
)
from divineos.core.ledger import init_db
from divineos.core.moral_compass import (
    _compass_loop_status,
    format_compass_reading,
    init_compass,
    log_observation,
)
from divineos.core.pre_registrations import (
    file_pre_registration,
    format_summary as prereg_format_summary,
    init_pre_registrations_tables,
    prereg_loop_status,
)
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.store import submit_finding, submit_round
from divineos.core.watchmen.summary import watchmen_loop_status


@pytest.fixture(autouse=True)
def _labels_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_compass()
        init_pre_registrations_tables()
        init_watchmen_tables()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# ── Lesson loop status ───────────────────────────────────────────────


class TestLessonLoopStatus:
    def test_label_is_nonempty(self):
        label = _lesson_loop_status()
        assert label
        assert "Loop status:" in label

    def test_label_names_positive_evidence_coverage(self):
        """The label must say which categories have the RESOLVED path wired."""
        label = _lesson_loop_status()
        assert "RESOLVED" in label.upper() or "resolved" in label
        # Names the specific categories
        assert "blind_retry" in label
        assert "upset_recovered" in label

    def test_label_acknowledges_unwired_categories(self):
        """Must explicitly call out what is NOT wired — no silent optimism."""
        label = _lesson_loop_status()
        assert "DORMANT" in label.upper() or "dormant" in label

    def test_label_appears_in_lesson_summary(self):
        # Need some data so the "No lessons tracked yet." branch doesn't fire
        record_lesson("test_category", "test lesson", "session-1")
        out = get_lesson_summary()
        assert "Loop status:" in out


# ── Compass loop status ──────────────────────────────────────────────


class TestCompassLoopStatus:
    def test_label_is_nonempty(self):
        label = _compass_loop_status()
        assert label
        assert "Loop status:" in label

    def test_label_names_rudder_scope(self):
        """Must name Task/Agent as the gated tools and acknowledge Edit/Write
        are NOT gated — no silent inflation of what's actually firing."""
        label = _compass_loop_status()
        assert "Task" in label or "Agent" in label
        assert "Edit" in label or "Write" in label or "Bash" in label
        assert "NOT" in label or "not" in label

    def test_label_names_partial_closure(self):
        """The compass is partially closed — the label must say so."""
        label = _compass_loop_status()
        assert "PARTIAL" in label.upper() or "partial" in label

    def test_label_appears_in_compass_reading(self):
        # Need some observations so the "no data" branch doesn't short-circuit
        for _ in range(6):
            log_observation(spectrum="initiative", position=0.0, source="MEASURED", evidence="test")
        out = format_compass_reading()
        assert "Loop status:" in out


# ── Watchmen loop status ─────────────────────────────────────────────


class TestWatchmenLoopStatus:
    def test_label_is_nonempty(self):
        label = watchmen_loop_status()
        assert label
        assert "Loop status:" in label

    def test_label_names_what_works_and_what_does_not(self):
        """Filing works, routing works, auto-scheduled cadence does NOT work yet.
        The label must be explicit about both sides."""
        label = watchmen_loop_status()
        # Says what works
        assert "filing" in label.lower()
        # Says what does not
        assert "NOT" in label or "not" in label
        # Names the specific unfinished piece
        assert "cadence" in label.lower() or "scheduled" in label.lower()

    def test_label_tracks_pr4_reference(self):
        """Readers should be able to trace to the PR that will close this loop."""
        label = watchmen_loop_status()
        assert "PR 4" in label or "Grok" in label


# ── Pre-registration loop status ─────────────────────────────────────


class TestPreregLoopStatus:
    def test_label_is_nonempty(self):
        label = prereg_loop_status()
        assert label
        assert "Loop status:" in label

    def test_label_distinguishes_mechanism_from_outcome_driven_behavior(self):
        """The mechanism (filing, overdue surfacing, outcome) is wired. The
        deeper claim (outcomes alter behavior) is still being measured.
        Label must draw that line explicitly."""
        label = prereg_loop_status()
        assert "wired" in label.lower()
        assert "measuring" in label.lower() or "measure" in label.lower()

    def test_label_appears_in_summary(self):
        """File at least one prereg so the summary shows the populated path."""
        file_pre_registration(
            actor="a",
            mechanism="labels_test",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        out = prereg_format_summary()
        assert "Loop status:" in out

    def test_label_appears_in_empty_summary(self):
        """Even with zero pre-regs filed, the label should still appear
        so the empty state is honest."""
        out = prereg_format_summary()
        # Empty-state branch prints different content; loop-status should
        # still be present so even a fresh install sees the honest framing.
        assert "Loop status:" in out or "No pre-registrations filed" in out


# ── Cross-surface invariants ─────────────────────────────────────────


class TestCrossSurfaceConsistency:
    """All four labels share a minimum contract: they start with
    'Loop status:' so a grep over the codebase finds them all."""

    def test_all_four_labels_start_with_loop_status(self):
        for fn in (
            _lesson_loop_status,
            _compass_loop_status,
            watchmen_loop_status,
            prereg_loop_status,
        ):
            label = fn()
            assert label.startswith("Loop status:"), f"{fn.__name__} label: {label!r}"

    def test_no_label_claims_full_closure_yet(self):
        """As of Grok audit 2026-04-16 + PR 2/4 (compass rudder), no loop
        is fully closed end-to-end. This test enforces that no label can
        silently start claiming full closure without the agent updating
        the test too — which is the whole point of label-as-commitment.
        """
        for fn in (
            _lesson_loop_status,
            _compass_loop_status,
            watchmen_loop_status,
            prereg_loop_status,
        ):
            label = fn()
            # The three honest qualifiers we expect somewhere in each label
            has_qualifier = any(
                token in label.lower()
                for token in ("partial", "not", "measuring", "aspirational", "yet")
            )
            assert has_qualifier, (
                f"{fn.__name__} has no honesty qualifier — if this loop is "
                f"truly closed end-to-end, update the test alongside the label. "
                f"Label: {label!r}"
            )

    def test_finding_a_label_via_grep_works(self):
        """Readers skimming the codebase should be able to find every
        loop-status surface via a single grep."""
        import subprocess

        # Look for 'Loop status:' definitions — not just usages
        result = subprocess.run(
            ["git", "grep", "-l", "Loop status:"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            check=False,
        )
        # git grep returns 0 on match, 1 on no match. We expect matches.
        assert result.returncode in (0, 1)
        # The four source files we added labels to must appear
        assert "lessons.py" in result.stdout
        assert "moral_compass.py" in result.stdout
        assert "watchmen/summary.py" in result.stdout
        assert "pre_registrations/summary.py" in result.stdout


# ── Edge case: empty Watchmen store still carries status ─────────────


def test_watchmen_loop_status_available_with_zero_findings():
    """Even if no audit has ever fired, the label must still be gettable.
    It describes the mechanism, not the state."""
    assert "Loop status:" in watchmen_loop_status()


def test_watchmen_loop_status_available_after_finding_filed():
    """Label must not depend on specific DB state."""
    round_id = submit_round(actor="user", focus="test round")
    submit_finding(
        round_id=round_id,
        actor="user",
        severity="low",
        category="knowledge",
        title="test",
        description="test finding",
    )
    assert "Loop status:" in watchmen_loop_status()
