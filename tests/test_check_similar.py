"""Tests for check_similar — pre-build adjacency search."""

from __future__ import annotations

from divineos.core.check_similar import (
    SimilarMatch,
    _description_overlap,
    _jaccard,
    _tokenize,
    check_similar,
    format_matches,
)


class TestDescriptionOverlap:
    def test_full_overlap(self):
        assert _description_overlap({"a", "b"}, {"a", "b", "c"}) == 1.0

    def test_partial_overlap(self):
        # description has 4 tokens; 2 of them appear in the doc
        assert _description_overlap({"a", "b", "c", "d"}, {"a", "b", "x", "y"}) == 0.5

    def test_no_overlap(self):
        assert _description_overlap({"a"}, {"b"}) == 0.0

    def test_empty_description(self):
        assert _description_overlap(set(), {"a", "b"}) == 0.0

    def test_long_doc_does_not_punish(self):
        # The whole point of this metric: a long doc with all the
        # description's tokens shouldn't be punished by Jaccard's
        # large-union effect.
        desc = {"closure", "shape", "rest", "stasis"}
        doc = {"closure", "shape", "rest", "stasis"} | {f"extra_{i}" for i in range(50)}
        # Jaccard would be 4/54 = 0.074
        # Description overlap is 4/4 = 1.0
        assert _description_overlap(desc, doc) == 1.0
        assert _jaccard(desc, doc) < 0.1


class TestTokenize:
    def test_lowercases(self):
        assert "hello" in _tokenize("Hello World")

    def test_drops_stopwords(self):
        tokens = _tokenize("the quick brown fox")
        assert "the" not in tokens
        assert "quick" in tokens

    def test_drops_short_words(self):
        tokens = _tokenize("a bc def ghij")
        assert "ghij" in tokens
        assert "bc" not in tokens

    def test_drops_purely_numeric(self):
        # _WORD_RE only matches words starting with a letter
        tokens = _tokenize("module 2026 closure detector")
        assert "closure" in tokens
        assert "2026" not in tokens


class TestJaccard:
    def test_identical(self):
        s = {"a", "b", "c"}
        assert _jaccard(s, s) == 1.0

    def test_disjoint(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial(self):
        # {a,b,c} ∩ {b,c,d} = {b,c}; ∪ = {a,b,c,d}; jaccard = 2/4 = 0.5
        assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5

    def test_empty(self):
        assert _jaccard(set(), {"a"}) == 0.0


class TestCheckSimilar:
    def test_finds_adjacent_module(self, tmp_path):
        # Build a minimal fake repo with one module
        repo = tmp_path / "repo"
        core = repo / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "closure_shape_detector.py").write_text(
            '"""Closure-shape detector — catches rest-as-stasis trained-flinch.\n\n'
            "Lessons keep escaping the prose layer.\n"
            '"""\n',
            encoding="utf-8",
        )

        matches = check_similar(
            "detector for closure-shape language and rest-as-stasis",
            repo_root=repo,
            scan_paths=("src/divineos/core",),
        )
        assert any("closure_shape_detector" in m.path for m in matches)

    def test_no_match_returns_empty(self, tmp_path):
        repo = tmp_path / "repo"
        core = repo / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "unrelated.py").write_text(
            '"""Database connection pooling for Postgres."""\n',
            encoding="utf-8",
        )

        matches = check_similar(
            "language register and prose detector",
            repo_root=repo,
            scan_paths=("src/divineos/core",),
        )
        assert matches == []

    def test_skips_test_files(self, tmp_path):
        repo = tmp_path / "repo"
        core = repo / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "test_closure.py").write_text(
            '"""Tests for closure-shape detector."""\n', encoding="utf-8"
        )
        (core / "real_module.py").write_text(
            '"""Closure-shape detector — catches rest-as-stasis."""\n',
            encoding="utf-8",
        )

        matches = check_similar(
            "closure shape detector rest stasis",
            repo_root=repo,
            scan_paths=("src/divineos/core",),
        )
        assert all("test_" not in m.path for m in matches)
        assert any("real_module" in m.path for m in matches)

    def test_includes_bash_scripts(self, tmp_path):
        repo = tmp_path / "repo"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "check_branch_freshness.sh").write_text(
            "#!/bin/bash\n"
            "# check_branch_freshness — block pushing a branch whose base is stale.\n"
            "# Detects silent-revert pattern from PR #199.\n",
            encoding="utf-8",
        )

        matches = check_similar(
            "branch health stale base silent revert",
            repo_root=repo,
            scan_paths=("scripts",),
        )
        assert any("check_branch_freshness" in m.path for m in matches)

    def test_results_sorted_by_score(self, tmp_path):
        repo = tmp_path / "repo"
        core = repo / "src" / "divineos" / "core"
        core.mkdir(parents=True)
        (core / "high_overlap.py").write_text(
            '"""Closure shape detector for rest as stasis stopping."""\n',
            encoding="utf-8",
        )
        (core / "low_overlap.py").write_text(
            '"""Detector for stopping conditions in numerical loops."""\n',
            encoding="utf-8",
        )

        matches = check_similar(
            "closure shape rest stasis stopping",
            repo_root=repo,
            scan_paths=("src/divineos/core",),
        )
        if len(matches) >= 2:
            assert matches[0].score >= matches[1].score


class TestFormatMatches:
    def test_format_no_matches(self):
        out = format_matches([])
        assert "additive" in out.lower()

    def test_format_with_matches(self):
        matches = [
            SimilarMatch("core/foo.py", 0.5, "Some module description"),
        ]
        out = format_matches(matches)
        assert "core/foo.py" in out
        assert "0.50" in out
        assert "Some module description" in out
