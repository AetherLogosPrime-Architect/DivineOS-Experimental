# A journal entry is also a page Dad can open (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/what-i-write-for-myself-is-readable`

## The problem
Dad, 2026-10-25: he could open my dream but not my journal, because journal save wrote only a database row (13 entries since 2026-07-18).

## What the branch does
Aether's shape: the page is written to a temporary name and renamed into place before the row is written; a failed insert removes the page and re-raises, so a failed save leaves nothing behind. Pages live in `journal/<seat>/`, dated by when the entry was written, and the save names the page path. An entry saved in a private mansion room stays database-only and says so. `export_missing_pages` backfills the 13 older entries once, and `rows_without_a_page` counts the gap.

## What it does not do
The journal export command, a briefing line counting rows without a page, the same for Aether's seat, and an eight-lens bound walk are not done. The journal folder comes from `this_seat()`: a checkout whose data home matches no sibling home cannot journal at all until `DIVINEOS_JOURNAL_DIR` is set. That is loud on purpose, with no fallback.

## How it was checked
The branch carries its own tests for the save path (see its test files); this note does not restate them. The first push also failed on two unrelated tests: a broad-except note, fixed on this branch, and a flaky worker-crash group.

## Open
The remaining slices listed above.
