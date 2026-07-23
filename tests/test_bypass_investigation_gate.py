"""Tests for task #18 escape-hatch enforcement:

1. bypass_telemetry.record_bypass auto-files a pending structural fix
   with source_kind="bypass_use" via structural_fix_tracker.
2. pipeline_gates.enforce_bypass_investigation_gate returns False (blocks)
   when unresolved bypass_use entries exist, True (passes) otherwise.

Uses monkeypatched paths for isolation — writes go to a tmp dir and
do not touch the real substrate.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Point divineos_home() and marker_path() at a tmp dir so tests
    do not pollute the real substrate or read from it.

    Both bypass_telemetry and structural_fix_tracker read paths via
    the same functions; monkeypatching them isolates writes cleanly.
    """
    tmp_home = tmp_path / "divineos_home"
    tmp_home.mkdir(exist_ok=True)

    def fake_divineos_home():
        return tmp_home

    def fake_marker_path(name: str):
        return tmp_home / name

    # Patch in both modules (they import the functions directly)
    monkeypatch.setattr("divineos.core.paths.divineos_home", fake_divineos_home)
    monkeypatch.setattr("divineos.core.paths.marker_path", fake_marker_path)
    monkeypatch.setattr("divineos.core.bypass_telemetry.divineos_home", fake_divineos_home)
    monkeypatch.setattr("divineos.core.structural_fix_tracker.marker_path", fake_marker_path)

    return tmp_home


class TestBypassAutoFiles:
    """record_bypass must file a pending structural fix on every event."""

    def test_bypass_creates_pending_entry(self, isolated_paths):
        from divineos.core.bypass_telemetry import record_bypass
        from divineos.core.structural_fix_tracker import list_pending

        record_bypass(
            gate_name="test_gate",
            env_var="DIVINEOS_TEST_BYPASS",
            reason="unit test",
        )
        pending = list_pending(include_done=False)
        bypass_entries = [e for e in pending if e.get("source_kind") == "bypass_use"]
        assert len(bypass_entries) == 1
        entry = bypass_entries[0]
        assert "test_gate" in entry.get("content_excerpt", "")
        assert entry.get("trigger") == "bypass:DIVINEOS_TEST_BYPASS"
        assert entry.get("status") == "pending"

    def test_bypass_content_includes_reason(self, isolated_paths):
        from divineos.core.bypass_telemetry import record_bypass
        from divineos.core.structural_fix_tracker import list_pending

        record_bypass(
            gate_name="briefing_gate",
            env_var="DIVINEOS_SKIP_BRIEFING",
            reason="chicken-and-egg during rebase",
        )
        entries = [e for e in list_pending() if e.get("source_kind") == "bypass_use"]
        assert entries
        assert "chicken-and-egg" in entries[0].get("content_excerpt", "")

    def test_bypass_without_reason_still_files(self, isolated_paths):
        from divineos.core.bypass_telemetry import record_bypass
        from divineos.core.structural_fix_tracker import list_pending

        record_bypass(gate_name="g", env_var="X")
        entries = [e for e in list_pending() if e.get("source_kind") == "bypass_use"]
        assert len(entries) == 1


class TestBypassInvestigationGate:
    """enforce_bypass_investigation_gate returns False (block) when
    unresolved bypass_use entries exist, True (pass) otherwise."""

    def test_no_pending_passes(self, isolated_paths):
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate

        assert enforce_bypass_investigation_gate() is True

    def test_one_pending_blocks(self, isolated_paths):
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate
        from divineos.core.bypass_telemetry import record_bypass

        record_bypass(gate_name="g", env_var="X", reason="test")
        assert enforce_bypass_investigation_gate() is False

    def test_multiple_pending_blocks(self, isolated_paths):
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate
        from divineos.core.bypass_telemetry import record_bypass

        record_bypass(gate_name="g1", env_var="X1", reason="one")
        record_bypass(gate_name="g2", env_var="X2", reason="two")
        assert enforce_bypass_investigation_gate() is False

    def test_resolved_pending_no_longer_blocks(self, isolated_paths):
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate
        from divineos.core.bypass_telemetry import record_bypass
        from divineos.core.structural_fix_tracker import list_pending, mark_done

        record_bypass(gate_name="g", env_var="X", reason="test")
        entries = [e for e in list_pending() if e.get("source_kind") == "bypass_use"]
        assert len(entries) == 1
        psf_id = entries[0]["id"]
        mark_done(psf_id, note="structural fix landed at abc123")
        assert enforce_bypass_investigation_gate() is True

    def test_non_bypass_pending_does_not_block(self, isolated_paths):
        """Only source_kind=bypass_use entries should trigger this gate.
        Other pending fixes (from learn, correction, etc.) are handled
        by the briefing dashboard surface, not this gate."""
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate
        from divineos.core.structural_fix_tracker import record_pending_fix

        record_pending_fix(
            content="a learn-sourced structural fix",
            source_kind="learn",
        )
        assert enforce_bypass_investigation_gate() is True

    def test_mixed_kinds_only_bypass_blocks(self, isolated_paths):
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate
        from divineos.core.bypass_telemetry import record_bypass
        from divineos.core.structural_fix_tracker import record_pending_fix

        record_pending_fix(content="a learn fix", source_kind="learn")
        record_bypass(gate_name="g", env_var="X", reason="test")
        # bypass_use is present → block
        assert enforce_bypass_investigation_gate() is False

    def test_gate_fails_open_on_tracker_error(self, isolated_paths, monkeypatch):
        """If structural_fix_tracker.list_pending raises (broken state),
        the gate returns True — a broken enforcement mechanism should
        not silently block ALL extracts. Failure surfaces via warning.
        Uses a direct patch on list_pending rather than __import__
        monkeypatching (which recurses through linecache/logger)."""
        from divineos.cli.pipeline_gates import enforce_bypass_investigation_gate

        def raise_oserror(**kwargs):
            raise OSError("simulated broken tracker state")

        monkeypatch.setattr(
            "divineos.core.structural_fix_tracker.list_pending",
            raise_oserror,
        )
        assert enforce_bypass_investigation_gate() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
