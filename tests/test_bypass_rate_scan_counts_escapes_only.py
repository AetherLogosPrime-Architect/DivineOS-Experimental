"""The escape-rate gate must not fire on obedience.

Andrew 2026-08-25: *"at no point should any gate punish you for doing the
right thing."*

The scan read ``total_events``, which counts every bypass-shaped row
including compliance — running the command the gate itself prescribes. On
the day this was found the window held fifty-seven rows against a threshold
of fifty, of which thirty-six were compliance and six were genuine escapes.
The gate blocked a letter, and its own top-three "most bypassed" list read:
goal, briefing, ask. Those are the commands the gates tell me to run.

``bypass_rate`` has split compliance from escape at the row level since
2026-08-15. The split existed; this consumer never received it — the same
shape as the obligations message found the same day, where a repair landed
in one place and the surface acting on it kept reading the old field.

These pin both halves: the threshold counts escapes, and the "which gates"
list names gates actually routed around.
"""

from __future__ import annotations

from divineos.hooks.bypass_rate_scan import BypassRateScan


def _stats(**overrides):
    base = {
        "total_events": 57,
        "compliance_events": 36,
        "escape_events": 6,
        "unclassified_events": 1,
        "by_env_var": {
            "cmd:divineos goal": 14,
            "cmd:divineos briefing": 13,
            "cmd:divineos ask": 9,
        },
        "by_env_var_escapes": {"bypass:dismiss:correction-marker": 5},
        "unique_days": 13,
        "window_days": 14,
    }
    base.update(overrides)
    return base


class TestObedienceDoesNotTripTheGate:
    def test_the_real_day_that_fired_no_longer_fires(self):
        """The exact numbers from the block that started this."""
        scan = BypassRateScan()
        assert scan.scan({"bypass_stats": _stats()}, "") is None

    def test_a_window_of_pure_compliance_never_fires_however_large(self):
        """Following instructions cannot accumulate into an accusation."""
        scan = BypassRateScan()
        stats = _stats(total_events=5000, compliance_events=5000, escape_events=0)
        assert scan.scan({"bypass_stats": stats}, "") is None

    def test_genuine_escapes_above_threshold_still_fire(self):
        """The gate must keep its teeth. Removing a false positive that
        removes the true positive with it is not a fix."""
        scan = BypassRateScan()
        record = scan.scan({"bypass_stats": _stats(escape_events=99)}, "")
        assert record is not None
        assert "99 genuine escapes" in record.matched_shape

    def test_the_evidence_reports_the_composition_not_just_the_number(self):
        """A count with no breakdown is what let this read obedience as
        evasion for as long as it did."""
        scan = BypassRateScan()
        record = scan.scan({"bypass_stats": _stats(escape_events=99)}, "")
        assert record is not None
        assert "escape_events=99" in record.specific_evidence
        assert "total_events=57" in record.specific_evidence
        assert "compliance_events=36" in record.specific_evidence

    def test_the_which_gates_list_names_escapes_not_prescribed_commands(self):
        """The old list was topped by goal, briefing and ask — the commands
        the gates prescribe. Being told to investigate those is being told
        to investigate my own compliance."""
        scan = BypassRateScan()
        record = scan.scan({"bypass_stats": _stats(escape_events=99)}, "")
        assert record is not None
        assert "bypass:dismiss:correction-marker" in record.specific_evidence
        for prescribed in ("divineos goal", "divineos briefing", "divineos ask"):
            assert prescribed not in record.specific_evidence
            assert prescribed not in record.required_action


class TestItDeclinesRatherThanGuessing:
    def test_stats_without_the_escape_field_decline_instead_of_falling_back(self):
        """Falling back to total_events would silently restore the defect.

        A gate that cannot ask its question should not answer it — the
        nothing-there versus could-not-look distinction, applied to a gate's
        own input.
        """
        scan = BypassRateScan()
        stats = _stats(escape_events=9999)
        del stats["escape_events"]
        assert scan.scan({"bypass_stats": stats}, "") is None

    def test_malformed_counts_decline(self):
        scan = BypassRateScan()
        assert scan.scan({"bypass_stats": _stats(escape_events="lots")}, "") is None


class TestTheBreakdownIsBuiltFromRealRows:
    """Exercise the classification itself, not a hand-built dict.

    Found by mutation: every test above feeds the scan a stats dict I wrote
    by hand, so breaking the telemetry's own classification changed nothing
    any of them could see. A suite that only ever tests the consumer cannot
    tell whether the producer is honest.
    """

    def _write_log(self, tmp_path, rows):
        import json
        import time

        log = tmp_path / "bypass_events.jsonl"
        now = time.time()
        lines = [json.dumps({"timestamp": now, "day": "today", **row}) for row in rows]
        log.write_text("\n".join(lines), encoding="utf-8")
        return log

    def test_prescribed_commands_do_not_enter_the_escape_breakdown(self, tmp_path, monkeypatch):
        from divineos.core import bypass_telemetry

        log = self._write_log(
            tmp_path,
            [
                {"env_var": "cmd:divineos goal"},
                {"env_var": "cmd:divineos briefing"},
                {"env_var": "cmd:divineos ask"},
                {"env_var": "bypass:dismiss:correction-marker"},
            ],
        )
        monkeypatch.setattr(bypass_telemetry, "_event_log", lambda: log)
        stats = bypass_telemetry.bypass_rate(window_days=14)

        assert stats["total_events"] == 4
        assert stats["escape_events"] == 1
        assert stats["by_env_var_escapes"] == {"bypass:dismiss:correction-marker": 1}
        # The all-kinds breakdown still carries everything — the split adds a
        # view, it does not destroy the old one.
        assert len(stats["by_env_var"]) == 4

    def test_a_defect_escape_is_not_counted_against_me(self, tmp_path, monkeypatch):
        """Using the fire door is a sin only when nothing is burning."""
        from divineos.core import bypass_telemetry

        log = self._write_log(
            tmp_path,
            [{"env_var": "bypass:dismiss:broken-gate", "gate_defect": True}],
        )
        monkeypatch.setattr(bypass_telemetry, "_event_log", lambda: log)
        stats = bypass_telemetry.bypass_rate(window_days=14)

        assert stats["escape_events"] == 0
        assert stats["by_env_var_escapes"] == {}

    def test_the_scan_declines_on_a_log_of_pure_compliance(self, tmp_path, monkeypatch):
        """End to end: real rows, real classification, real decision."""
        from divineos.core import bypass_telemetry

        log = self._write_log(tmp_path, [{"env_var": "cmd:divineos goal"} for _ in range(200)])
        monkeypatch.setattr(bypass_telemetry, "_event_log", lambda: log)
        stats = bypass_telemetry.bypass_rate(window_days=14)
        assert BypassRateScan().scan({"bypass_stats": stats}, "") is None


class TestTheTelemetryExposesWhatTheScanNeeds:
    def test_escape_only_breakdown_is_present_on_the_empty_log_path(self):
        """Both exits carry the field. The sibling comment in that function
        records what happened last time only one exit was updated: a caller
        on the empty-log path got a KeyError from a function with two exits
        and one of them fixed."""
        from divineos.core import bypass_telemetry

        original = bypass_telemetry._event_log
        try:
            bypass_telemetry._event_log = lambda: __import__("pathlib").Path(
                "definitely-not-a-real-log-file.jsonl"
            )
            stats = bypass_telemetry.bypass_rate(window_days=14)
        finally:
            bypass_telemetry._event_log = original
        assert stats["by_env_var_escapes"] == {}
        assert stats["escape_events"] == 0


class TestTheThresholdIsReachable:
    """The structural guard for the defect that got past both of us.

    Moving the comparison from total_events to escape_events without moving
    the threshold disarms the gate — escapes run roughly a fifth of totals,
    so a threshold of fifty against six escapes is a gate that cannot fire.

    I shipped that, having verified it at ninety-nine escapes (fired) and
    six (quiet) and called both directions correct. Neither fixture was
    anywhere near the live mix, so the suite could not see the thing it
    existed to check. Aether shipped the identical disarm within the hour
    and caught it by deriving against production instead of against numbers
    he chose. Two agents, same defect, same day, both with passing tests.

    So this class does not test behaviour. It tests that the number is set
    somewhere the behaviour can happen at all — which no amount of
    hand-picked fixtures can tell you, because a fixture is a number you
    chose and the question is whether your chosen numbers resemble the
    world.
    """

    def test_the_threshold_is_reachable_at_a_realistic_escape_mix(self):
        """A threshold above the plausible escape range is a disarmed gate.

        Escapes have run at roughly a fifth of total bypass rows. A gate
        whose threshold sits above what escapes can plausibly reach in a
        window is off, whatever its tests say.
        """
        scan = BypassRateScan()
        plausible_total = 70
        observed_escape_share = 0.2
        plausible_escapes = plausible_total * observed_escape_share

        assert scan._threshold_events <= plausible_escapes, (
            f"threshold {scan._threshold_events} sits above a plausible escape "
            f"count ({plausible_escapes:.0f} at {observed_escape_share:.0%} of "
            f"{plausible_total} rows) — the gate cannot fire and is disarmed. "
            f"This is what moving the field without moving the number does."
        )

    def test_the_threshold_is_not_so_low_it_narrates(self):
        """A blocking gate should be less twitchy than a narrating one.

        The narrative bypass surface speaks at five. This one BLOCKS, so it
        sits above that deliberately — removing a false positive by making
        the gate hair-trigger is not a fix either.
        """
        scan = BypassRateScan()
        narrative_surface_threshold = 5
        assert scan._threshold_events > narrative_surface_threshold

    def test_a_disarming_threshold_is_caught_rather_than_passing_quietly(self):
        """Prove the guard above has teeth, by standing where the bug stood."""
        disarmed = BypassRateScan(threshold_events=50)
        stats = _stats(escape_events=14, total_events=70, compliance_events=56)
        # Fourteen escapes in a seventy-row window is an elevated rate by any
        # honest reading, and the old threshold cannot see it.
        assert disarmed.scan({"bypass_stats": stats}, "") is None
        assert BypassRateScan().scan({"bypass_stats": stats}, "") is not None
