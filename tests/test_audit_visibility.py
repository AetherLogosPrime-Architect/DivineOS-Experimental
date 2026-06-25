"""Tests for divineos.core.audit_visibility.

Focus: the deterministic helpers (is_auditable_path) and the routing
logic of check_visibility with all git/subprocess paths mocked.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.audit_visibility import (
    AUDITABLE_PREFIXES,
    VisibilityResult,
    check_visibility,
    is_auditable_path,
)


class TestIsAuditablePath:
    """Prefix check for path classification."""

    def test_src_divineos_is_auditable(self):
        assert is_auditable_path("src/divineos/core/foo.py") is True

    def test_scripts_is_auditable(self):
        assert is_auditable_path("scripts/push_queued.py") is True

    def test_github_workflows_is_auditable(self):
        assert is_auditable_path(".github/workflows/ci.yml") is True

    def test_setup_is_auditable(self):
        assert is_auditable_path("setup/setup-hooks.sh") is True

    def test_claude_hooks_is_auditable(self):
        assert is_auditable_path(".claude/hooks/some-hook.sh") is True

    def test_docs_is_not_auditable(self):
        assert is_auditable_path("docs/ARCHITECTURE.md") is False

    def test_exploration_is_not_auditable(self):
        assert is_auditable_path("exploration/aether/notes.md") is False

    def test_family_letters_not_auditable(self):
        assert is_auditable_path("family/letters/aria-to-aether-2026-06-24-x.md") is False

    def test_root_readme_not_auditable(self):
        assert is_auditable_path("README.md") is False


class TestCheckVisibilityRouting:
    """The central decision routing with all git calls mocked."""

    def test_main_branch_no_warn(self):
        with patch("divineos.core.audit_visibility._current_branch", return_value="main"):
            result = check_visibility()
            assert result.should_warn is False
            assert "main" in result.reason

    def test_detached_head_no_warn(self):
        with patch("divineos.core.audit_visibility._current_branch", return_value="HEAD"):
            result = check_visibility()
            assert result.should_warn is False

    def test_empty_branch_no_warn(self):
        with patch("divineos.core.audit_visibility._current_branch", return_value=""):
            result = check_visibility()
            assert result.should_warn is False

    def test_no_auditable_files_no_warn(self):
        with (
            patch("divineos.core.audit_visibility._current_branch", return_value="feat/x"),
            patch(
                "divineos.core.audit_visibility._files_in_head",
                return_value=["docs/README.md", "exploration/notes.md"],
            ),
        ):
            result = check_visibility()
            assert result.should_warn is False
            assert "no auditable paths" in result.reason

    def test_auditable_and_published_no_warn(self):
        with (
            patch("divineos.core.audit_visibility._current_branch", return_value="feat/x"),
            patch(
                "divineos.core.audit_visibility._files_in_head",
                return_value=["src/divineos/core/foo.py"],
            ),
            patch("divineos.core.audit_visibility._local_head_sha", return_value="abc123"),
            patch(
                "divineos.core.audit_visibility._remote_head_sha",
                return_value=(0, "abc123"),
            ),
        ):
            result = check_visibility()
            assert result.should_warn is False
            assert "published" in result.reason

    def test_auditable_and_not_on_origin_warns(self):
        with (
            patch("divineos.core.audit_visibility._current_branch", return_value="feat/x"),
            patch(
                "divineos.core.audit_visibility._files_in_head",
                return_value=["src/divineos/core/foo.py"],
            ),
            patch("divineos.core.audit_visibility._local_head_sha", return_value="abc123"),
            patch(
                "divineos.core.audit_visibility._remote_head_sha",
                return_value=(0, ""),
            ),
            patch("divineos.core.audit_visibility._git", return_value=(0, "abc123 fix(x)")),
        ):
            result = check_visibility()
            assert result.should_warn is True
            assert "AUDITABLE WORK NOT VISIBLE" in result.banner
            assert "git push -u origin feat/x" in result.banner

    def test_auditable_and_local_differs_from_remote_warns(self):
        with (
            patch("divineos.core.audit_visibility._current_branch", return_value="feat/x"),
            patch(
                "divineos.core.audit_visibility._files_in_head",
                return_value=["scripts/push_queued.py"],
            ),
            patch("divineos.core.audit_visibility._local_head_sha", return_value="abc123"),
            patch(
                "divineos.core.audit_visibility._remote_head_sha",
                return_value=(0, "def456"),
            ),
            patch("divineos.core.audit_visibility._git", return_value=(0, "abc123 fix(x)")),
        ):
            result = check_visibility()
            assert result.should_warn is True
            assert "abc123" in result.reason and "def456" in result.reason

    def test_ls_remote_failure_warns_conservatively(self):
        # Network failure → warn (don't trust silent "published" assumption).
        with (
            patch("divineos.core.audit_visibility._current_branch", return_value="feat/x"),
            patch(
                "divineos.core.audit_visibility._files_in_head",
                return_value=["src/divineos/core/foo.py"],
            ),
            patch("divineos.core.audit_visibility._local_head_sha", return_value="abc123"),
            patch(
                "divineos.core.audit_visibility._remote_head_sha",
                return_value=(1, ""),
            ),
            patch("divineos.core.audit_visibility._git", return_value=(0, "abc123 fix(x)")),
        ):
            result = check_visibility()
            assert result.should_warn is True
            assert "ls-remote failed" in result.reason


class TestVisibilityResultDataclass:
    """Result type is well-formed."""

    def test_no_warn_default(self):
        r = VisibilityResult(should_warn=False)
        assert r.should_warn is False
        assert r.banner == ""
        assert r.branch == ""

    def test_warn_shape(self):
        r = VisibilityResult(should_warn=True, banner="loud", branch="feat/x", reason="why")
        assert r.should_warn is True
        assert r.banner == "loud"
        assert r.branch == "feat/x"


class TestAuditablePrefixesContract:
    """Lock the public AUDITABLE_PREFIXES list so any change is intentional."""

    def test_includes_src_divineos(self):
        assert "src/divineos/" in AUDITABLE_PREFIXES

    def test_includes_scripts(self):
        assert "scripts/" in AUDITABLE_PREFIXES

    def test_includes_workflows(self):
        assert ".github/workflows/" in AUDITABLE_PREFIXES

    def test_includes_setup(self):
        assert "setup/" in AUDITABLE_PREFIXES

    def test_includes_hooks(self):
        assert ".claude/hooks/" in AUDITABLE_PREFIXES
