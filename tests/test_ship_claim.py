"""Regression-pin tests for falsifier-enforced ship-claim.

Andrew named the show-fix pattern 2026-05-14. This module's contract:
no claim files unless the falsifier-test passes RIGHT NOW. These tests
verify the contract from both directions — passes file the claim,
failures reject it.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from divineos.core import ship_claim as sc


@pytest.fixture(autouse=True)
def isolate_claims_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test writes to its own claims file."""
    monkeypatch.setattr(sc, "_CLAIMS_FILE", tmp_path / "shipped_claims.json")


def _make_passing_test(tmp_path: Path) -> Path:
    test_file = tmp_path / "test_passing.py"
    test_file.write_text("def test_ok():\n    assert True\n")
    return test_file


def _make_failing_test(tmp_path: Path) -> Path:
    test_file = tmp_path / "test_failing.py"
    test_file.write_text("def test_fails():\n    assert False\n")
    return test_file


def test_rejects_empty_claim() -> None:
    r = sc.ship_claim("", ["t.py"], ["os"])
    assert r.filed is False
    assert "empty" in r.reason.lower()


def test_rejects_missing_test_paths() -> None:
    r = sc.ship_claim("claim", [], ["os"])
    assert r.filed is False
    assert "falsifier" in r.reason.lower() or "test_paths" in r.reason.lower()


def test_rejects_missing_executes() -> None:
    r = sc.ship_claim("claim", ["t.py"], [])
    assert r.filed is False
    assert "executes" in r.reason.lower()


def test_rejects_unimportable_executes(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    r = sc.ship_claim(
        "claim", [str(test_file)], ["divineos.does.not.exist"], repo_root=tmp_path
    )
    assert r.filed is False
    assert "not importable" in r.reason.lower()


def test_rejects_missing_attribute_on_executes(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim:no_such_function"],
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "missing attribute" in r.reason.lower()


def test_rejects_failing_test(tmp_path: Path) -> None:
    test_file = _make_failing_test(tmp_path)
    # Need a real repo_root with pyproject.toml or tests work weirdly; use tmp_path
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "claim",
        [str(test_file)],
        ["divineos.core.ship_claim:ship_claim"],
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "falsifier failed" in r.reason.lower()


def test_accepts_passing_test_and_valid_executes(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    r = sc.ship_claim(
        "Gate 6.5 read-before-write is shipped",
        [str(test_file)],
        ["divineos.core.read_before_write:gate_check"],
        repo_root=tmp_path,
    )
    assert r.filed is True, f"expected filed, got: {r.reason}"
    assert r.entry is not None
    assert r.entry["claim"] == "Gate 6.5 read-before-write is shipped"
    assert "test_passing.py" in r.entry["test_paths"][0]


def test_filed_claim_appears_in_list(tmp_path: Path) -> None:
    test_file = _make_passing_test(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    sc.ship_claim(
        "First claim",
        [str(test_file)],
        ["divineos.core.ship_claim"],
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
        cross_check="exit 1",
        repo_root=tmp_path,
    )
    assert r.filed is False
    assert "cross-check" in r.reason.lower()


def test_guardrail_marker_present() -> None:
    src = Path(sc.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
