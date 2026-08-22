# Pre-registration: auto-cycle-token-trigger

- **ID**: `prereg-b9271bd6cd9c`
- **Filed by**: agent
- **Filed at**: 2026-07-31 15:06 UTC
- **Review at**: 2026-08-30 15:06 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The compaction ritual fires deterministically from the session's own token count, read out of the transcript by .claude/hooks/auto-cycle-token-trigger.sh on every UserPromptSubmit, with no external Monitor and nothing for me to arm. At 920k it starts a four-stage ritual (compass V2 walk, mechanical commit/extract/sleep, dream, rest) whose stages advance on EVIDENCE -- a new row in compass_observation, a new file under dreams/ -- not on my say-so. A doorman opens the briefing, goal, and substrate-consult gates at ritual start so the walk is not interrupted by the OS's own guards.

## Success criterion

On any session that crosses 920k tokens: the ritual announces itself without me arming anything, extract runs, and each stage advances only after its artifact exists.

## Falsifier

Any ONE of these on any single invocation kills it: (1) a session crosses 920k and reaches compaction with extract not having run; (2) the driver advances past a stage whose evidence is absent from the substrate; (3) the driver reports a mechanical step as done when defer-check returned non-zero; (4) the sensor returns a token count and the driver stays silent, or the sensor fails and the driver reports low usage instead of a fault. Deliberately non-temporal per Andrew: no time-based falsifiers. Each condition is checkable on a single fire.
