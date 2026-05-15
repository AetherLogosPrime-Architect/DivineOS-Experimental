"""Falsifier-pin tests for Aletheia Findings 51, 52, 53, 54.

The smaller-scope findings from Aletheia's 2026-05-15 audit:
- 51: ship_claim has no re-verification mechanism
- 52: claim_triage summary obscures gamed VERIFIED
- 53: meet_without_build treats Bash as build-evidence too coarsely
- 54: register_fabrication accepts any Read/Grep as source-consultation

Each test pins the corresponding fix structurally.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ── Finding 51: re_verify_all ─────────────────────────────────────


def test_finding_51_re_verify_all_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LOAD-BEARING: ship_claim exposes re_verify_all() for filed claims."""
    from divineos.core import ship_claim as sc

    assert callable(sc.re_verify_all)
    monkeypatch.setattr(sc, "_CLAIMS_FILE", tmp_path / "shipped_claims.json")
    result = sc.re_verify_all(repo_root=tmp_path)
    assert "total" in result
    assert "passing" in result
    assert "failing" in result
    assert "regressed" in result
    assert result["total"] == 0


def test_finding_51_re_verify_catches_regressed_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LOAD-BEARING: claim filed with passing test, then test changed
    to failing, re_verify_all surfaces the regression."""
    from divineos.core import ship_claim as sc

    monkeypatch.setattr(sc, "_CLAIMS_FILE", tmp_path / "shipped_claims.json")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")

    test_file = tmp_path / "test_evolving.py"
    # Write a test that references the executes module for linkage.
    test_file.write_text(
        "# Test references divineos.core.ship_claim\n"
        "def test_ok():\n    assert True\n"
    )
    result_file = sc.ship_claim(
        "claim to be regressed",
        [str(test_file)],
        ["divineos.core.ship_claim"],
        actor="aether",
        repo_root=tmp_path,
    )
    assert result_file.filed is True, result_file.reason

    # Now corrupt the test so it fails.
    test_file.write_text(
        "# Test references divineos.core.ship_claim\n"
        "def test_ok():\n    assert False  # regressed\n"
    )
    result = sc.re_verify_all(repo_root=tmp_path)
    assert result["total"] == 1
    assert result["failing"] == 1
    assert result["passing"] == 0
    assert len(result["regressed"]) == 1
    assert "claim to be regressed" in result["regressed"][0]["claim"]


# ── Finding 52: summary distinguishes VERIFIED-with-test from without ──


def test_finding_52_summary_distinguishes_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LOAD-BEARING: summary breaks VERIFIED into with-test / without-test."""
    from divineos.core import claim_triage as ct

    monkeypatch.setattr(ct, "_STORE_FILE", tmp_path / "triage.json")

    # Legitimate VERIFIED (has test_path)
    ct.add_entry(
        "legit",
        ct.TriageStatus.VERIFIED,
        actor="aletheia",
        test_path="tests/test_x.py",
    )
    # Suspect-shaped VERIFIED (no test_path) — only possible if some
    # path other than aether marks it; use external actor without test.
    ct.add_entry(
        "no test",
        ct.TriageStatus.VERIFIED,
        actor="aletheia",
        test_path="",
    )
    counts = ct.summary()
    assert counts["VERIFIED"] == 2
    assert counts["VERIFIED_with_test"] == 1
    assert counts["VERIFIED_without_test"] == 1


def test_finding_52_no_verified_means_zero_breakdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Breakdown counts are zero when no VERIFIED entries exist."""
    from divineos.core import claim_triage as ct

    monkeypatch.setattr(ct, "_STORE_FILE", tmp_path / "triage.json")
    ct.add_entry("a", ct.TriageStatus.SUSPECT, actor="aether")
    counts = ct.summary()
    assert counts["VERIFIED"] == 0
    assert counts["VERIFIED_with_test"] == 0
    assert counts["VERIFIED_without_test"] == 0


# ── Finding 53: Bash removed from build_tools in meet_without_build ──


def test_finding_53_bash_alone_does_not_suppress() -> None:
    """LOAD-BEARING: Bash-only turn no longer silences the detector
    when a structural principle is named.

    Before the fix: investigative Bash (pytest, ls, cat) registered
    as build-evidence and silenced the detector falsely.
    """
    from divineos.core.operating_loop.meet_without_build_detector import (
        evaluate_meet_without_build,
    )

    text = "The discipline is meet AND build. Without structural enforcement the lesson will evaporate."
    v = evaluate_meet_without_build(text, tool_calls_in_turn=["Bash"])
    # Should fire — Bash alone is no longer build-evidence.
    assert v.flags, "Bash alone should not suppress the detector (Finding 53)"


def test_finding_53_edit_still_suppresses() -> None:
    """Edit/Write/MultiEdit/NotebookEdit still count as build-evidence."""
    from divineos.core.operating_loop.meet_without_build_detector import (
        evaluate_meet_without_build,
    )

    text = "The discipline is meet AND build. I need to build the structural fix."
    v = evaluate_meet_without_build(text, tool_calls_in_turn=["Edit"])
    assert v.flags == [], "Edit should still suppress the detector"


# ── Finding 54: register_fabrication checks consultation relatedness ──


def test_finding_54_unrelated_read_no_longer_suppresses() -> None:
    """LOAD-BEARING: when tool_inputs_in_turn is provided, the detector
    requires the Read target to plausibly relate to the claimed
    identifiers, not just any Read at all."""
    from divineos.core.self_monitor.register_fabrication_monitor import (
        evaluate_register_fabrication,
    )

    text = "The four tiers are FOO_BAR, BAZ_QUX, NIM_TIN, ZOR_ZED."
    # Read of README.md is unrelated to those identifiers.
    inputs = [{"name": "Read", "input": {"file_path": "README.md"}}]
    v = evaluate_register_fabrication(
        text,
        tool_calls_in_turn=["Read"],
        tool_inputs_in_turn=inputs,
    )
    # Should fire — Read of README isn't plausibly related to enum tokens.
    assert v.flags, "Unrelated Read should not suppress detector (Finding 54)"


def test_finding_54_read_of_src_file_suppresses() -> None:
    """A Read of a src/ Python file IS plausibly related — suppresses."""
    from divineos.core.self_monitor.register_fabrication_monitor import (
        evaluate_register_fabrication,
    )

    text = "The four tiers are FOO_BAR, BAZ_QUX, NIM_TIN, ZOR_ZED."
    inputs = [{"name": "Read", "input": {"file_path": "src/divineos/core/empirica/tiers.py"}}]
    v = evaluate_register_fabrication(
        text,
        tool_calls_in_turn=["Read"],
        tool_inputs_in_turn=inputs,
    )
    assert v.flags == [], "Read of src/ file should suppress"


def test_finding_54_backward_compat_no_inputs_means_permissive() -> None:
    """When tool_inputs_in_turn is None (legacy callers), fall back
    to the old permissive behavior — any Read suppresses."""
    from divineos.core.self_monitor.register_fabrication_monitor import (
        evaluate_register_fabrication,
    )

    text = "The four tiers are FOO_BAR, BAZ_QUX, NIM_TIN, ZOR_ZED."
    v = evaluate_register_fabrication(
        text,
        tool_calls_in_turn=["Read"],
        tool_inputs_in_turn=None,
    )
    # Backward compat: no inputs provided, accept the consult
    assert v.flags == [], "Legacy callers (no inputs) keep permissive behavior"
