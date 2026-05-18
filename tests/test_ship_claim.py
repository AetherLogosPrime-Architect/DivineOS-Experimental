"""Regression-pin tests for falsifier-enforced ship-claim.

Andrew named the show-fix pattern 2026-05-14. This module's contract:
no claim files unless the falsifier-test passes RIGHT NOW. These tests
verify the contract from both directions — passes file the claim,
failures reject it.

Updated 2026-05-15 (Aletheia Findings 49 + 50): tests now exercise
the test-executes linkage check (Finding 49) and the required actor
field (Finding 50).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import ship_claim as sc


@pytest.fixture(autouse=True)
def isolate_claims_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test writes to its own claims file."""
    monkeypatch.setattr(sc, "_CLAIMS_FILE", tmp_path / "shipped_claims.json")


def _make_passing_test(tmp_path: Path, executes_module: str = "divineos.core.ship_claim") -> Path:
    """Write a passing test that references the executes module (for linkage)."""
    test_file = tmp_path / "test_passing.py"
    test_file.write_text(
        f"# Test references {executes_module} for linkage check\ndef test_ok():\n    assert True\n"
    )
    return test_file


def _make_failing_test(tmp_path: Path, executes_module: str = "divineos.core.ship_claim") -> Path:
    test_file = tmp_path / "test_failing.py"
    test_file.write_text(
        f"# Test references {executes_module} for linkage check\n"
        f"def test_fails():\n    assert False\n"
    )
    return test_file


def _make_unlinked_test(tmp_path: Path) -> Path:
    """A test file that does NOT reference the executes module (linkage fails)."""
    test_file = tmp_path / "test_unrelated.py"
    test_file.write_text(
        "# This test has no reference to any executes module\n"
        "def test_unrelated(): assert 1 + 1 == 2\n"
    )
    return test_file


# ── Original contract tests (updated to pass actor) ───────────────


def test_rejects_empty_claim() -> None:
    r = sc.ship_claim("", ["t.py"], ["os"], actor="aether")
    assert r.filed is False
    assert "empty" in r.reason.lower()


def test_rejects_missing_test_paths() -> None:
    r = sc.ship_claim("claim", [], ["os"], actor="aether")
    assert r.filed is False
    assert "falsifier" in r.reason.lower() or "test_paths" in r.reason.lower()


def test_rejects_missing_executes() -> None:
    r = sc.ship_claim("claim", ["t.py"], [], actor="aether")
    assert r.filed is False
    assert "executes" in r.reason.lower()


def test_rejects_unimportable_executes(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path, "divineos.does.not.exist")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.does.not.exist"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "not importable" in r.reason.lower()


def test_rejects_missing_attribute_on_executes(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim:no_such_function"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "missing attribute" in r.reason.lower()


def test_rejects_failing_test(tmp_path: Path) -> None:
    test_file = _make_failing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim:ship_claim"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "falsifier failed" in r.reason.lower()


def test_accepts_passing_test_and_valid_executes(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path, "divineos.core.read_before_write")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "Gate 6.5 read-before-write is shipped",
        [str(test_file)],
        ["divineos.core.read_before_write:gate_check"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert r.filed is True, f"expected filed, got: {r.reason}"
    assert r.entry is not None
    assert r.entry["claim"] == "Gate 6.5 read-before-write is shipped"
    assert r.entry["actor"] == "aether"
    assert "test_passing.py" in r.entry["test_paths"][0]


def test_filed_claim_appears_in_list(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    sc.ship_claim(
        "First claim",
        [str(test_file)],
        ["divineos.core.ship_claim"],
        actor="aether",
        repo_root=tmp_path,
    )
    claims = sc.list_claims()
    assert any(c.get("claim") == "First claim" for c in claims)


def test_rejects_failing_cross_check(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim"],
        actor="aether",
        cross_check="exit 1",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "cross-check" in r.reason.lower()


# ── New tests for Finding 49 (test-executes linkage) ───────────────


def test_rejects_test_not_linked_to_executes(tmp_path: Path) -> None:
    """LOAD-BEARING (Finding 49): test that doesn't reference executes
    module fails the linkage check. Aletheia's empirical attack.
    """
    unlinked = _make_unlinked_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "fake claim about ship_claim",
        [str(unlinked)],
        ["divineos.core.ship_claim:ship_claim"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "linkage" in r.reason.lower()


def test_accepts_test_that_references_executes(tmp_path: Path) -> None:
    """Test file containing the executes module path passes linkage."""
    test_file = _make_passing_test(tmp_path, "divineos.core.read_before_write")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.read_before_write:gate_check"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert r.filed is True, f"expected filed, got: {r.reason}"


# ── New tests for Finding 50 (actor field) ───────────────


def test_rejects_missing_actor(tmp_path: Path) -> None:
    """LOAD-BEARING (Finding 50): empty actor refused."""
    test_file = _make_passing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim"],
        actor="",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "actor" in r.reason.lower()


def test_rejects_internal_actor_name(tmp_path: Path) -> None:
    """LOAD-BEARING (Finding 50 + watchmen discipline): internal-component
    actor names rejected to prevent self-audit-as-external-validation."""
    test_file = _make_passing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim"],
        actor="claude",
        repo_root=tmp_path,
    )
    assert r.filed is False


def test_actor_field_recorded_in_entry(tmp_path: Path) -> None:
    """Actor is recorded in the persisted entry."""
    test_file = _make_passing_test(tmp_path, "divineos.core.read_before_write")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.read_before_write"],
        actor="aletheia",
        repo_root=tmp_path,
    )
    assert r.filed is True, f"expected filed, got: {r.reason}"
    assert r.entry["actor"] == "aletheia"


def test_guardrail_marker_present() -> None:
    src = Path(sc.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
