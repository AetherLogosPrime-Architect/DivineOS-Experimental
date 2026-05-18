"""Tests for the --ignore-has-reason gate (Aletheia Finding 74).

The gate refuses pytest --ignore= usages without an adjacent # REASON:
comment naming what's being masked and why. Substrate-level prevention
for the bypass-too-broad pattern that recurred twice on 2026-05-17.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to sys.path so we can import the checker module.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from check_ignore_has_reason import _check_file, _looks_like_pytest_invocation  # noqa: E402


class TestPytestInvocationDetection:
    """The check must only fire on real pytest invocations, not prose."""

    def test_matches_bare_pytest_call(self):
        assert _looks_like_pytest_invocation("pytest --ignore=tests/foo.py")

    def test_matches_python_module_invocation(self):
        assert _looks_like_pytest_invocation("python -m pytest tests/ --ignore=tests/foo.py")

    def test_matches_py_dot_test_legacy(self):
        assert _looks_like_pytest_invocation("py.test --ignore=tests/foo.py")

    def test_skips_docstring_mention(self):
        # A docstring that talks ABOUT --ignore but doesn't invoke pytest
        # should not match.
        line = '    """The --ignore= flag is dangerous when used broadly."""'
        assert not _looks_like_pytest_invocation(line)

    def test_skips_non_pytest_ignore(self):
        # grep --ignore-case, rsync --ignore-existing, etc. are different
        # tools; this check is scoped to pytest by Finding 74's naming.
        assert not _looks_like_pytest_invocation("grep --ignore-case foo bar")
        assert not _looks_like_pytest_invocation("rsync --ignore-existing src/ dst/")


class TestCheckFile:
    """File-level scanning with REASON-comment lookback."""

    def _write(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "script.sh"
        p.write_text(content, encoding="utf-8")
        return p

    def test_invocation_with_reason_passes(self, tmp_path):
        content = (
            "#!/bin/bash\n"
            "# REASON: test_foo has pre-existing failure in claim-123;\n"
            "#         masking until upstream-fix lands.\n"
            "pytest tests/ --ignore=tests/test_foo.py\n"
        )
        p = self._write(tmp_path, content)
        violations = _check_file(p)
        assert violations == []

    def test_invocation_without_reason_fails(self, tmp_path):
        content = "#!/bin/bash\npytest tests/ --ignore=tests/test_foo.py\n"
        p = self._write(tmp_path, content)
        violations = _check_file(p)
        assert len(violations) == 1
        assert "test_foo" in violations[0][1]

    def test_reason_too_far_above_does_not_satisfy(self, tmp_path):
        # REASON 5 lines above the invocation — outside the 3-line window.
        content = (
            "#!/bin/bash\n"
            "# REASON: discussing this masks something\n"
            "\n"
            "\n"
            "\n"
            "echo 'unrelated'\n"
            "pytest tests/ --ignore=tests/test_foo.py\n"
        )
        p = self._write(tmp_path, content)
        violations = _check_file(p)
        # The REASON is at line 2; invocation is at line 7; gap is too wide.
        assert len(violations) == 1

    def test_multiple_invocations_each_need_reason(self, tmp_path):
        # First has REASON, second doesn't — only second flagged.
        content = (
            "#!/bin/bash\n"
            "# REASON: first masking, claim-aaa\n"
            "pytest tests/ --ignore=tests/test_one.py\n"
            "\n"
            "pytest tests/ --ignore=tests/test_two.py\n"
        )
        p = self._write(tmp_path, content)
        violations = _check_file(p)
        assert len(violations) == 1
        assert "test_two" in violations[0][1]

    def test_reason_token_case_sensitive(self, tmp_path):
        # Lowercase "reason:" should NOT satisfy — the discipline is
        # case-sensitive so accidental prose mentions don't pass.
        content = (
            "#!/bin/bash\n# reason: this is too casual\npytest tests/ --ignore=tests/test_foo.py\n"
        )
        p = self._write(tmp_path, content)
        violations = _check_file(p)
        assert len(violations) == 1

    def test_non_pytest_ignore_not_flagged(self, tmp_path):
        # grep, rsync, etc. shouldn't be in scope.
        content = (
            "#!/bin/bash\ngrep --ignore-case 'foo' file.txt\nrsync --ignore-existing src/ dst/\n"
        )
        p = self._write(tmp_path, content)
        violations = _check_file(p)
        assert violations == []

    def test_empty_file(self, tmp_path):
        p = self._write(tmp_path, "")
        assert _check_file(p) == []

    def test_no_pytest_at_all(self, tmp_path):
        p = self._write(tmp_path, "#!/bin/bash\necho hello\n")
        assert _check_file(p) == []


class TestRepoCleanState:
    """The real repo state must be clean after the bypass-discipline fix.

    Specifically: scripts/check_push_readiness.sh used to carry an
    --ignore= against test_check_broad_exceptions without a REASON
    comment. PR #12 + PR #10's noqa fix closed the underlying violations,
    so the masking is no longer justified — the --ignore was removed
    rather than retroactively justified. The repo should scan clean.
    """

    def test_repo_has_no_unjustified_ignore_flags(self):
        from check_ignore_has_reason import _gather_files, _check_file as check

        violations = []
        for p in _gather_files(_REPO_ROOT):
            for line_num, line in check(p):
                violations.append(f"{p.name}:{line_num}: {line[:80]}")
        assert not violations, "Repo has pytest --ignore= without REASON comments:\n" + "\n".join(
            f"  {v}" for v in violations
        )
