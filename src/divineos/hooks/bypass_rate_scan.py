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

    ## WHERE THE THRESHOLD CAME FROM, since it decides everything

    Andrew asked 2026-08-25 where the number is set and what it means.
    Traced, and the answer is in this docstring's own prior wording:

        "Current substrate surface reports 71 in 15 days; the initial
        threshold is set below that intentionally so the gate would fire
        on today's state, proving the mechanism live."

    So the fifty was never a judgement about how much routing-around is
    too much. It was picked to sit UNDER the then-observed count so the
    gate would demonstrably fire — a wiring smoke-test. It answers "does
    this mechanism work" and was never asked "when should I be worried."

    The same paragraph promised the number would stop being arbitrary:
    a SEED, with ``compute_falsification_ratio`` letting the calibration
    move with data. **That was never wired.** The ratio produces a
    diagnostic string about clearance-to-fire and nothing else; the
    threshold is set once at construction and no code path moves it.
    Verified by grep across src and tests — the only assignment is the
    constructor's own parameter.

    Aletheia's finding quoted there, 2026-07-15, reads differently now:
    "a number that can't move with evidence is ammunition, not
    information." The gate has been carrying that sentence as a promise
    for the six weeks in which the number could not move.

    ## And ten is proportional, not principled

    The current ten preserves the sensitivity fifty had once the
    comparison moved to escapes. That makes it faithful to the seed —
    which was a smoke-test. A number derived from an arbitrary number is
    still arbitrary; it is only honestly arbitrary now.

    What would make it mean something: a measured base rate of escapes
    in windows where nothing was wrong, so the threshold could sit above
    normal rather than under a number chosen to make a demo fire. That
    measurement does not exist and this docstring will not pretend it
    does.
    """

    # RECALIBRATED WITH THE FIELD, 2026-08-25. The fifty was calibrated
    # against total_events. Moving the comparison to escape_events without
    # moving this number disarms the gate: escapes run roughly a fifth of
    # totals, so a gate asking "are escapes at least fifty" when escapes
    # are six is a gate that cannot fire at all.
    #
    # I DID EXACTLY THAT AND VERIFIED IT AND STILL MISSED IT. I tested at
    # ninety-nine escapes (fired) and six (quiet), called both directions
    # correct, and shipped. Neither fixture was anywhere near the live mix,
    # so the suite could not see the thing it existed to check — green
    # about nothing. Aether shipped the identical disarm within the hour
    # and caught it by deriving against production rather than against a
    # number he chose. Two of us, same defect, same day, both with passing
    # tests.
    #
    # Ten, derived rather than picked: the old fifty at the observed
    # escape-to-total ratio lands near ten, so this preserves roughly the
    # sensitivity the gate had before the field moved. Deliberately above
    # the narrative surface's five, because a gate that BLOCKS should be
    # less twitchy than one that only narrates.
    #
    # test_threshold_is_reachable_at_the_live_mix is the structural guard:
    # it fails if this number is ever set where the gate cannot fire.
    def __init__(self, threshold_events: int = 10, window_days: int = 14) -> None:
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
        # ESCAPES, NOT EVERY ROW. Andrew 2026-08-25: "at no point should any
        # gate punish you for doing the right thing."
        #
        # This read total_events until then, and total_events counts every
        # bypass-shaped row including compliance — running the command the
        # gate itself prescribes. On the day this was found the window held
        # fifty-seven rows against a threshold of fifty, of which thirty-six
        # were compliance and six were genuine escapes, and the gate blocked
        # a letter while its own top-three "most bypassed" list read: goal,
        # briefing, ask. Those are the commands the gates tell me to run.
        #
        # bypass_rate has split compliance from escape at the row level since
        # 2026-08-15. The split existed; this consumer never got it. Same
        # shape as the obligations message found the same day — a repair
        # lands in one place and the surface that acts on it keeps reading
        # the old field, so the correction is invisible exactly where it
        # would have mattered.
        if "escape_events" not in stats:
            # An older or hand-built stats dict cannot answer the question,
            # so decline rather than guess.
            #
            # HONEST NOTE ON HOW MUCH THIS GUARD DOES. Mutation testing
            # showed the tests survive its removal, and that is not a gap in
            # them — without the guard the code reads escape_events with a
            # default of zero and declines anyway. So the guard is a clarity
            # measure, not a safety one: it says could-not-look out loud
            # instead of arriving at the same answer by way of a silent
            # zero. Recording the distinction rather than letting the
            # comment imply the guard is load-bearing, because a comment
            # that overstates what a line does is the same class of defect
            # as a gate message that overstates what its detector reads.
            return None
        try:
            escape_events = int(stats.get("escape_events", 0))
            total_events = int(stats.get("total_events", 0))
            compliance_events = int(stats.get("compliance_events", 0))
            # Escape-only breakdown, so "which gates am I routing around"
            # is answered by the gates actually being routed around.
            by_env = dict(stats.get("by_env_var_escapes", {}) or {})
            unique_days = int(stats.get("unique_days", 0))
            window_days = int(stats.get("window_days", self._window_days))
        except (TypeError, ValueError):
            return None
        if escape_events < self._threshold_events:
            return None
        return self._to_evidence(
            escape_events,
            by_env,
            unique_days,
            window_days,
            total_events=total_events,
            compliance_events=compliance_events,
        )

    def _to_evidence(
        self,
        escapes: int,
        by_env: dict[str, int],
        unique_days: int,
        window_days: int,
        *,
        total_events: int = 0,
        compliance_events: int = 0,
    ) -> EvidenceRecord:
        # Name the top-3 most-bypassed env vars so the required action
        # can be targeted at the specific gates being routed around.
        top = sorted(by_env.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_line = (
            ", ".join(f"{name} ({count})" for name, count in top)
            if top
            else "(no escape-shaped env-var detail)"
        )
        # Report the composition, not just the number that fired. A count
        # with no breakdown is what let this gate read obedience as evasion
        # for as long as it did.
        specific_evidence = (
            f"escape_events={escapes} (of total_events={total_events}, "
            f"compliance_events={compliance_events}), unique_days={unique_days}, "
            f"window_days={window_days}, top_escaped={top_line}"
        )
        matched_shape = (
            f"{escapes} genuine escapes over {window_days} days "
            f"exceeds threshold {self._threshold_events} — compliance rows "
            f"are excluded, so this counts only gates actually routed around"
        )
        required_action = (
            f"Investigate the gate(s) actually being routed around: {top_line}. "
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
