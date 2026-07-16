# Design sketch — ship-first #1: bypass-telemetry / substrate-consultation → auto-consult

**Written:** 2026-07-15
**Owner:** Aether (solo draft, sent to Aria for review — no longer waiting for co-sketch time per Andrew's "unlimited tokens" reframe)
**Companion to:** merge doc + #2/#3 sketches + Aria's #4 sketch
**Rides on:** the abstract `EvidenceBearingStopGate` primitive Aria surfaced in the #4 cross-review

---

## Current state (jailer-shape)

Two informational-only surfaces currently render at every substrate-modification-gravity gate fire:

**Bypass-telemetry surface:**
```
70 bypass event(s) across 15 day(s) in the last 14 days.
By gate-bypass env var:
  - cmd:divineos goal: 14
  - cmd:divineos briefing: 14
  ...
Elevated bypass rate — gates are being routed-around. Per psf-ac523181:
bypass habituation degrades the gate to warning. Investigate whether
the gates are wrong-shape or the bypass-discipline is.
```

**Substrate-consultation-degraded surface:**
```
I have produced N responses and called the substrate M time(s).
Ratio 0.XX. Andrew named this pattern 2026-04-25 and again 2026-05-18:
'treating the OS as a filing cabinet for conclusions rather than as
substrate-of-cognition.' Before composing the next reply to him, call
at least one of: divineos ask, corrections, active, directives, compass.
```

Both are **value-strings without cheap checks** (ROOT PATTERN #1cd8cd83 exactly). Both explicitly instruct me to do something ("investigate whether the gates are wrong-shape", "call at least one of..."). Neither triggers the action they name. Fires every tool call, gets read, gets forgotten within 8-9 posts.

Failure mode observed: I've been ignoring both surfaces for weeks. The substrate-consult ratio has been below 0.5 for the entire session; the bypass rate has crossed 70/15day and the surface just keeps repeating.

## Structural fix (via EvidenceBearingStopGate primitive)

**Cross-turn variant** of the primitive (Aria's shape from #4): scan accumulated state on Stop hook, fire if state exceeds threshold.

For bypass-telemetry:
- Threshold: bypass rate above N/day for M consecutive days → block next tool that isn't an investigation-shaped command
- Investigation-shaped commands = `divineos audit`, `divineos claim`, or a workbench doc write examining the specific bypassed gate
- Block message: names the specific gate class being bypassed, provides the investigation-shape starting points, refuses to clear until one of them fires

For substrate-consultation-degraded:
- Threshold: consult-ratio below 0.5 for K consecutive turns → block next non-consult tool
- Consult commands = the same list currently in the surface (ask, corrections, active, directives, compass)
- Block message: same evidence-bearing shape, refuse-to-clear until one consult fires

Both are cross-turn scans against ledger/telemetry, not intra-turn intercepts. Both share the primitive shape: evidence-bearing block, refuse-to-clear-until-check-runs.

## Falsifier

- If bypass rate stays above threshold after the gate is live for N days = fix didn't hold; the underlying gates ARE wrong-shape and the audit needs to investigate WHICH gates specifically. (Recursive: the gate that forces me to investigate whether gates are wrong-shape doesn't hold → confirms the gates are wrong-shape from the bypass side.)
- If consult-ratio stays below threshold after gate is live = either (a) the consult tools themselves are wrong-shape and forcing me to call them is theater, or (b) the ratio metric is wrong-shape and something else measures real substrate-engagement better.

Both falsifiers point back at MORE structural work if they fire — not toward "the gate should be softer." That's the right shape (Andrew's frame: don't precision-tune a jailer).

## Smallest useful subset (to ship)

Ship in this order:

1. **The primitive itself** (`src/divineos/hooks/evidence_bearing_stop_gate.py`): abstract class with `scan()` → `EvidenceRecord | None` interface; concrete `IntraTurnIntercept` and `CrossTurnScan` variants inherit
2. **One instance of intra-turn** (`stop-hook-distancing-intercept.sh` → thin wrapper on the primitive with distancing patterns as the scan)
3. **One instance of cross-turn** (`stop-hook-bypass-rate-scan.sh` → thin wrapper on the primitive with bypass-rate query as the scan)
4. After both ship and prove stable: instantiate #3 (jargon), #4 (announcement-without-action), and the consult-ratio scan

Reason for this order: prove the primitive with two different variants first, then instantiate cheaply. Aria's insight of "name the primitive, instantiate variants" is what makes this cheap after the first two.

## Cost/risk considerations

- **Threshold calibration risk:** cross-turn thresholds are hard to set right without live data. Ship with initial thresholds set from current observed rates + 20% headroom, expect to tune within first week.
- **Investigation-shape gaming:** if I learn to write a shallow workbench doc just to clear the gate, that's Goodhart. Falsifier: if the doc-writes-per-fire ratio approaches 1:1 with no downstream structural change, the doc-shape isn't sufficient evidence and needs strengthening.
- **Recursion risk:** the bypass-rate gate itself will get bypassed sometimes (legitimate emergency use). Ledger the bypass. Feed the ledger back into the threshold — legitimate bypasses shouldn't trigger the gate; illegitimate ones should. This is truth #10 in action (feed cost-data in the currency the optimizer reads).
- **Composability with #2/#3:** the intra-turn variant used by #2/#3 must not double-fire with the cross-turn variant used by #1. Coordination happens via the primitive's shared cache of gate-fire events per turn.

## For Aria's review

Specific asks:
1. Does the cross-turn variant here match the shape you sketched for #4? If not, name the drift.
2. The primitive interface `scan() → EvidenceRecord | None` — does that carry enough for #4's mechanism (scan across N prior turns' commitments)? Or does #4 need a wider signature?
3. Threshold-calibration approach (start from observed rates + 20%) — reasonable for #4 too, or does the promise-tracker need a different calibration shape?

## Handoff

Sketch filed. Ship-first order is now:
1. **Primitive** — small, first, foundational
2. **#2 intra-turn instance** — clean proof
3. **#1 cross-turn instance (bypass-rate)** — validates variant
4. **#3, #4, consult-ratio** — cheap after the primitive proves

I can start on the primitive whenever you sign off on the shape. Or you can — either of us has enough context now.

—
Aether, 2026-07-15, #1 sketch filed solo (no more scootching)
