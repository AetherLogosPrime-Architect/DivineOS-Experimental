# Pre-registration: record_intention: new write verb for the intention/deferral category (currently zero modules)

- **ID**: `prereg-227f9d066e4d`
- **Filed by**: agent
- **Filed at**: 2026-07-20 02:33 UTC
- **Review at**: 2026-08-19 02:33 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Adding a record_intention() write verb parallel to record_lesson/store_knowledge will convert the currently-invisible category of intentions and deferrals (Phase-2 designs, dead_architecture_alarm detections, quiet-room-style shelf-designs) from prose-that-evaporates into retrievable rows the surfacer can reach at compose-time.

## Success criterion

Over the next 30 sessions: (a) at least 5 intentions filed via record_intention that would previously have lived only in prose, (b) at least 1 surface fire that references a filed intention to Andrew, (c) Aletheia audits and confirms the category has non-zero modules and the write path is exercised.

## Falsifier

If after 30 sessions record_intention has been called <=1 time, or if the surfacer never references any filed intention, the verb is another dead architecture and should be removed. If filed intentions accumulate without ever being fulfilled/abandoned/superseded (lifecycle unused), the verb is missing its close-verbs and should not have been shipped alone.
