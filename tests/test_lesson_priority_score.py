"""Tests for SM-2-style lesson priority scoring (prereg-10c34b72e90a).

The briefing's lesson block was sorting by pure recency, which meant a
one-time freshly-seen lesson outranked an 8-occurrence-with-regressions
lesson that hadn't ticked in a few days. Spaced-repetition logic flips
that: high-recurrence + high-regression lessons surface MORE often than
quiet one-offs, and stale lessons with no recent regressions fade.

These tests pin the ranking invariants so future tuning of the
hyper-parameters doesn't silently break the qualitative ordering.
"""

import time

from divineos.core.knowledge.lessons import lesson_priority_score


def _lesson(occurrences=1, regressions=0, last_seen=None, status="active"):
    """Build a minimal lesson dict for scoring tests."""
    if last_seen is None:
        last_seen = time.time()
    return {
        "occurrences": occurrences,
        "regressions": regressions,
        "last_seen": last_seen,
        "status": status,
    }


class TestSpacedRepetitionRanking:
    def test_high_regression_outranks_freshly_seen(self):
        """The core inversion: a recurring lesson with regressions
        should outrank a one-off lesson seen seconds ago."""
        now = time.time()
        recurring = _lesson(occurrences=8, regressions=5, last_seen=now - 3 * 86400)
        fresh_oneoff = _lesson(occurrences=1, regressions=0, last_seen=now)
        assert lesson_priority_score(recurring, now) > lesson_priority_score(fresh_oneoff, now)

    def test_regressions_weighted_higher_than_occurrences(self):
        """Two lessons same age, one has more regressions — that one wins
        even if total events are equal. Regressions are stronger signal
        than occurrences because they mean the lesson keeps coming back
        after being thought-resolved."""
        now = time.time()
        more_regressions = _lesson(occurrences=2, regressions=3, last_seen=now)
        more_occurrences = _lesson(occurrences=5, regressions=0, last_seen=now)
        assert lesson_priority_score(more_regressions, now) > lesson_priority_score(
            more_occurrences, now
        )

    def test_recency_decay_shrinks_old_lessons(self):
        """Same lesson, two ages: the older copy scores lower.
        Without this, lessons would never fade and the briefing would
        accumulate stale entries indefinitely."""
        now = time.time()
        recent = _lesson(occurrences=3, regressions=1, last_seen=now)
        old = _lesson(occurrences=3, regressions=1, last_seen=now - 60 * 86400)
        assert lesson_priority_score(recent, now) > lesson_priority_score(old, now)

    def test_improving_status_penalizes_score(self):
        """Lessons marked 'improving' have a small priority dampener
        so genuinely-active recurring lessons surface ahead of ones
        the agent is already getting better at."""
        now = time.time()
        active = _lesson(occurrences=3, regressions=1, last_seen=now, status="active")
        improving = _lesson(occurrences=3, regressions=1, last_seen=now, status="improving")
        assert lesson_priority_score(active, now) > lesson_priority_score(improving, now)

    def test_score_is_non_negative(self):
        """Score floor: a lesson with zero everything should return 0,
        not negative. Negative scores would behave strangely in sort
        order and aren't semantically meaningful."""
        now = time.time()
        empty = _lesson(occurrences=0, regressions=0, last_seen=now)
        assert lesson_priority_score(empty, now) >= 0.0

    def test_handles_missing_fields_gracefully(self):
        """Real DB rows can have None values for some fields. The score
        function should not crash on partial data."""
        partial = {"description": "test"}  # no occurrences, regressions, last_seen, status
        # Should not raise; should return a finite number
        score = lesson_priority_score(partial, time.time())
        assert score >= 0.0


class TestRankingInversionVsRecency:
    """The whole point of the change: priority ordering differs from
    pure-recency ordering when the regression signal is strong."""

    def test_priority_inverts_recency_when_regressions_present(self):
        """Take three lessons. Under recency ordering, lesson C (most
        recent) wins. Under priority ordering, lesson A (high regressions
        despite being older) wins. This pins the qualitative inversion."""
        now = time.time()
        lesson_a = _lesson(occurrences=10, regressions=8, last_seen=now - 5 * 86400)
        lesson_b = _lesson(occurrences=2, regressions=0, last_seen=now - 2 * 86400)
        lesson_c = _lesson(occurrences=1, regressions=0, last_seen=now)

        recency_order = sorted(
            [lesson_a, lesson_b, lesson_c],
            key=lambda lesson: lesson["last_seen"],
            reverse=True,
        )
        priority_order = sorted(
            [lesson_a, lesson_b, lesson_c],
            key=lambda lesson: lesson_priority_score(lesson, now),
            reverse=True,
        )

        # Recency: C, B, A
        assert recency_order[0] is lesson_c
        # Priority: A first (high regressions outweigh age)
        assert priority_order[0] is lesson_a
