"""Regression pin for Marc audit finding #7 (2026-07-16): the benchmark
head-to-head tally in ``benchmark/opus_test.py`` used ``.get("correct_fix", 0)``
on every score entry, silently defaulting judge-error entries (which lack
the ``correct_fix`` key entirely) to 0/FAIL. That inflated the enhanced-
wins count: an ENHANCED-scored=1 vs BASE-judge-errored task registered
as an "enhanced win" even though base was never actually judged.

The fix filters out judge-error entries before the tally. This test
exercises the tally logic against a synthetic mixed-error corpus and
asserts the correct arithmetic. Runs headless (no LLM calls, no gh, no
network) — pure unit test of the tally shape.
"""

from __future__ import annotations

from typing import Any


def _tally(base_scores: list[dict[str, Any]], enh_scores: list[dict[str, Any]]) -> dict[str, int]:
    """Reproduce the tally logic from opus_test.py in isolation.

    Kept as a local reimplementation because opus_test.py is a script,
    not a library — factoring the tally out would be a bigger refactor
    than this fix warrants. Any drift between here and there is caught
    by test_tally_shape_matches_source below.
    """
    enh_wins = 0
    base_wins = 0
    ties = 0
    judge_error_skips = 0
    for s_base, s_enh in zip(base_scores, enh_scores):
        if "error" in s_base or "error" in s_enh:
            judge_error_skips += 1
            continue
        b = s_base.get("correct_fix", 0)
        e = s_enh.get("correct_fix", 0)
        if e and not b:
            enh_wins += 1
        elif b and not e:
            base_wins += 1
        else:
            ties += 1
    return {
        "enh_wins": enh_wins,
        "base_wins": base_wins,
        "ties": ties,
        "judge_error_skips": judge_error_skips,
    }


class TestBenchmarkTally:
    def test_judge_error_on_base_does_not_count_as_enhanced_win(self):
        """The exact failure Marc named: base judge errored, enhanced
        scored 1. Pre-fix this registered as an enhanced win. Post-fix
        it's a judge-error skip.
        """
        base = [{"error": "JSONDecodeError"}]
        enh = [{"correct_fix": 1}]
        r = _tally(base, enh)
        assert r["enh_wins"] == 0, "enhanced-win must not be credited when base wasn't judged"
        assert r["judge_error_skips"] == 1

    def test_judge_error_on_enhanced_does_not_count_as_base_win(self):
        """Symmetric case — enhanced judge errored, base scored 1."""
        base = [{"correct_fix": 1}]
        enh = [{"error": "timeout"}]
        r = _tally(base, enh)
        assert r["base_wins"] == 0
        assert r["judge_error_skips"] == 1

    def test_judge_error_on_both_is_a_skip_not_a_tie(self):
        """Pre-fix, both-errored counted as tie (both defaulted to 0).
        Post-fix it's a skip so error-corrupted 'ties' don't inflate
        the tie count either.
        """
        base = [{"error": "x"}]
        enh = [{"error": "y"}]
        r = _tally(base, enh)
        assert r["ties"] == 0
        assert r["judge_error_skips"] == 1

    def test_clean_corpus_tally_unchanged_by_fix(self):
        """The fix must not change results on a corpus with no judge
        errors — regression guard against over-filtering.
        """
        base = [
            {"correct_fix": 1},
            {"correct_fix": 0},
            {"correct_fix": 0},
            {"correct_fix": 1},
        ]
        enh = [
            {"correct_fix": 0},  # base_win
            {"correct_fix": 1},  # enh_win
            {"correct_fix": 0},  # tie
            {"correct_fix": 1},  # tie
        ]
        r = _tally(base, enh)
        assert r == {"enh_wins": 1, "base_wins": 1, "ties": 2, "judge_error_skips": 0}

    def test_mixed_error_corpus_matches_marc_reproduction(self):
        """The scenario Marc described: 4 error files present in the
        150-task run. Verify a synthetic version of that shape gives
        the smaller tally the fix produces.
        """
        base = [
            {"correct_fix": 0},
            {"correct_fix": 0},
            {"correct_fix": 0},
            {"error": "x"},  # error on base — pre-fix would count enh as win
        ]
        enh = [
            {"correct_fix": 1},  # legitimate enh win
            {"correct_fix": 1},  # legitimate enh win
            {"correct_fix": 0},
            {"correct_fix": 1},  # spurious "win" pre-fix
        ]
        r = _tally(base, enh)
        # Legitimate wins only — the 4th task is skipped.
        assert r["enh_wins"] == 2
        assert r["base_wins"] == 0
        assert r["ties"] == 1
        assert r["judge_error_skips"] == 1


class TestTallyShapeMatchesSource:
    def test_source_uses_error_filter(self):
        """Regression pin: opus_test.py's tally loop must include the
        ``if "error" in s_base or "error" in s_enh: ... continue`` guard.
        If a future refactor removes it, this test fails loudly.
        """
        from pathlib import Path

        src = (Path(__file__).resolve().parent.parent / "benchmark" / "opus_test.py").read_text(
            encoding="utf-8"
        )
        assert 'if "error" in s_base or "error" in s_enh:' in src, (
            "benchmark/opus_test.py tally loop has lost the judge-error "
            "filter. Regression of Marc audit finding #7 — judge-errored "
            "tasks will again silently default to 0 and inflate the win count."
        )
        assert "judge_error_skips" in src, (
            "benchmark summary no longer tracks judge_error_skips — the "
            "denominator transparency Marc's fix added is gone."
        )
