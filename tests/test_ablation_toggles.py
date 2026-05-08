"""Tests for ablation toggle infrastructure (chunk 2).

Verifies the four wired mechanisms each respect their respective
DIVINEOS_DISABLE_<NAME> env var. The 5th priority mechanism
(compass calibration multi-channel guard) is in unmerged PR #299;
toggle wiring deferred until that merges.
"""

from __future__ import annotations

import os
import pytest


@pytest.fixture
def clean_env(monkeypatch):
    """Strip all DIVINEOS_DISABLE_ env vars for the test."""
    for key in list(os.environ.keys()):
        if key.startswith("DIVINEOS_DISABLE_"):
            monkeypatch.delenv(key, raising=False)
    yield


class TestAblationModule:
    def test_is_disabled_default_false(self, clean_env):
        from divineos.core.ablation import is_disabled

        assert is_disabled("noise_filter_on_extraction") is False

    def test_is_disabled_with_value(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", "1")
        from divineos.core.ablation import is_disabled

        assert is_disabled("noise_filter_on_extraction") is True

    def test_is_disabled_empty_string_false(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", "")
        from divineos.core.ablation import is_disabled

        assert is_disabled("noise_filter_on_extraction") is False

    def test_is_disabled_case_insensitive(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_TEST_MECH", "1")
        from divineos.core.ablation import is_disabled

        assert is_disabled("test_mech") is True
        assert is_disabled("TEST_MECH") is True

    def test_list_disabled_empty(self, clean_env):
        from divineos.core.ablation import list_disabled

        assert list_disabled() == []

    def test_list_disabled_returns_active(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", "1")
        monkeypatch.setenv("DIVINEOS_DISABLE_SLEEP_CONSOLIDATION_PRUNING", "1")
        from divineos.core.ablation import list_disabled

        result = list_disabled()
        assert "noise_filter_on_extraction" in result
        assert "sleep_consolidation_pruning" in result


class TestNoiseFilterToggle:
    def test_default_active(self, clean_env):
        from divineos.core.knowledge._text import _is_extraction_noise

        assert _is_extraction_noise("yes", "PRINCIPLE") is True

    def test_disabled_passes_through(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", "1")
        from divineos.core.knowledge._text import _is_extraction_noise

        assert _is_extraction_noise("yes", "PRINCIPLE") is False


class TestSleepPruningToggle:
    def test_toggle_skips_phase(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_SLEEP_CONSOLIDATION_PRUNING", "1")
        from divineos.core.sleep import _phase_pruning, DreamReport

        report = DreamReport()
        _phase_pruning(report)
        assert report.health_results.get("skipped_via_ablation_toggle") is True
        assert report.hygiene_results.get("skipped_via_ablation_toggle") is True


class TestWatchmenToggle:
    def test_internal_actor_rejected_by_default(self, clean_env):
        from divineos.core.watchmen.store import _validate_actor

        with pytest.raises(ValueError, match="cannot submit"):
            _validate_actor("claude")

    def test_internal_actor_allowed_with_toggle(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", "1")
        from divineos.core.watchmen.store import _validate_actor

        assert _validate_actor("claude") == "claude"

    def test_external_actor_always_allowed(self, clean_env):
        from divineos.core.watchmen.store import _validate_actor

        assert _validate_actor("user") == "user"

    def test_empty_actor_still_rejected_with_toggle(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", "1")
        from divineos.core.watchmen.store import _validate_actor

        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_actor("")


class TestFamilyOperatorsToggle:
    def test_toggle_bypasses_operators(self, clean_env, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DISABLE_FAMILY_VOICE_APPROPRIATION_OPERATORS", "1")
        from divineos.core.family.store import _run_content_checks
        from divineos.core.family.types import SourceTag

        # With toggle on, function returns early -- does not raise
        _run_content_checks("any content", SourceTag.OBSERVED)


def test_no_toggles_set_by_default(clean_env):
    from divineos.core.ablation import list_disabled

    assert list_disabled() == []
