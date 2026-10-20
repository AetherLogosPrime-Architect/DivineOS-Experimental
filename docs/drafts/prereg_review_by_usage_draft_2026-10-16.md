# A pre-registration is reviewed when it has been used, not when a date arrives (draft, 2026-10-16)

Author: aether

## What Dad said
2026-10-16: *"we do not do reviews by dates but by usage itself"*, then: *"you have a pull to do the date thing so you need some structural support to make sure it always goes by use or events, as i could go on vacation for 30 days come back and you have no data.. or even worse it takes 30 days for the issue to sit there and pile up before its addressed.. all of this machinery is deterministic it doesnt take that many runs to determine if it works correctly"*.

## What is wrong
`divineos prereg file` schedules a review `--review-days` out and the overdue gate fires on the calendar. Two failures follow. The date can arrive with nothing used (a vacation), so the review demands a verdict with no data and the only exits are a fabricated verdict or a deferral. Or the mechanism is used heavily and its fault sits for weeks before anyone looks. I wrote two 30-day reviews this morning without noticing; the form invited it, because days are the only unit it offers. That is the pull he named, and a note I must remember is not a fix.

## The change (truth 11: take the option away)
A pre-registration is filed with a usage trigger: `--review-after-uses N --uses-of EVENT_TYPE`. EVENT_TYPE is a ledger event type. It is due when the ledger has recorded N more events of that type since filing. The CLI no longer accepts a calendar review for a new filing. The date is not a backstop either: a vacation must not make a review overdue, so a usage-based row is never overdue by date.

Proof the instrument can find a case (CLAUDE.md rule 9): filing is refused if the ledger has no event of that type at all, because a count that can never move reads as "not due" forever.

Old rows with no usage trigger keep their date, so nothing already filed changes behaviour.

## Not doing
No new system: columns on the existing table, a count helper on the ledger, the overdue query extended. No guessing which event a mechanism "should" count; the filer names it.

## Tests
- file with a usage trigger records the baseline; due only after N more events of the type
- a usage row whose date has long passed is NOT overdue; a legacy row whose date passed still is
- filing against an event type with no events is refused
- the CLI refuses a filing with no usage trigger
- mutation: make the date count for usage rows and the vacation test fails

## Falsifier
If a usage-based review is ever overdue by date, or a review sits more than its N uses past due without surfacing, this is wrong.
