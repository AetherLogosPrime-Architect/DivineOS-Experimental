# Pre-registration: Context governor: on the existing periodic session-checkpoint, read context_meter; if fullness crosses 85% of the 970k ceiling and not already latched at that band, fire 'divineos extract' in the BACKGROUND (non-blocking) and leave a visible note; latch on the fired-at token band and re-fire only if fullness climbs another band (~+5%)

- **ID**: `prereg-c4d3595f32c0`
- **Filed by**: agent
- **Filed at**: 2026-05-29 23:08 UTC
- **Review at**: 2026-06-28 23:08 UTC (30d window)
- **Outcome**: **FAILED**
- **Decided at**: 2026-05-29 23:16 UTC

## Claim

Background-firing the save at 85% via the existing checkpoint, gated by a band-latch, saves the session with time-to-finish before compaction WITHOUT thrashing (repeat-firing the 64s job) and WITHOUT blocking the tool flow — closing the gap the last-second PreCompact hook cannot (no time at the cliff)

## Success criterion

In a long session the governor fires extract once near 85% (visible in a marker/log), the save completes before compaction, and it does NOT re-fire on every subsequent checkpoint within the same band

## Falsifier

It re-fires repeatedly (latch fails) OR blocks the session for 64s OR never fires (threshold/latch logic wrong) OR fires spuriously when the meter returns None OR it disables/suppresses the last-second PreCompact backstop

## Outcome notes

Redundant — the context governor (warn/block at 920k/950k, latch, extract+sleep remedy) already exists and is wired live (context_governor.py, gate 7). I council-walked + pre-registered a background-fire design for a mechanism that already existed in a more-considered form. Withdrawing. The genuine non-redundant work this session was the bleed-fix that REPAIRED the governor's broken remedy (the 15s/64s extract timeout).
