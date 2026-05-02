"""Tests for anti-slop — runtime enforcer verification.

Locks three invariants:

1. All checks run without unhandled exceptions on the live module set.
2. Each check reports a passed + detail. detail is non-empty.
3. summarize() returns (total, passed, failed) consistent with
   individual results.
4. On a healthy codebase, all registered checks pass.
"""

from __future__ import annotations

from divineos.core.anti_slop import (
    SlopCheckResult,
    run_all_checks,
    summarize,
)


class TestRunAllChecks:
    def test_returns_non_empty_list(self):
        results = run_all_checks()
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_every_result_is_slop_check_result(self):
        for r in run_all_checks():
            assert isinstance(r, SlopCheckResult)

    def test_every_result_has_name_and_detail(self):
        for r in run_all_checks():
            assert r.name
            assert r.detail

    def test_every_result_has_bool_passed(self):
        for r in run_all_checks():
            assert isinstance(r.passed, bool)


class TestSummarize:
    def test_summarize_counts_correctly(self):
        fake = [
            SlopCheckResult("a", True, "ok"),
            SlopCheckResult("b", True, "ok"),
            SlopCheckResult("c", False, "fail"),
        ]
        total, passed, failed = summarize(fake)
        assert total == 3
        assert passed == 2
        assert failed == 1

    def test_summarize_empty(self):
        total, passed, failed = summarize([])
        assert total == 0
        assert passed == 0
        assert failed == 0


class TestLiveEnforcementHealth:
    """The actual point of anti-slop: on a healthy codebase, every
    registered check should pass. If this test starts failing, it
    means either a real enforcer has regressed OR the anti-slop check
    for that enforcer is wrong. Either requires attention."""

    def test_all_registered_enforcers_pass_on_healthy_codebase(self):
        results = run_all_checks()
        total, passed, failed = summarize(results)

        failures = [r for r in results if not r.passed]
        assert failed == 0, (
            f"{failed}/{total} enforcer(s) failed anti-slop: "
            f"{[(r.name, r.detail) for r in failures]}"
        )


class TestSpecificEnforcerCoverage:
    """Each shipped enforcer must have an anti-slop check. This test
    locks the list so adding a new enforcer without adding a check is
    visible as a test failure, not silent coverage gap."""

    def test_expected_enforcers_are_checked(self):
        names = {r.name for r in run_all_checks()}
        # Lite: family-based (reject_clause/sycophancy_detector/access_check)
        # and logic-based (fallacy_detector) enforcers stripped. Full DivineOS
        # keeps the full set.
        expected = {
            "hedge_monitor",
            "corrigibility",
        }
        missing = expected - names
        assert not missing, f"Enforcers missing from anti-slop registry: {missing}."


class TestResultDataclassFrozen:
    def test_result_is_frozen(self):
        import pytest

        r = SlopCheckResult("test", True, "detail")
        with pytest.raises((AttributeError, Exception)):
            r.passed = False  # type: ignore[misc]
