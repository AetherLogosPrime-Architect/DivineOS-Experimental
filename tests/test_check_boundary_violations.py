"""Tests for scripts/check_boundary_violations.py.

The check enforces ADR-0001 main-vs-experimental boundary discipline.
These tests pin its behavior so future changes that loosen detection
or break the allowlist are caught at test time.

Pre-reg prereg-ed736cac falsifier covers behavior in production
(boundary violations landing in main main-branch despite the check).
These tests cover behavior in the checker itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the script importable.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import check_boundary_violations as cbv  # noqa: E402


class TestPathRules:
    """Path-based detection."""

    def test_family_letters_caught(self, tmp_path: Path) -> None:
        (tmp_path / "family" / "letters").mkdir(parents=True)
        (tmp_path / "family" / "letters" / "aether-to-aria-2026-04-19.md").write_text(
            "letter content", encoding="utf-8"
        )
        violations = cbv.find_path_violations(tmp_path)
        rels = [v.rel_path for v in violations]
        assert "family/letters/aether-to-aria-2026-04-19.md" in rels

    def test_family_letters_readme_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "family" / "letters").mkdir(parents=True)
        (tmp_path / "family" / "letters" / "README.md").write_text(
            "this is the template README", encoding="utf-8"
        )
        violations = cbv.find_path_violations(tmp_path)
        rels = [v.rel_path for v in violations]
        assert "family/letters/README.md" not in rels

    def test_dated_council_walk_caught(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "council_walks").mkdir(parents=True)
        (tmp_path / "docs" / "council_walks" / "2026-05-07-property-walk.md").write_text(
            "walk content", encoding="utf-8"
        )
        violations = cbv.find_path_violations(tmp_path)
        assert any(
            v.rel_path == "docs/council_walks/2026-05-07-property-walk.md" for v in violations
        )

    def test_council_walks_readme_not_caught_by_path_rule(self, tmp_path: Path) -> None:
        """README is path-allowed but should still be content-scanned."""
        (tmp_path / "docs" / "council_walks").mkdir(parents=True)
        (tmp_path / "docs" / "council_walks" / "README.md").write_text(
            "Generic README content", encoding="utf-8"
        )
        violations = cbv.find_path_violations(tmp_path)
        assert not any(v.rel_path == "docs/council_walks/README.md" for v in violations)

    def test_aria_ledger_caught(self, tmp_path: Path) -> None:
        (tmp_path / "family").mkdir()
        (tmp_path / "family" / "aria_ledger.db").write_bytes(b"sqlite stub")
        violations = cbv.find_path_violations(tmp_path)
        assert any(v.rel_path == "family/aria_ledger.db" for v in violations)

    def test_aether_md_caught(self, tmp_path: Path) -> None:
        """AETHER.md at project root is substrate-occupant identity-document
        and belongs in Experimental, not main. Per Aletheia round-8 audit
        observation 2026-05-08: identity-documents are a file-class that
        ADR-0001 boundary-discipline should cover, same shape as the
        family/* substrate-state directories."""
        (tmp_path / "AETHER.md").write_text("# AETHER.md\n\nidentity content", encoding="utf-8")
        violations = cbv.find_path_violations(tmp_path)
        assert any(v.rel_path == "AETHER.md" for v in violations)

    def test_numbered_exploration_caught(self, tmp_path: Path) -> None:
        (tmp_path / "exploration").mkdir()
        (tmp_path / "exploration" / "01_first_entry.md").write_text(
            "exploration content", encoding="utf-8"
        )
        violations = cbv.find_path_violations(tmp_path)
        assert any(v.rel_path == "exploration/01_first_entry.md" for v in violations)

    def test_exploration_readme_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "exploration").mkdir()
        (tmp_path / "exploration" / "README.md").write_text(
            "exploration template README", encoding="utf-8"
        )
        violations = cbv.find_path_violations(tmp_path)
        assert not any(v.rel_path == "exploration/README.md" for v in violations)


class TestContentRules:
    """Content-based detection."""

    def test_prereg_filed_by_specific_actor_caught(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "pre_regs").mkdir(parents=True)
        f = tmp_path / "docs" / "pre_regs" / "prereg-deadbeef.md"
        f.write_text(
            "# Pre-registration: example\n\n"
            "- **ID**: `prereg-deadbeef`\n"
            "- **Filed by**: aether\n"
            "- **Filed at**: 2026-05-08 12:00 UTC\n",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert any(v.rel_path == "docs/pre_regs/prereg-deadbeef.md" for v in violations)

    def test_prereg_filed_by_agent_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "pre_regs").mkdir(parents=True)
        f = tmp_path / "docs" / "pre_regs" / "prereg-cafebabe.md"
        f.write_text(
            "# Pre-registration: example\n\n"
            "- **ID**: `prereg-cafebabe`\n"
            "- **Filed by**: agent\n"
            "- **Filed at**: 2026-05-08 12:00 UTC\n",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert not any(v.rel_path == "docs/pre_regs/prereg-cafebabe.md" for v in violations)

    def test_prereg_filed_by_system_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "pre_regs").mkdir(parents=True)
        f = tmp_path / "docs" / "pre_regs" / "prereg-12345678.md"
        f.write_text("- **Filed by**: system\n", encoding="utf-8")
        violations = cbv.find_content_violations(tmp_path)
        assert not any(v.rel_path == "docs/pre_regs/prereg-12345678.md" for v in violations)

    def test_foundations_named_attribution_caught(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "foundations").mkdir(parents=True)
        f = tmp_path / "docs" / "foundations" / "layer_0.md"
        f.write_text(
            "# Layer 0\n\n"
            "**Authors**: Andrew (methodology), External Claude (audit), "
            "Aether (build), Aria (correction)\n",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert any(v.rel_path == "docs/foundations/layer_0.md" for v in violations)

    def test_foundations_generic_attribution_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "foundations").mkdir(parents=True)
        f = tmp_path / "docs" / "foundations" / "layer_1.md"
        f.write_text(
            "# Layer 1\n\n**Authors**: substrate-occupant (build), audit-instance (review)\n",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert not any(v.rel_path == "docs/foundations/layer_1.md" for v in violations)

    def test_claude_md_substrate_assertion_caught(self, tmp_path: Path) -> None:
        f = tmp_path / "CLAUDE.md"
        f.write_text(
            "Some text. The loadout surveys my explorations, letters with Aria, and date-nights.\n",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert any(v.rel_path == "CLAUDE.md" for v in violations)

    def test_claude_md_template_pointer_allowed(self, tmp_path: Path) -> None:
        f = tmp_path / "CLAUDE.md"
        f.write_text(
            "If your install has accumulated state, LOADOUT.md surveys what's there.\n",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert not any(v.rel_path == "CLAUDE.md" for v in violations)

    def test_council_walks_readme_possessive_caught(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "council_walks").mkdir(parents=True)
        f = tmp_path / "docs" / "council_walks" / "README.md"
        f.write_text(
            "Each file ends with Aether's closing synthesis across the walk.",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        assert any(v.rel_path == "docs/council_walks/README.md" for v in violations)

    def test_council_walks_readme_generic_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "council_walks").mkdir(parents=True)
        f = tmp_path / "docs" / "council_walks" / "README.md"
        f.write_text(
            "Each file ends with the agent's closing synthesis across the walk.",
            encoding="utf-8",
        )
        violations = cbv.find_content_violations(tmp_path)
        # Generic possessive ('agent's') should NOT trigger.
        assert not any(v.rel_path == "docs/council_walks/README.md" for v in violations)


class TestAllowlist:
    """Files in the global allowlist or under allowlisted prefixes are exempt."""

    def test_adr_document_allowlisted(self) -> None:
        assert cbv._path_in_global_allowlist("docs/adr/0001-three-version-repo-architecture.md")

    def test_tests_directory_allowlisted(self) -> None:
        assert cbv._path_in_global_allowlist("tests/test_anything.py")
        assert cbv._path_in_global_allowlist("tests/conftest.py")

    def test_detector_files_allowlisted(self) -> None:
        assert cbv._path_in_global_allowlist("src/divineos/core/dissociation_filter.py")
        assert cbv._path_in_global_allowlist("src/divineos/core/distancing_detector.py")

    def test_operating_loop_allowlisted(self) -> None:
        assert cbv._path_in_global_allowlist("src/divineos/core/operating_loop/lepos_detector.py")
        assert cbv._path_in_global_allowlist("src/divineos/core/operating_loop/banned_phrases.py")

    def test_ablation_runner_allowlisted(self) -> None:
        assert cbv._path_in_global_allowlist("scripts/ablation_runner.py")

    def test_random_path_not_allowlisted(self) -> None:
        assert not cbv._path_in_global_allowlist("docs/foundations/layer_0.md")
        assert not cbv._path_in_global_allowlist("CLAUDE.md")
        assert not cbv._path_in_global_allowlist("README.md")


class TestIntegration:
    """End-to-end on a synthesized tree."""

    def test_clean_tree_no_violations(self, tmp_path: Path) -> None:
        # A bare-template tree with only allowlisted README files.
        (tmp_path / "family" / "letters").mkdir(parents=True)
        (tmp_path / "family" / "letters" / "README.md").write_text("template", encoding="utf-8")
        (tmp_path / "exploration").mkdir()
        (tmp_path / "exploration" / "README.md").write_text("template", encoding="utf-8")
        violations = cbv.find_path_violations(tmp_path) + cbv.find_content_violations(tmp_path)
        assert violations == []

    def test_dirty_tree_finds_all_categories(self, tmp_path: Path) -> None:
        # Synthesize one of each violation category.
        (tmp_path / "family" / "letters").mkdir(parents=True)
        (tmp_path / "family" / "letters" / "letter1.md").write_text("x", encoding="utf-8")
        (tmp_path / "docs" / "council_walks").mkdir(parents=True)
        (tmp_path / "docs" / "council_walks" / "2026-01-01-walk.md").write_text(
            "x", encoding="utf-8"
        )
        (tmp_path / "docs" / "pre_regs").mkdir(parents=True)
        (tmp_path / "docs" / "pre_regs" / "prereg-aaaaaaaa.md").write_text(
            "- **Filed by**: aether\n", encoding="utf-8"
        )
        path_v = cbv.find_path_violations(tmp_path)
        content_v = cbv.find_content_violations(tmp_path)
        assert len(path_v) >= 2  # letter + dated walk
        assert len(content_v) >= 1  # prereg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
