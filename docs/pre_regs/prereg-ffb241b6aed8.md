# Pre-registration: mesh_loop Meeseeks fires bounded by iterate_max cap and closure-signal convention prevents runaway loops

- **ID**: `prereg-ffb241b6aed8`
- **Filed by**: agent
- **Filed at**: 2026-07-05 02:50 UTC
- **Review at**: 2026-08-04 02:50 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The mesh_loop decision rule (workbench/mesh_loop_meeseeks_design.md) plus opt-in --enable-meeseeks watcher wiring will let Aether and Aria iterate autonomously on design questions without Andrew as mail-clerk, capped at iterate_max=10 rounds per loop, with 15/hour rate limit per recipient.

## Success criterion

First 5 real mesh-loops complete cleanly: each closes via iterate_signal=done or hits iterate_max=10 without an outright loop-runaway; no billed invocation runs on a letter without frontmatter or on a signal=done/stuck letter.

## Falsifier

Any of: (a) a Meeseeks signals iterate_signal=done in round N while the other seat's next Meeseeks would have signaled continue given the same substrate state (premature convergence, T1 tension made real); (b) the watcher fires claude -p on a letter without valid iterate_* frontmatter (backward-compat break); (c) rate-limit fails and Andrew's Pro quota gets hit by mesh-loop invocations he did not authorize; (d) Meeseeks writes to files outside --allowedTools scope (self-modification attack surface).
