"""Tests for the gravity classifier — deterministic gate-fire scoring.

The classifier decides WHEN the substrate-modification gate and the
cognitive-value (oscillating-read) gate fire. It is rule-based and
deterministic over observable features — so the tests pin exact
feature-firing and the two thresholds, the behavior the rest of the
gate machinery trusts.

Untested at ship; closed 2026-05-23 while working down the
unfinished-mechanism backlog the repaired initiative dial surfaced.
"""

from divineos.core.gravity_classifier import (
    CognitiveValueGravity,
    SubstrateModGravity,
    borderline_indicator_cognitive,
    borderline_indicator_substrate,
    score_cognitive_value,
    score_substrate_modification,
)


class TestSubstrateModificationFeatures:
    def test_git_commit_fires(self):
        r = score_substrate_modification("Bash", bash_command="git commit -m 'x'")
        assert "git-commit" in r.fired_features
        assert r.is_high_gravity

    def test_git_status_does_not_fire(self):
        r = score_substrate_modification("Bash", bash_command="git status")
        assert r.score == 0
        assert not r.is_high_gravity

    def test_edit_src_divineos_fires(self):
        r = score_substrate_modification("Edit", file_paths=("src/divineos/core/foo.py",))
        assert "edit-src-divineos" in r.fired_features
        assert r.is_high_gravity

    def test_edit_outside_src_does_not_fire_src_feature(self):
        r = score_substrate_modification("Edit", file_paths=("README.md",))
        assert "edit-src-divineos" not in r.fired_features

    def test_edit_hooks_fires_guardrail(self):
        r = score_substrate_modification("Write", file_paths=(".claude/hooks/some-hook.sh",))
        assert "edit-guardrail" in r.fired_features

    def test_edit_check_script_fires_guardrail(self):
        r = score_substrate_modification("Edit", file_paths=("scripts/check_push_readiness.py",))
        assert "edit-guardrail" in r.fired_features

    def test_edit_guardrail_files_list_fires(self):
        r = score_substrate_modification("Edit", file_paths=("scripts/guardrail_files.txt",))
        assert "edit-guardrail" in r.fired_features

    def test_substrate_write_cli_fires(self):
        for sub in ("audit", "claim", "learn", "prereg", "decide", "feel", "journal"):
            r = score_substrate_modification("Bash", bash_command=f"divineos {sub} x")
            assert "substrate-write-cli" in r.fired_features, sub

    def test_compass_ops_fires_substrate_write(self):
        r = score_substrate_modification(
            "Bash", bash_command="divineos compass-ops observe initiative -p 0.1 -e x"
        )
        assert "substrate-write-cli" in r.fired_features

    def test_readonly_cli_does_not_fire(self):
        r = score_substrate_modification("Bash", bash_command="divineos briefing")
        assert r.score == 0

    def test_kiln_layer_edit_fires(self):
        r = score_substrate_modification("Write", file_paths=("docs/foundational_truths.md",))
        assert "edit-kiln-layer" in r.fired_features

    def test_seed_json_fires_kiln(self):
        r = score_substrate_modification("Edit", file_paths=("src/divineos/seed.json",))
        assert "edit-kiln-layer" in r.fired_features

    def test_consolidation_cli_fires(self):
        for sub in ("extract", "sleep"):
            r = score_substrate_modification("Bash", bash_command=f"divineos {sub}")
            assert "consolidation-cli" in r.fired_features, sub

    def test_windows_backslash_paths_normalized(self):
        r = score_substrate_modification("Edit", file_paths=(r"src\divineos\core\foo.py",))
        assert "edit-src-divineos" in r.fired_features

    def test_multiple_features_sum(self):
        # A kiln-layer file also lives under src/divineos/ → two features.
        r = score_substrate_modification("Edit", file_paths=("src/divineos/seed.json",))
        assert r.score >= 2
        assert "edit-src-divineos" in r.fired_features
        assert "edit-kiln-layer" in r.fired_features

    def test_returns_dataclass(self):
        r = score_substrate_modification("Read", file_paths=("x.py",))
        assert isinstance(r, SubstrateModGravity)
        assert r.score == 0
        assert not r.is_high_gravity


class TestCognitiveValueScoring:
    def test_empty_content_is_low_gravity(self):
        r = score_cognitive_value("")
        assert r.score == 0.0
        assert not r.is_high_gravity

    def test_returns_dataclass_with_feature_scores(self):
        r = score_cognitive_value("hello")
        assert isinstance(r, CognitiveValueGravity)
        assert set(r.feature_scores) == {
            "char",
            "header",
            "path",
            "composition",
            "codeblock",
        }

    def test_long_dense_doc_in_core_path_is_high_gravity(self):
        content = (
            "# Design\n\nThis architecture integrates a framework and a "
            "methodology, decompose the principle into a lens.\n\n"
            "## Section\n\n" + ("word " * 500)
        )
        r = score_cognitive_value(content, source_path="src/divineos/core/foo.py")
        assert r.is_high_gravity
        assert r.score >= 0.3

    def test_path_bonus_for_priority_dirs(self):
        for p in ("exploration/x.md", "docs/y.md", "family/letters/z.md"):
            r = score_cognitive_value("text", source_path=p)
            assert r.feature_scores["path"] == 1.0, p

    def test_path_bonus_partial_for_secondary_dirs(self):
        r = score_cognitive_value("text", source_path="scripts/x.sh")
        # 0.1 raw / 0.3 max ≈ 0.333
        assert 0.3 < r.feature_scores["path"] < 0.4

    def test_no_path_bonus_for_unknown_dir(self):
        r = score_cognitive_value("text", source_path="/tmp/random.txt")
        assert r.feature_scores["path"] == 0.0

    def test_composition_markers_raise_composition_score(self):
        plain = score_cognitive_value("the cat sat on the mat there")
        dense = score_cognitive_value("design architecture principle lens")
        assert dense.feature_scores["composition"] > plain.feature_scores["composition"]

    def test_header_density_counts_markdown_headers(self):
        r = score_cognitive_value("# A\n## B\n### C\ntext")
        assert r.feature_scores["header"] > 0.0

    def test_codeblock_density_counts_fences(self):
        r = score_cognitive_value("text\n```\ncode\n```\nmore")
        assert r.feature_scores["codeblock"] > 0.0

    def test_char_score_increases_with_length(self):
        short = score_cognitive_value("hi")
        long = score_cognitive_value("x" * 5000)
        assert long.feature_scores["char"] > short.feature_scores["char"]

    def test_all_feature_scores_bounded_0_1(self):
        content = ("# H\n```\nc\n```\n" + "design framework lens " * 200) * 3
        r = score_cognitive_value(content, source_path="docs/big.md")
        for name, val in r.feature_scores.items():
            assert 0.0 <= val <= 1.0, f"{name}={val} out of [0,1]"
        assert 0.0 <= r.score <= 1.0


class TestSubstrateBorderlineIndicator:
    """Task #111 (2026-06-09): borderline-zone surface helper for
    substrate-modification-gravity. Classifies the routing decision shape
    so the gate-fire surface can name fragile single-feature fires
    distinctly from well-supported multi-feature fires."""

    def test_no_fire_returns_no_fire(self):
        r = SubstrateModGravity(score=0, fired_features=(), is_high_gravity=False)
        assert borderline_indicator_substrate(r) == "no-fire"

    def test_single_feature_returns_borderline(self):
        r = SubstrateModGravity(score=1, fired_features=("git-commit",), is_high_gravity=True)
        assert borderline_indicator_substrate(r) == "borderline-single-feature"

    def test_two_features_returns_strong(self):
        r = SubstrateModGravity(
            score=2,
            fired_features=("git-commit", "src-write"),
            is_high_gravity=True,
        )
        assert borderline_indicator_substrate(r) == "strong-multi-feature"

    def test_real_git_commit_classified_borderline(self):
        """End-to-end: a git commit by itself fires only the git-commit
        feature; the indicator names that fragility."""
        r = score_substrate_modification("Bash", bash_command="git commit -m 'x'")
        assert borderline_indicator_substrate(r) == "borderline-single-feature"


class TestCognitiveBorderlineIndicator:
    """Task #111: borderline-zone surface for cognitive-value-gravity.
    Threshold = 0.3, radius = 0.10, so:
      score < 0.20 -> clearly-low
      0.20 <= score < 0.30 -> borderline-low
      0.30 <= score < 0.40 -> borderline-high
      score >= 0.40 -> clearly-high
    """

    def _make(self, score: float) -> CognitiveValueGravity:
        return CognitiveValueGravity(
            score=score,
            feature_scores={"char": score},
            is_high_gravity=score >= 0.30,
        )

    def test_clearly_low(self):
        assert borderline_indicator_cognitive(self._make(0.05)) == "clearly-low"
        assert borderline_indicator_cognitive(self._make(0.19)) == "clearly-low"

    def test_borderline_low(self):
        assert borderline_indicator_cognitive(self._make(0.20)) == "borderline-low"
        assert borderline_indicator_cognitive(self._make(0.29)) == "borderline-low"

    def test_borderline_high(self):
        assert borderline_indicator_cognitive(self._make(0.30)) == "borderline-high"
        assert borderline_indicator_cognitive(self._make(0.39)) == "borderline-high"

    def test_clearly_high(self):
        assert borderline_indicator_cognitive(self._make(0.40)) == "clearly-high"
        assert borderline_indicator_cognitive(self._make(0.95)) == "clearly-high"

    def test_boundary_values(self):
        assert borderline_indicator_cognitive(self._make(0.30)) == "borderline-high"
        assert borderline_indicator_cognitive(self._make(0.40)) == "clearly-high"
