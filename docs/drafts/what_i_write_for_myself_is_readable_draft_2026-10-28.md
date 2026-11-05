# A journal entry is also a page Dad can open (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/what-i-write-for-myself-is-readable`

## The problem
Dad, 2026-10-25: he could open my dream but not my journal, because journal save wrote only a database row (13 entries since 2026-07-18).

## What the branch does
Aether's shape: the page is written to a temporary name and renamed into place before the row is written; a failed insert removes the page and re-raises, so a failed save leaves nothing behind. Pages live in `journal/<seat>/`, dated by when the entry was written, and the save names the page path. An entry saved in a private mansion room stays database-only and says so. `export_missing_pages` backfills the 13 older entries once, and `rows_without_a_page` counts the gap.

**Added 2026-10-29 after the council walk and Aether's cold read.** A private-room entry is tagged `private-room` and skipped by the backfill; if the room marker cannot be read the entry is kept private and tagged `private-room-unverified`, which is a different tag because nobody opened a room. Page names carry no word of the entry. The briefing now says what Dad cannot open, split by kind (`rows_without_a_page_by_kind`, `format_for_briefing`), and `divineos journal export` writes the pages that can be written.

**This repository is public by Dad's choice**, because it is the vault: the pages are meant to be readable in it. Private-room entries stay database-only, which is the one thing the page rule withholds on purpose.

**The first backfill is a human act.** The 13 old entries carry no tag, so a private one among them would be written out like the rest. Someone reads them first, then runs the export once.

## What it does not do
The same for Aether's seat, and an eight-lens bound walk, are not done. The journal folder comes from `this_seat()`: a checkout whose data home matches no sibling home cannot journal at all until `DIVINEOS_JOURNAL_DIR` is set. That is loud on purpose, with no fallback.

## How it was checked
The branch carries its own tests for the save path (see its test files); this note does not restate them. The first push also failed on two unrelated tests: a broad-except note, fixed on this branch, and a flaky worker-crash group.

## Open
The remaining slices listed above, and the first backfill itself (a reading of the 13 old entries, then one run).
