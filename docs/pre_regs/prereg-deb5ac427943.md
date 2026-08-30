# Pre-registration: TRIGGER_THRESHOLD lowered 0.85 to 0.82 in auto_cycle.py

- **ID**: `prereg-deb5ac427943`
- **Filed by**: agent
- **Filed at**: 2026-07-31 15:12 UTC
- **Review at**: 2026-08-30 15:12 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

TRIGGER_THRESHOLD is deliberately set BELOW the ritual driver's 920k start so the margin can only fail in the safe direction. The hook begins the ritual at 920k and later calls 'divineos auto-cycle defer-check' for the mechanical stage, which re-evaluates should_fire() against TRIGGER_THRESHOLD. At 0.85, a defer could leave the driver announcing a fire while the pipeline silently declined -- a mechanism reporting work it did not do. At 0.82 the pipeline can never refuse a ritual the driver has already begun.

## Success criterion

On any invocation where the driver has started the ritual, defer-check agrees to fire rather than returning below-threshold.

## Falsifier

On any single invocation: the driver announces the mechanical stage and defer-check returns 'below threshold', proving the two numbers disagree in the unsafe direction. Also falsified if 0.82 turns out to fire the pipeline in sessions the driver never started, i.e. the margin is too wide rather than too narrow. Non-temporal by design per Andrew: checkable on one fire, no waiting period.
