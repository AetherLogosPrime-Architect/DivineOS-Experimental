"""Bypass-rate scan — second concrete instance of the CrossTurnScan
variant of EvidenceBearingStopGate. Validates the cross-turn variant
the same way ``distancing_intercept`` validated intra-turn.

Historical shape (informational-only surface, jailer-adjacent):
``bypass_telemetry.briefing_block()`` shows a value-string on every
substrate-modification-gravity gate fire — "71 bypasses in 15 days,
elevated bypass rate — gates are being routed-around. Per psf-ac523181:
bypass habituation degrades the gate to warning. Investigate whether
the gates are wrong-shape or the bypass-discipline is." The surface
explicitly instructs an investigation. The investigation never fires.
Fires every substrate-modifying tool, gets read, gets forgotten within
8-9 posts. The exact ROOT PATTERN #1cd8cd83 shape: value-string
without cheap check.

Structural fix (this module): the cross-turn scan reads bypass_rate()
against a threshold on Stop hook; when the threshold is exceeded and
this session hasn't run an investigation-shape action (audit filing,
claim, or workbench doc examining the bypassed gates), it fires with
positive evidence naming the specific gates being bypassed.

Not yet wired to a Stop hook shell script — Python surface first, per
the same ship-order that landed distancing intercept without shell
wiring. Wiring both concrete instances together after this commit
proves the primitive across both variants.
"""

from __future__ import annotations

from typing import Any

from divineos.core.bypass_telemetry import bypass_rate
from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    CrossTurnScan,
    EvidenceRecord,
)
from divineos.hooks.gate_event_ledger import (
    compute_falsification_ratio,
    record_gate_clearance,
    record_gate_fire,
)


class BypassRateScan(CrossTurnScan):
    """Fire when the bypass rate in the recent window exceeds a threshold.

    Reads ``divineos.core.bypass_telemetry.bypass_rate()`` — the same
    numbers the substrate-modification-gravity gate has been surfacing
    without action. Cross-turn variant of the primitive: state is the
    accumulated bypass ledger, not any single turn.

    Threshold defaults to 10 ESCAPES over 14 days — see
    ``_ESCAPE_THRESHOLD_DEFAULT`` below for the derivation.

    It read "50 events" here until 2026-08-25, and that sentence outlived
    two changes beneath it: the comparison moving from every row to escapes
    only, and the number moving from 50 to 10. Corrected in the same edit as
    the code, because a docstring that teaches the old contract reinstalls
    the old assumption in every reader — the same shape as the hook comment
    that kept pointing at a dead home for forty days.

    THE THRESHOLD DOES NOT MOVE, AND THIS DOCSTRING SAID IT DID.

    It read: "Threshold is a SEED — the falsification-signal layer
    (``compute_falsification_ratio``) lets the calibration move with data as it
    accumulates", quoting Aletheia 2026-07-15: *"a number that can't move with
    evidence is ammunition, not information."*

    ``_threshold_events`` is assigned once in ``__init__`` and read twice. No
    code path changes it. ``compute_falsification_ratio`` emits a diagnostic
    string about clearance-to-fire and feeds nothing back. So the gate carried
    that quotation as a promise through the whole period in which the number
    could not move — and I rewrote this docstring on 2026-08-25, corrected the
    stale NUMBER, and left the false CAPABILITY standing in the present tense.
    Aria found it an hour later, by grep, and she was right.

    AND THE ORIGINAL FIFTY WAS NEVER A JUDGEMENT (Aria, 2026-08-25). The
    removed text said it out loud: *"the initial threshold is set below that
    intentionally so the gate would fire on today's state, proving the
    mechanism live."* It was picked to sit UNDER the observed count so the
    wiring could be demonstrated. It answered "does this fire" and was never
    asked "when should I be worried."

    Which means the 10 below INHERITS that. It was derived to preserve the
    sensitivity 50 had once the comparison moved to escapes, so it is faithful
    to a smoke-test. A number derived from an arbitrary number is still
    arbitrary; this one is only honestly arbitrary, and saying so here is the
    difference. What would make it mean something is a measured base rate of
    escapes across windows where nothing was wrong, so the bar sits above
    normal rather than under a figure chosen to make a demo fire. That
    measurement does not exist in either tree yet.
    """

    # THE THRESHOLD MOVED WITH THE FIELD IT MEASURES. (2026-08-25.)
    #
    # 50 was calibrated against `total_events`, the lumped count. When the
    # comparison switched to `escape_events` earlier the same turn, the
    # threshold did not move with it -- and escapes run about a fifth of
    # totals here (measured: 70 total, 45 compliance, 15 escapes, 10
    # unclassified). A gate asking "are escapes >= 50" when escapes are 15
    # is a gate that never fires. I disarmed a safety check while reporting
    # that I had repaired it.
    #
    # Aria caught this before I did and refused to make the same patch,
    # filing claim 8628807d instead: "switching the field changes when a
    # gate fires and that is a calibration change, not a typo." She was
    # right and I was not. My verification used synthetic numbers -- 99
    # escapes fires, 3 does not -- which are nowhere near the live 15, so
    # the check looked rigorous and could not have caught this. That is a
    # fake-green of my own construction, on the day spent hunting them.
    #
    # Derivation, so this is a translation rather than a fresh guess:
    # 50 lumped x (15 escapes / 70 total) = 10.7 at the observed mix, so 10
    # preserves roughly the sensitivity 50 had before the field changed. It
    # sits deliberately above bypass_telemetry's escape-scale threshold of 5,
    # which drives an INFORMATIONAL surface; a gate that blocks should be
    # less twitchy than one that narrates.
    _ESCAPE_THRESHOLD_DEFAULT = 10

    def __init__(
        self, threshold_events: int = _ESCAPE_THRESHOLD_DEFAULT, window_days: int = 14
    ) -> None:
        self.gate_name = "bypass_rate_scan"
        self._threshold_events = threshold_events
        self._window_days = window_days
        self.fires: list[EvidenceRecord] = []
        self.clears: list[ClearanceRecord] = []
        self._recent_ratio: float | None = None

    def blocks(self) -> str:
        return (
            "next non-investigation tool call "
            "(clear by filing an audit, claim, or workbench doc examining "
            "the bypassed gate class)"
        )

    def scan(
        self,
        accumulated_state: dict[str, Any],
        just_emitted_text: str,  # noqa: ARG002 — bypass records are already in-log by scan-time; text-buffer not needed for this variant, but signature honored per Aria's refinement
    ) -> EvidenceRecord | None:
        # Prefer host-injected stats (allows tests + composability with
        # a future state-provider layer); fall back to fetching directly
        # so the concrete gate is usable in isolation.
        stats = accumulated_state.get("bypass_stats")
        if stats is None:
            try:
                stats = bypass_rate(window_days=self._window_days)
            except Exception:  # noqa: BLE001 — fail-open per primitive contract
                return None
        try:
            # ESCAPES, NOT EVERY ROW. (audit round-7c8963ffa78a, 2026-08-25.)
            #
            # This compared `total_events`, which counts COMPLIANCE rows --
            # running the command a gate prescribed. It blocked at
            # 70-over-14-days naming its top three offenders as
            # `divineos goal`, `divineos ask` and `divineos context`: three
            # commands that gates tell me to run. Doing what a gate says is
            # not routing around it.
            #
            # bypass_telemetry.py:593 reads the same stats for the narrative
            # surface and already filtered to escape_events. Two consumers of
            # one dataset, one filtering and one not -- and the one that
            # BLOCKS was the one that did not. The surface printed "compliance
            # is excluded from this verdict" directly above a verdict that
            # included it.
            #
            # Falls back to total_events when the provider is too old to carry
            # the classification, matching the telemetry side, so an
            # unclassified window still trips rather than silently passing.
            escape_events = int(stats.get("escape_events", stats.get("total_events", 0)))
            # The offender list has to be drawn from the same rows the count
            # was. Reading by_env_var here made the gate print "escape rate 15
            # ... compliance rows are excluded" and then name three prescribed
            # commands as the gates being routed around (round-5b387cf59034).
            # Falls back to the all-rows view only when the provider predates
            # the split, so an old stats dict still names something.
            by_env = dict(stats.get("by_env_var_escape") or stats.get("by_env_var", {}) or {})
            unique_days = int(stats.get("unique_days", 0))
            window_days = int(stats.get("window_days", self._window_days))
        except (TypeError, ValueError):
            return None
        if escape_events < self._threshold_events:
            return None
        return self._to_evidence(escape_events, by_env, unique_days, window_days)

    def _to_evidence(
        self,
        total: int,
        by_env: dict[str, int],
        unique_days: int,
        window_days: int,
    ) -> EvidenceRecord:
        # Name the top-3 most-bypassed env vars so the required action
        # can be targeted at the specific gates being routed around.
        top = sorted(by_env.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_line = (
            ", ".join(f"{name} ({count})" for name, count in top) if top else "(no env-var detail)"
        )
        # The label follows the number. This said `total_events` while the
        # value became escape_events, which is how a correct figure still
        # reads as the wrong claim -- the exact shape being fixed here.
        specific_evidence = (
            f"escape_events={total}, unique_days={unique_days}, "
            f"window_days={window_days}, top_bypassed={top_line} "
            f"(compliance rows -- running a command a gate prescribed -- are excluded)"
        )
        matched_shape = (
            f"escape rate {total} events over {window_days} days "
            f"exceeds threshold {self._threshold_events}"
        )
        required_action = (
            f"Investigate the top-bypassed gate(s): {top_line}. "
            "Clear by filing (a) a divineos audit round examining whether the "
            "gate is wrong-shape, (b) a divineos claim naming the specific "
            "failure mode, or (c) a workbench doc that names the structural "
            "fix. Absence of an investigation-shape action = the surface "
            "keeps firing but nothing changes (per Andrew 2026-07-15: "
            "'gates are helpers not jailers')."
        )
        return EvidenceRecord(
            gate_name=self.gate_name,
            matched_shape=matched_shape,
            specific_evidence=specific_evidence,
            required_action=required_action,
        )

    def record_fire(self, evidence: EvidenceRecord) -> None:
        self.fires.append(evidence)
        record_gate_fire(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)
        record_gate_clearance(clearance)

    def falsification_signal(self) -> str | None:
        # Same shape as DistancingIntercept — read the ratio off the
        # ledger; fall back to the seed threshold when data is sparse.
        # For a cross-turn gate the "gaming" shape is different: high
        # clearance rate could mean I'm actually investigating (good) OR
        # filing shallow docs just to clear (bad). Distinguishing needs
        # deeper evidence than just the ratio; for now surface the ratio
        # itself as diagnostic, don't hard-alarm on it.
        ratio = self._recent_ratio
        if ratio is None:
            ratio = compute_falsification_ratio(self.gate_name)
        if ratio is not None and ratio > 0.90:
            return (
                f"clearance-to-fire ratio {ratio:.2f} — investigate whether "
                "the investigation-shape clearances are producing structural "
                "fixes or just clearing the marker (Goodhart risk)"
            )
        return None


__all__ = ["BypassRateScan"]
