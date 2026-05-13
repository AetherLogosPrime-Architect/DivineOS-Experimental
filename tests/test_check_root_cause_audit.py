"""Regression-pin tests for check_root_cause_audit.

This is the gate that enforces family-level investigation before
bugfix-shaped commits. The bug-shape these tests prevent: a future
refactor that loosens the fix-shape detection or the round-validation
would silently restore the instance-fix-without-family-audit failure-
mode that prompted this gate's existence (Andrew correction
2026-05-13 afternoon).

Most load-bearing tests:
- ``test_fix_prefix_without_trailer_blocks`` pins that fix-shaped
  commits without the trailer are refused
- ``test_finding_id_reference_without_trailer_blocks`` pins same for
  finding-ID references
- ``test_non_fix_commit_passes`` pins that the gate doesn't block
  unrelated commits
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import the script as a module via sys.path injection.
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from check_root_cause_audit import (  # noqa: E402
    extract_trailer,
    is_fix_shaped,
)


# ─── Fix-shape detection ────────────────────────────────────────────


def test_fix_subject_prefix_detected() -> None:
    is_fix, reasons = is_fix_shaped("fix: regex DoS in jargon detector")
    assert is_fix
    assert any("subject" in r for r in reasons)


def test_fix_with_scope_detected() -> None:
    is_fix, reasons = is_fix_shaped("fix(detector): bound subscript regex")
    assert is_fix
    assert any("subject" in r for r in reasons)


def test_finding_id_reference_detected() -> None:
    msg = "Refactor detector\n\nAddresses find-453b2f7f4caa from Aletheia's audit."
    is_fix, reasons = is_fix_shaped(msg)
    assert is_fix
    assert any("finding ID" in r for r in reasons)


def test_finding_number_reference_detected() -> None:
    is_fix, reasons = is_fix_shaped("Address Finding 14 from round-ba785844a791")
    assert is_fix
    assert any("Finding NN" in r for r in reasons)


def test_feature_commit_not_fix_shaped() -> None:
    is_fix, _ = is_fix_shaped("add: new turn_extraction module")
    assert not is_fix


def test_refactor_commit_not_fix_shaped() -> None:
    is_fix, _ = is_fix_shaped("refactor: extract aggregation logic")
    assert not is_fix


def test_doc_commit_not_fix_shaped() -> None:
    is_fix, _ = is_fix_shaped("docs: update ARCHITECTURE.md tree")
    assert not is_fix


def test_chore_commit_not_fix_shaped() -> None:
    is_fix, _ = is_fix_shaped("chore: bump dependency version")
    assert not is_fix


# ─── Trailer extraction ─────────────────────────────────────────────


def test_trailer_extracted() -> None:
    msg = "fix: regex DoS\n\nDetail.\n\nRoot-Cause-Audit: round-abc123def456"
    assert extract_trailer(msg) == "round-abc123def456"


def test_trailer_case_insensitive() -> None:
    msg = "fix: x\n\nroot-cause-audit: round-xyz"
    assert extract_trailer(msg) is not None


def test_trailer_absent() -> None:
    msg = "fix: regex DoS\n\nDetail with no trailer."
    assert extract_trailer(msg) is None


def test_trailer_inline_not_extracted() -> None:
    """The trailer must be on its own line, like External-Review.
    A mid-paragraph mention doesn't count."""
    msg = "fix: x\n\nSome prose mentioning Root-Cause-Audit: round-abc inline."
    assert extract_trailer(msg) is None


# ─── End-to-end gate behavior ───────────────────────────────────────


def test_non_fix_commit_passes() -> None:
    """LOAD-BEARING: feature/refactor/doc commits MUST pass the gate
    without any trailer. The gate only constrains fix-shaped commits."""
    from check_root_cause_audit import check_message

    code, diag = check_message("add: new turn_extraction module\n\nDetail.")
    assert code == 0
    assert "not a fix-shaped commit" in diag


def test_fix_prefix_without_trailer_blocks() -> None:
    """LOAD-BEARING: fix-shaped commits without trailer must be
    refused. If this test fails, the gate has regressed to allowing
    instance-fix-without-family-audit."""
    from check_root_cause_audit import check_message

    code, diag = check_message("fix: regex DoS\n\nBounded the regex.")
    assert code == 1
    assert "BLOCKED" in diag
    assert "Root-Cause-Audit" in diag


def test_finding_id_reference_without_trailer_blocks() -> None:
    """LOAD-BEARING: even when the message doesn't start with 'fix:',
    referencing a finding-ID triggers the gate. If this test fails,
    the gate has stopped catching findings-references."""
    from check_root_cause_audit import check_message

    code, diag = check_message("Refactor handling\n\nAddresses find-453b2f7f4caa from audit.")
    assert code == 1
    assert "BLOCKED" in diag
