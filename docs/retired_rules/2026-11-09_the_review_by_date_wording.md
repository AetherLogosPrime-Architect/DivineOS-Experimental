<!-- retired-rule
id: review-by-date-wording
retired: 2026-08-12
retired-by: Andrew
successor: pre-registrations are reviewed by USE, never by date or days. File with --review-after-uses N and --uses-of <event type>; the briefing surfaces the ones whose use count has been reached. See the prereg skill.
pattern: --review-days\b
pattern: (?i)\breview clock\b
pattern: \bReviews whose date has passed\b
-->

# The review-by-date wording

**Retired 2026-08-12 by Andrew. Archived 2026-11-09, after the teaching pages were found still using it.**

## What it said

A pre-registration is filed with a review date: `divineos prereg file ... --review-days 30`, "scheduled review date", "review clock", "over 30 days", and `prereg overdue` described as "reviews whose date has passed".

## Why it was retired

Andrew, 2026-08-12: *"at no point should time duration be used as a falsifier.. it should all be based on N-events or something similar."* A duration is a decay an agent cannot observe from inside; a clock can be consumed by the very defect it was meant to bound. The code followed on 2026-10-16 with `--review-after-uses` and `--uses-of`. The teaching pages kept the old wording: CLAUDE.md, the prereg skill and the briefing-fresh skill. On 2026-11-09 he said time keeps appearing as a metric and asked whether the council was why. Aria checked the lens cards instead of agreeing: none prescribes a test by date. The habit was in the pages that teach.

## What replaced it

Review by use: `--review-after-uses N --uses-of <event type>`. Reviews come due when that many events of that type have happened, not when days pass.

## What this does not catch

The machinery still carries legacy rows with a review date, and `prereg overdue` still reports those as overdue by days. Source comments that describe that legacy data ("review date has passed") are accurate for it and are deliberately NOT registered, so a clean run says nothing about them. A rule restated in other words, for example "revisit after a month", also passes. The patterns match only the exact instruction wording that was found on the teaching pages.
