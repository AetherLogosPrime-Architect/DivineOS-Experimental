"""Tests for the three bypass_rate_scan defects repaired 2026-08-25.

The gate blocked every substrate edit and could not be cleared through any of
the three exits it documents. Andrew authorised a marker bypass on condition
the defects got fixed; these pin the fixes.

Filed as audit round-7c8963ffa78a and claim b59f71c4. All three were found by
following the gate's own instructions and watching them fail:

  1. Timestamps. The ledger writes float epochs; the clearance check parsed
     them as ISO strings, so EVERY timestamp read as 0.0 and both the
     clearance path and the cool-off were dead. This is why filing a claim
     and then an audit round -- two of its three prescribed exits -- cleared
     nothing.
  2. Denominator. It thresholded on total_events, which counts COMPLIANCE
     rows: it blocked at 70 naming `divineos goal`, `ask` and `context` as
     top offenders, three commands gates prescribe.
  3. Marker path. Hand-built at ~/.divineos-aether/, a home nothing else
     reads. A marker there held this gate off for forty days unseen.
"""

from __future__ import annotations

from divineos.hooks.bypass_rate_hook import _parse_iso, _recent_clearance_within
from divineos.hooks.bypass_rate_scan import BypassRateScan


def _stats(*, escapes: int, total: int, top_env: str) -> dict:
    return {
        "escape_events": escapes,
        "total_events": total,
        "by_env_var": {top_env: escapes or total},
        "unique_days": 14,
        "window_days": 14,
    }


class TestTimestampParsing:
    def test_float_epoch_is_read_not_zeroed(self):
        """The defect. get_events returns floats; this returned 0.0 for all
        of them, and 0.0 means 'skip this event' everywhere it is used."""
        assert _parse_iso(1787693818.7120047) == 1787693818.7120047

    def test_integer_epoch_is_read(self):
        assert _parse_iso(1787693818) == 1787693818.0

    def test_iso_string_still_parses(self):
        """Ledgers change format. A reader that knows only one shape is how
        this bug happened; it must not become how the next one happens."""
        assert _parse_iso("2026-08-25T21:00:00+00:00") > 0

    def test_iso_with_z_suffix_parses(self):
        assert _parse_iso("2026-08-25T21:00:00Z") > 0

    def test_unparseable_returns_zero(self):
        assert _parse_iso("not a timestamp") == 0.0
        assert _parse_iso(None) == 0.0


class TestCooloffSeesFloatTimestamps:
    def test_recent_clearance_is_detected_with_float_timestamps(self):
        """The cool-off had its own inline copy of the broken parse, so the
        same defect killed it twice. One reader now."""
        import time

        now = time.time()

        def fake_get_events(event_type, limit=100, order="desc"):
            if event_type == "AUDIT_ROUND_CREATED":
                return [{"timestamp": now - 60, "payload": {}}]
            return []

        assert _recent_clearance_within("bypass_rate_scan", 3600.0, fake_get_events) is True

    def test_old_clearance_does_not_count_as_recent(self):
        import time

        now = time.time()

        def fake_get_events(event_type, limit=100, order="desc"):
            if event_type == "AUDIT_ROUND_CREATED":
                return [{"timestamp": now - 99999, "payload": {}}]
            return []

        assert _recent_clearance_within("bypass_rate_scan", 3600.0, fake_get_events) is False


class TestThresholdCountsEscapesOnly:
    def test_fires_on_real_escapes(self):
        gate = BypassRateScan()
        result = gate.scan(
            {"bypass_stats": _stats(escapes=99, total=200, top_env="DIVINEOS_SKIP_TESTS")}, ""
        )
        assert result is not None

    def test_does_not_fire_on_compliance_heavy_window(self):
        """200 rows, 3 of them escapes, the rest prescribed commands. Doing
        what a gate says is not routing around it."""
        gate = BypassRateScan()
        result = gate.scan(
            {"bypass_stats": _stats(escapes=3, total=200, top_env="cmd:divineos goal")}, ""
        )
        assert result is None

    def test_falls_back_to_total_when_classification_absent(self):
        """An unclassified window must still trip rather than silently pass --
        unknown is not the same as clean."""
        gate = BypassRateScan()
        result = gate.scan(
            {
                "bypass_stats": {
                    "total_events": 99,
                    "by_env_var": {"unknown": 99},
                    "unique_days": 14,
                    "window_days": 14,
                }
            },
            "",
        )
        assert result is not None

    def test_evidence_line_names_escapes_not_totals(self):
        """A correct figure under the wrong label still reads as the wrong
        claim."""
        gate = BypassRateScan()
        result = gate.scan(
            {"bypass_stats": _stats(escapes=99, total=200, top_env="DIVINEOS_SKIP_TESTS")}, ""
        )
        assert result is not None
        assert "escape_events=99" in result.specific_evidence
        assert "total_events=" not in result.specific_evidence
        assert "compliance rows" in result.specific_evidence


class TestMarkerPathUsesTheResolver:
    def test_hook_asks_member_home_instead_of_rebuilding_the_rule(self):
        """Sixth site to rebuild `$HOME/.divineos-$MEMBER` by hand. The
        previous marker at that path held this gate off for forty days in a
        home nothing else reads."""
        from pathlib import Path

        hook = (
            Path(__file__).resolve().parents[1]
            / ".claude"
            / "hooks"
            / "pre-tool-bypass-rate-scan.sh"
        )
        source = hook.read_text(encoding="utf-8")
        assert "member_home" in source
        assert '"$HOME/.divineos-aether/bypass-rate-scan.disabled"' not in source
