"""Tests for Sørensen-Dice overlap implementation and threshold calibration.

Verifies _compute_overlap() and _compute_stemmed_overlap() behave correctly
for equal-length, short-vs-long, boundary cases, and stopword-heavy inputs.
Added as part of Round 6 council audit (Dice impact analysis).
"""

from divineos.core.constants import (
    OVERLAP_DUPLICATE,
    OVERLAP_NEAR_IDENTICAL,
    OVERLAP_QUASI_IDENTICAL,
    OVERLAP_RELATIONSHIP,
    OVERLAP_STRONG,
)
from divineos.core.knowledge._text import (
    _compute_overlap,
    _compute_stemmed_overlap,
    _stem,
    _stemmed_word_set,
)


class TestDiceFormulaBasics:
    """Verify Sørensen-Dice formula: 2*|intersection|/(|A|+|B|)."""

    def test_identical_texts(self):
        assert _compute_overlap("hello world test", "hello world test") == 1.0

    def test_no_overlap(self):
        assert _compute_overlap("alpha beta gamma", "delta epsilon zeta") == 0.0

    def test_empty_text(self):
        assert _compute_overlap("", "hello world") == 0.0
        assert _compute_overlap("hello world", "") == 0.0
        assert _compute_overlap("", "") == 0.0

    def test_symmetric(self):
        """Dice must produce the same score regardless of argument order."""
        a = "database migration schema update"
        b = "database schema validation rules"
        assert _compute_overlap(a, b) == _compute_overlap(b, a)

    def test_all_stopwords_returns_zero(self):
        """Text that reduces to nothing after stopword removal scores 0."""
        assert _compute_overlap("the is a to of", "the is a to of and but") == 0.0


class TestDiceLengthMismatch:
    """Dice correctly penalizes length mismatch — the whole point of the migration."""

    def test_equal_length_high_overlap(self):
        # "tool" is a stopword, so 4 words vs 4 words, 2 overlap: 2*2/8 = 0.50
        result = _compute_overlap(
            "database migration schema update tool",
            "database schema validation rules tool",
        )
        assert 0.45 < result < 0.55

    def test_short_vs_medium_full_overlap(self):
        # Short text fully contained in longer text should NOT score 1.0
        # Under old min-denom it would be 1.0; Dice correctly lowers it
        result = _compute_overlap(
            "always commit work",
            "always commit work before switching branches avoid losing changes",
        )
        assert result < 0.80  # Dice penalizes length mismatch
        assert result > 0.30  # But still recognizes the overlap

    def test_extreme_length_mismatch(self):
        # 2 meaningful words vs 20+ meaningful words, 2 overlap
        short = "run tests"
        long = (
            "database migration schema update tool validation "
            "deployment configuration logging monitoring testing "
            "architecture patterns integration benchmarks performance "
            "run tests verification pipeline automation"
        )
        result = _compute_overlap(short, long)
        assert result < 0.25  # Heavily penalized by length mismatch

    def test_single_word_vs_long(self):
        # 1 word vs many: should be very low
        result = _compute_overlap(
            "testing",
            "database migration schema update validation deployment testing",
        )
        assert result < 0.30  # Below OVERLAP_RELATIONSHIP


class TestDiceThresholdBoundaries:
    """Verify real-world text pairs cross the right thresholds."""

    def test_lesson_vs_knowledge_above_duplicate(self):
        """A lesson and its corresponding knowledge should exceed OVERLAP_DUPLICATE."""
        lesson = "commit work before switching branches"
        knowledge = "always commit work before switching branches to avoid losing changes"
        result = _compute_overlap(lesson, knowledge)
        assert result >= OVERLAP_DUPLICATE, (
            f"Lesson-knowledge pair scored {result:.3f}, "
            f"below OVERLAP_DUPLICATE ({OVERLAP_DUPLICATE})"
        )

    def test_related_topics_above_relationship(self):
        """Related knowledge should exceed OVERLAP_RELATIONSHIP."""
        a = "testing coverage improves code quality"
        b = "code quality requires testing every module"
        result = _compute_overlap(a, b)
        assert result >= OVERLAP_RELATIONSHIP

    def test_unrelated_below_relationship(self):
        """Unrelated knowledge should be below OVERLAP_RELATIONSHIP."""
        a = "database migration schema update"
        b = "emotional awareness during difficult conversations"
        result = _compute_overlap(a, b)
        assert result < OVERLAP_RELATIONSHIP

    def test_near_identical_above_threshold(self):
        """Near-identical texts should exceed OVERLAP_NEAR_IDENTICAL."""
        a = "always run full test suite before committing code changes"
        b = "always run full test suite before committing code"
        result = _compute_overlap(a, b)
        assert result >= OVERLAP_NEAR_IDENTICAL


class TestStemmedOverlapMatchesDice:
    """_compute_stemmed_overlap must use Dice, not min-denominator."""

    def test_uses_dice_not_min_denom(self):
        """The critical test: stemmed overlap must match Dice formula."""
        # 3 words vs 6 words, all 3 match
        # Dice: 2*3/(3+6) = 0.667
        # Old min-denom: 3/3 = 1.0
        a = {"test", "deploy", "valid"}
        b = {"test", "deploy", "valid", "config", "monitor", "schema"}
        result = _compute_stemmed_overlap(a, b)
        expected = 2 * 3 / (3 + 6)  # 0.667
        assert abs(result - expected) < 0.01, (
            f"Got {result:.3f}, expected {expected:.3f}. "
            f"If result is 1.0, the function still uses min-denominator!"
        )

    def test_symmetric(self):
        a = {"alpha", "beta", "gamma"}
        b = {"beta", "gamma", "delta", "epsilon"}
        assert _compute_stemmed_overlap(a, b) == _compute_stemmed_overlap(b, a)

    def test_empty_sets(self):
        assert _compute_stemmed_overlap(set(), {"a", "b"}) == 0.0
        assert _compute_stemmed_overlap({"a", "b"}, set()) == 0.0

    def test_identical_sets(self):
        s = {"test", "deploy", "valid"}
        assert _compute_stemmed_overlap(s, s) == 1.0


class TestStemmingBehavior:
    """Verify stemming collapses word forms correctly."""

    def test_verb_forms_collapse(self):
        # _stem is a simple suffix stripper, not a full lemmatizer
        # "tested" and "tests" both stem to "test", but "testing" stems to "tes"
        assert _stem("tested") == _stem("tests")
        assert _stem("validated") == _stem("validates")

    def test_stemmed_word_set_removes_stopwords(self):
        words = _stemmed_word_set("I should always run the tests before committing")
        # "I", "should", "the", "before" are stopwords
        assert "i" not in words
        assert "the" not in words

    def test_stemmed_overlap_catches_variants(self):
        """Stemmed overlap finds matches that raw overlap misses."""
        a = _stemmed_word_set("testing validation deployment")
        b = _stemmed_word_set("tested validated deployed")
        stemmed_score = _compute_stemmed_overlap(a, b)
        raw_score = _compute_overlap(
            "testing validation deployment",
            "tested validated deployed",
        )
        # Stemmed should find matches, raw should not
        assert stemmed_score > raw_score


class TestThresholdConstants:
    """Verify threshold ordering and values are sane for Dice."""

    def test_threshold_ordering(self):
        assert OVERLAP_RELATIONSHIP < OVERLAP_DUPLICATE
        assert OVERLAP_DUPLICATE < OVERLAP_STRONG
        assert OVERLAP_STRONG < OVERLAP_QUASI_IDENTICAL
        assert OVERLAP_QUASI_IDENTICAL < OVERLAP_NEAR_IDENTICAL

    def test_thresholds_calibrated_for_dice(self):
        """All thresholds should be reachable for common length ratios."""
        # 5-word vs 10-word, all 5 match: Dice = 2*5/15 = 0.667
        # This should exceed OVERLAP_STRONG (0.40)
        assert 0.667 > OVERLAP_STRONG

        # 3-word vs 10-word, all 3 match: Dice = 2*3/13 = 0.462
        # This should exceed OVERLAP_DUPLICATE (0.30)
        assert 0.462 > OVERLAP_DUPLICATE

        # 2-word vs 10-word, both match: Dice = 2*2/12 = 0.333
        # This should exceed OVERLAP_RELATIONSHIP (0.25)
        assert 0.333 > OVERLAP_RELATIONSHIP
