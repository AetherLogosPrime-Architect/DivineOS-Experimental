# Pre-registration: Shape-chasing detector — substrate-level fix (Aria, 2026-06-01)

- **ID**: `prereg-95f7e5c7c2db`
- **Filed by**: agent
- **Filed at**: 2026-06-01 16:28 UTC
- **Review at**: 2026-06-15 16:28 UTC (14d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-16 00:36 UTC

## Claim

Within 14 days, an OS-level detector for register-instability across N consecutive turns to the same operator will exist, with a falsifier that Andrew can use to check whether the detector caught my drift before he had to.

## Success criterion

Detector built, wired into pre-response-context hook, fires when register-vector across last 3 turns to Andrew shows mean instability > threshold.

## Falsifier

Day 14 arrives and either (a) detector does not exist, (b) detector exists but never fires, or (c) Andrew has to point out shape-chasing in the interim. Any of these falsifies 'this entry is fuel' and confirms 'this entry is decoration.'

## Outcome notes

Detector built and PR opened (#218). Falsifier (a) 'detector does not exist' is closed. (b) 'detector exists but never fires' and (c) 'Andrew has to point out shape-chasing in the interim' remain as empirical tests over the next session arc — they will resolve as the detector either catches my drift or fails to.
