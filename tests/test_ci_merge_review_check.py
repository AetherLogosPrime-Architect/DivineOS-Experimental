"""Tests for scripts/ci_merge_review_check.py emergency-bypass branch.

Task #97 / 2026-06-08: the bypass env var must enforce REASON discipline.
Prior shape silently passed the gate when the reason was too short
(`record_emergency_use` raised ValueError → broad except caught → returned 0).

New shape:
  - Valid reason (>=20 chars) → record_emergency_use logs, return 0
  - Invalid reason (<20 chars, ValueError) → return 1 with diagnostic
  - Infra failure during record → return 0 with loud warning

These tests exercise the bypass branch only — they don't need real GitHub
API access because the bypass path returns BEFORE the PR-data fetch.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_script_module():
    """Import scripts/ci_merge_review_check.py as a module so we can call main().

    Scripts aren't on sys.path; we load by file path.
    """
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "ci_merge_review_check.py"
    spec = importlib.util.spec_from_file_location("ci_merge_review_check_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ci_merge_review_check_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script_module():
    return _load_script_module()


class TestEmergencyBypassReasonGate:
    """The env var triggers the bypass ATTEMPT, but the reason gates the EFFECT."""

    def test_valid_reason_logs_and_passes(self, script_module, monkeypatch, capsys):
        """A >=20-char reason fires record_emergency_use and exits 0."""
        monkeypatch.setenv(
            "DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS",
            "real malfunction recovery — auth provider outage requires hotfix merge",
        )

        called_with = {}

        class _StubReport:
            claim_id = "claim-stub-001"
            psf_id = "psf-stub-001"

        def _fake_record(gate_name, env_var, reason):
            called_with["gate_name"] = gate_name
            called_with["env_var"] = env_var
            called_with["reason"] = reason
            return _StubReport()

        # Patch the module that script imports inside the bypass branch.
        monkeypatch.setattr(
            "divineos.core.emergency_bypass.record_emergency_use",
            _fake_record,
        )

        rc = script_module.main(["--pr", "42", "--repo", "owner/repo"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "EMERGENCY BYPASS fired — logged" in out
        assert called_with["gate_name"] == "merge-review"
        assert called_with["env_var"] == "DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS"
        assert called_with["reason"].startswith("real malfunction recovery")

    def test_short_reason_rejected_gate_fails(self, script_module, monkeypatch, capsys):
        """A <20-char reason raises ValueError inside record_emergency_use;
        the script now catches that specifically and FAILS the gate with a
        diagnostic, rather than the prior swallow-and-pass behavior.

        Regression-pin: task #97 / 2026-06-08. Setting the env var to "x"
        used to pass the gate silently with no record. That was the
        bypass-cost-doesn't-exceed-tool-use bug.
        """
        monkeypatch.setenv("DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS", "x")

        def _raise_value_error(gate_name, env_var, reason):
            raise ValueError(f"emergency bypass {env_var} refused: reason must be >= 20 chars")

        monkeypatch.setattr(
            "divineos.core.emergency_bypass.record_emergency_use",
            _raise_value_error,
        )

        rc = script_module.main(["--pr", "42", "--repo", "owner/repo"])
        err = capsys.readouterr().err
        assert rc == 1, "short-reason bypass must FAIL the gate, not pass silently"
        assert "EMERGENCY BYPASS REJECTED" in err
        assert ">= 20 chars" in err

    def test_infra_failure_stays_loud_but_passes(self, script_module, monkeypatch, capsys):
        """A non-ValueError exception from record_emergency_use means the
        logging infrastructure broke (DB unavailable, etc) but the operator
        supplied a valid reason — the bypass still fires, but loudly,
        instructing manual post-incident filing.

        Distinguishes operator-discipline-failure (ValueError → gate fails)
        from infrastructure-failure (other exception → gate passes loud).
        """
        valid_reason = "genuine emergency — production credential rotation requires merge"
        monkeypatch.setenv("DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS", valid_reason)

        def _raise_runtime_error(gate_name, env_var, reason):
            raise RuntimeError("telemetry DB unreachable")

        monkeypatch.setattr(
            "divineos.core.emergency_bypass.record_emergency_use",
            _raise_runtime_error,
        )

        rc = script_module.main(["--pr", "42", "--repo", "owner/repo"])
        out = capsys.readouterr().out
        assert rc == 0, "infra failure with valid reason must still let bypass fire"
        assert "LOGGING FAILED" in out
        assert "Manually file" in out

    def test_unset_env_var_does_not_enter_bypass_branch(self, script_module, monkeypatch):
        """If the env var is absent, the bypass branch is never entered
        and the gate proceeds to its normal PR-data fetch.

        We can't easily test the full normal-path here without mocking gh,
        but we CAN verify that record_emergency_use is never called.
        """
        monkeypatch.delenv("DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS", raising=False)

        call_count = {"n": 0}

        def _spy(gate_name, env_var, reason):
            call_count["n"] += 1
            raise AssertionError("record_emergency_use must not be called when env unset")

        monkeypatch.setattr(
            "divineos.core.emergency_bypass.record_emergency_use",
            _spy,
        )

        # The non-bypass path fetches PR data via gh; without a real PR it
        # will hit "infrastructure error" (rc=2) or "no guardrail files"
        # (rc=0). Either way, record_emergency_use must NOT have been called.
        try:
            script_module.main(["--pr", "42", "--repo", "owner/repo"])
        except SystemExit:
            pass
        assert call_count["n"] == 0

    def test_empty_env_var_treated_as_unset(self, script_module, monkeypatch):
        """Setting the env var to "" or "   " (whitespace) must not trigger
        the bypass branch — same as unset. The `.strip()` + truthy-check
        ensures that.
        """
        monkeypatch.setenv("DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS", "   ")

        call_count = {"n": 0}

        def _spy(gate_name, env_var, reason):
            call_count["n"] += 1
            raise AssertionError("record_emergency_use must not be called for whitespace-only")

        monkeypatch.setattr(
            "divineos.core.emergency_bypass.record_emergency_use",
            _spy,
        )

        try:
            script_module.main(["--pr", "42", "--repo", "owner/repo"])
        except SystemExit:
            pass
        assert call_count["n"] == 0
