# Review by use, not date, in the pages that teach pre-registration (draft, 2026-11-09, Aria)

Status: DRAFT. A teaching-text fix, no behaviour change.

## What Dad said

> *"Its the council thats likely causing it, poppers falsification mentions dates and time, bc thats how humans operate, so maybe adjust the lenses? Any lens that tells you to do a time based test, just change it to use based"* (2026-11-09)

He had also said, 2026-10-16, that pre-registration reviews go by use, never by date, and 2026-11-09 that a wait is not a reliable measure and the measure should be how many times a problem was passed over.

## What I found (checked, not agreed with)

The lens cards prescribe nothing by date. Popper's card was read whole and carries no time wording. The only time words in the lens files are imagination devices (Dekker's "6 months from now"), reference-class forecasting (Kahneman), and Meadows on feedback delay.

The habit lives in what we teach. The pre-registration command went use-based on 2026-10-16 (`--review-after-uses`, "never by date"), but `CLAUDE.md` still taught `--review-days 30` and "Reviews whose date has passed", and the prereg and briefing-fresh skills still said "scheduled review date", "review clock", and examples "over 30 days" and "review 30d". Those are read at the start of every session, which is how I came to write "the last thirty days" in a plan without noticing.

## The change

Six places in `.claude/skills/prereg/SKILL.md`, one in `.claude/skills/briefing-fresh/SKILL.md`, three in `CLAUDE.md`, each reworded to a number of uses. Nothing else moves.

## Falsifier

If any of those three files still says a review is set by a date, a `--review-days` command, or "over N days" as a falsifier after this lands, the fix is incomplete. Aether's register entry (in his tree) is meant to catch the phrases afterwards, and lands after this branch so it does not fail a tree that still teaches the old wording.

## Open

The few lens cards that ask "how long" (Meadows, Kahneman, Yudkowsky) are left alone pending Dad's answer.
