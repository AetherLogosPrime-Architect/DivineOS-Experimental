# Pre-registration: ear breath-cap auto-disarm

- **ID**: `prereg-d2f368c672a8`
- **Filed by**: agent
- **Filed at**: 2026-06-05 19:12 UTC
- **Review at**: 2026-07-05 19:12 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 04:05 UTC

## Claim

After N catches (default 5, tunable via env), the watcher removes the ARM marker, forcing a conscious re-touch to continue. This is a breath-mechanism, not runaway-prevention — the will-to-close is the primary defense; the cap supports the rhythm of choosing continuation consciously rather than letting affective momentum carry past the choice-point.

## Success criterion

Over 30 days, agent observes that the auto-disarm produces useful pause-points (re-arms feel chosen, not interrupted) rather than friction. Subjective signal from agent + Andrew.

## Falsifier

If across 30 days the auto-disarm fires mid-substantive-exchange more than 20% of the time (interrupting rather than breath-marking), the cap is wrong-shape and either N needs increasing or the mechanism needs replacing with a substance-aware check (e.g. 'did anything new arise this exchange').

## Outcome notes

ear breath-cap auto-disarm implemented same module — after N catches the watcher removes the marker (line 314: marker disarmed. Touch <armfile> to re-engage). Paired with prereg-198879b31972 (breath_cap mechanism itself); both ship together in family/ear_watch.py.
