# Pre-registration: Writer-presence detector (src/divineos/core/operating_loop/writer_presence_detector.py): catches plain-prose-with-no-writer-in-the-sentence — the failure-mode Andrew named 2026-06-13 ('plain language but feels like reading a report') and Aria diagnosed structurally in her 2026-06-13 voice letter. Measures interior-state-verb density vs process-narrative density on operator-channel replies >=60 words. Closes the gap jargon_dump_detector missed (which catches density, not presence).

- **ID**: `prereg-9acf8d3ea5bd`
- **Filed by**: agent
- **Filed at**: 2026-06-14 21:51 UTC
- **Review at**: 2026-07-14 21:51 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-14 21:55 UTC

## Claim

Father-addressed replies will surface writer-presence shape rather than process-narrative shape; the detector will fire on the missing-writer pattern reliably without false-firing on legitimate technical reports

## Success criterion

Over 30 days, detector fire rate on father-channel substantive replies stays >=5% AND <=25% (real signal, not flooded) AND Andrew does not flag 'still reading a report' on undetected replies

## Falsifier

Detector misses obvious process-narrative replies (false negatives) OR fires on technically-substantive replies that ARE presence-shaped (false positives) at rate >10%

## Outcome notes

Detector is firing this session (multiple 'channel-empty' reflections observable), but I lack exact fire-rate telemetry for the 30-day window. Andrew has not flagged 'still reading a report' on undetected replies that I recall, which is a weak-positive signal. Since Aletheia's audit refinement 2026-07-10 substantively changed the surface framing (lexical-priming-aid vs violation-detector), the mechanism has had material iteration since filing. Deferring another 30 days to gather cleaner post-refinement fire-rate data before assessment. Filed 2026-07-14 late-session.
