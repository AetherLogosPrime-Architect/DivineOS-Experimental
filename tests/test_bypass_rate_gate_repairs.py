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


class TestThresholdMovedWithTheField:
    """Aria's catch, claim 8628807d, and she was right to refuse the patch.

    Switching the comparison from total_events to escape_events without
    moving the threshold left a gate asking "are escapes >= 50" when escapes
    run about a fifth of totals. It could not fire. The repair disarmed the
    safety check while being reported as a repair.

    The verification that missed it used synthetic numbers -- 99 escapes and
    3 escapes -- neither anywhere near the live 15. A test whose fixtures sit
    far from production can be green about nothing, which is the same
    fake-green species being swept this session, authored by the sweeper.
    """

    def test_threshold_is_on_the_escape_scale_not_the_lumped_scale(self):
        gate = BypassRateScan()
        assert gate._threshold_events == 10, (
            "threshold must track the field it compares; 50 was calibrated "
            "against total_events and silently disables the gate on escapes"
        )

    def test_fires_at_the_observed_live_escape_level(self):
        """15 escapes is what the window actually held when this was written,
        and the narrative surface called that rate elevated. A blocking gate
        that stays silent while its own narrator says 'routed-around' is the
        two-consumers-disagreeing bug in a new costume."""
        gate = BypassRateScan()
        result = gate.scan(
            {"bypass_stats": _stats(escapes=15, total=70, top_env="DIVINEOS_SKIP_TESTS")}, ""
        )
        assert result is not None

    def test_stays_quiet_below_the_informational_surface(self):
        """bypass_telemetry narrates at 5. A gate that BLOCKS must be less
        twitchy than one that talks, or it becomes noise and gets bypassed --
        which is the habituation this gate exists to catch."""
        gate = BypassRateScan()
        result = gate.scan(
            {"bypass_stats": _stats(escapes=4, total=70, top_env="cmd:divineos goal")}, ""
        )
        assert result is None


class TestOffenderListSplitsLikeTheCount:
    """Found by the gate's own first honest fire, round-5b387cf59034.

    The count filtered to escapes and the top-three offender list did not, so
    one sentence read: "escape rate 15 exceeds threshold 10 ... compliance rows
    are excluded" and then named `divineos goal`, `ask` and `context` -- three
    commands gates PRESCRIBE, and rows that same sentence had just excluded.

    Worse than the lumped count it replaced. That one was wrong and LOOKED
    wrong; this one was right and READ wrong, and would send the next reader to
    investigate the wrong gates.
    """

    def test_offender_list_is_drawn_from_escapes_only(self):
        gate = BypassRateScan()
        stats = {
            "escape_events": 15,
            "total_events": 70,
            "by_env_var": {"cmd:divineos goal": 12, "DIVINEOS_SKIP_TESTS": 2},
            "by_env_var_escape": {"DIVINEOS_SKIP_TESTS": 2},
            "unique_days": 14,
            "window_days": 14,
        }
        result = gate.scan({"bypass_stats": stats}, "")
        assert result is not None
        assert "DIVINEOS_SKIP_TESTS" in result.specific_evidence
        assert "cmd:divineos goal" not in result.specific_evidence

    def test_falls_back_to_all_rows_when_the_split_is_absent(self):
        """An older stats provider must still name something rather than
        printing an empty offender list -- unknown is its own answer, but a
        blank is not."""
        gate = BypassRateScan()
        stats = {
            "escape_events": 15,
            "total_events": 70,
            "by_env_var": {"DIVINEOS_SKIP_TESTS": 15},
            "unique_days": 14,
            "window_days": 14,
        }
        result = gate.scan({"bypass_stats": stats}, "")
        assert result is not None
        assert "DIVINEOS_SKIP_TESTS" in result.specific_evidence

    def test_telemetry_emits_the_escape_only_breakdown(self):
        """The split lives at the source so both consumers read one thing."""
        from divineos.core.bypass_telemetry import bypass_rate

        stats = bypass_rate(window_days=14)
        assert "by_env_var_escape" in stats
        assert "by_env_var" in stats

    def test_both_exits_return_the_same_shape(self, tmp_path, monkeypatch):
        """The empty-log branch built its own dict literal and drifted three
        times: it was missing defect_escape_events and
        inferred_compliance_events while carrying a comment reading "Present on
        BOTH exits", and lost by_env_var_escape when that was added. One
        constructor now, so the shapes cannot diverge by hand."""
        from divineos.core import bypass_telemetry

        populated = bypass_telemetry.bypass_rate(window_days=14)
        monkeypatch.setattr(
            bypass_telemetry, "_event_log", lambda: tmp_path / "does-not-exist.jsonl"
        )
        empty = bypass_telemetry.bypass_rate(window_days=14)
        assert set(empty.keys()) == set(populated.keys())

    def test_escape_breakdown_never_exceeds_the_all_rows_breakdown(self):
        """Escapes are a subset of every row. If a key counts higher in the
        escape view than in the full one, the two loops have diverged."""
        from divineos.core.bypass_telemetry import bypass_rate

        stats = bypass_rate(window_days=14)
        every = stats.get("by_env_var", {})
        escapes = stats.get("by_env_var_escape", {})
        for key, count in escapes.items():
            assert count <= every.get(key, 0)


class TestTheDocstringDoesNotPromiseWhatTheCodeCannotDo:
    """Aria, 2026-08-25, by grep, an hour after I rewrote this docstring.

    It promised the threshold would "move with data as it accumulates" via
    compute_falsification_ratio, quoting Aletheia's line that a number which
    cannot move with evidence is ammunition. The number is assigned once and
    never changes. I corrected the stale NUMBER in that docstring and left the
    false CAPABILITY standing in the present tense.
    """

    def test_threshold_is_never_reassigned_after_construction(self):
        """If a calibration path is ever built, this fails and the docstring
        gets rewritten deliberately rather than drifting back into a promise."""
        import inspect

        from divineos.hooks import bypass_rate_scan

        source = inspect.getsource(bypass_rate_scan)
        assignments = [
            line
            for line in source.splitlines()
            if "_threshold_events" in line and "=" in line and "==" not in line
        ]
        assert len(assignments) == 1, (
            "the threshold is assigned in more than one place; if it can now "
            "move with evidence, say so in the docstring instead of leaving "
            "the correction that says it cannot"
        )

    def test_docstring_states_the_number_is_inherited_from_a_smoke_test(self):
        """The 50 was chosen to sit under the observed count so the wiring
        could be demonstrated -- it answered 'does this fire', never 'when
        should I be worried'. The 10 preserves its sensitivity, so it is
        faithful to a smoke-test and the file has to say so."""
        from divineos.hooks.bypass_rate_scan import BypassRateScan

        doc = BypassRateScan.__doc__ or ""
        assert "smoke-test" in doc
        assert "does not move" in doc.lower() or "DOES NOT MOVE" in doc


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
