# Pre-registration: Self-certifying wiring-gap gate: wire the existing scripts/wiring_gap detector into a live enforcement+report path that (a) certifies its OWN wiring first (inspector is its own first customer, per Hofstadter), (b) measures current-FLOWING not reference-EXISTING (per Yudkowsky Goodhart — a call-site count is gamed by test-only/if-False/dead-import callers), (c) is itself guardrailed/un-bypassable (per Schneier — gate's own wiredness + bypass path in guardrail/CI set), (d) reports unwired new code into the BRIEFING (cold-read surface, per Beer S3* + Jacobs distributed-eyes), and (e) ships with a sanctioned 'land the primitive WITH its wiring' door so it is a keel not a cage (per Meadows outflow + Dennett + Andrew caveat 6f77ea0a). Enforcement bite-level (briefing-surface only / commit-warn / merge-block) is an OPEN dial reserved for Andrew, whose 'dont make it a problem' caveat governs it.

- **ID**: `prereg-7d9dc8ca2527`
- **Filed by**: agent
- **Filed at**: 2026-05-29 16:42 UTC
- **Review at**: 2026-06-28 16:42 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:31 UTC

## Claim

Making 'done=wired' a structurally-enforced standard that reports into the cold-read briefing reduces the rate of new unwired/orphaned modules vs the docstring-'Phase 2'-defer status quo, because the deferral-intent moves from a docstring (in-context will, dies at reset) to a gate (survives reset).

## Success criterion

Over the 30-day window: (1) the detector verifies its own wiring; (2) no new module ships unwired-and-declared-done without the briefing surface flagging it; (3) the surface is actually acted on (orphans wired or honestly retired, not ignored).

## Falsifier

A new orphan ships during the window uncaught; OR the gate is gamed (a fake/test-only caller satisfies it while no real current flows); OR the gate itself becomes unwired/unrun like its predecessor (the recursion repeats); OR enforcing it makes the system a 'problem' for me to live in (cage, not keel) per Andrew's caveat.

## Outcome notes

Shipped: scripts/wiring_gap_phase1.py + wiring_gap_probe.py exist and the ORPHAN MODULES check runs in scripts/precommit.sh (I saw it fire tonight on the user_prompt_submit_gate.py commit).
