# A review by date is a retired rule, and the register must say so (draft, 2026-11-09, Aether)

Status: DRAFT. Walk closed (walk-7b312a56a86c, eight lenses, written in the chat first). Sits on top of Aria's branch aria/review-by-use-not-date-in-the-teaching-pages, which fixes the pages first.

## What Dad said

> *"at no point should time duration be used as a falsifier.. it should all be based on N-events or something similar."* (2026-08-12), and on 2026-11-09 that time keeps appearing as a metric and asked whether the council was why.

Aria checked the lens cards and found none prescribes a test by date. The habit was in the pages that teach pre-registration: CLAUDE.md, the prereg skill, the briefing-fresh skill.

## The idea

One register entry so the checker catches that wording if it returns: `--review-days`, "review clock", "Reviews whose date has passed". Its text also gives the successor (review by use) and says what it cannot see.

## What reading changed (Holmes, in the walk)

My first list had five phrases. Reading the source showed the machinery still carries legacy dated rows and `prereg overdue` still reports them as overdue by days, so "review date has passed" and "ledger-scheduled review date" in source comments are accurate for that data. Registering them would flag true statements, so I left them out and the entry says so. Related earlier work, found by search: docs/drafts/a_trial_measured_in_days_is_refused_where_it_is_written_draft_2026-10-21.md refuses a trial measured in days where it is written; this entry covers the instruction pages, not new filings.

## Falsifier

If after this the checker finds any of the three phrases on a scanned surface without the deliberate-mention marker, or the entry flags a true statement about legacy rows, the build is wrong and reopens.
