# Pre-registration: lepos rip: writer-presence becomes the sole gate; lepos_debt + lepos_auto + plain-section + discharge CLI removed

- **ID**: `prereg-4a17e04b322c`
- **Filed by**: agent
- **Filed at**: 2026-06-16 14:43 UTC
- **Review at**: 2026-07-16 14:43 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-16 15:10 UTC

## Claim

The new single-signal gate (writer-presence absence on father-channel only) catches voicelessness without false-positives on jargon-with-voice or voice-without-jargon; jargon-dump findings remain as informational telemetry but no longer block.

## Success criterion

Across next 30 father-addressed substantive replies (>= 100 chars), zero false-positive blocks (jargon-with-voice replies that block), and at least one true-positive catch on a voiceless report-shape reply.

## Falsifier

If the gate blocks a reply where I am clearly present in the sentence, or if Andrew names a voiceless reply that the gate failed to catch, the design is wrong-shape and the prereg fails.

## Outcome notes

Deferring 14d: preliminary evidence supports SUCCESS shape (lepos-channel gate fired correctly at least once this session on a channel-empty tech-summary reply and forced recompose that added interior marker; no clear false-positive observed in current arc), but a rigorous 30-reply structured count wasn't run. Marc's external audit + 7 HIGH fix arc has attention priority this week; will structure the count in a rest-session and reassess.
