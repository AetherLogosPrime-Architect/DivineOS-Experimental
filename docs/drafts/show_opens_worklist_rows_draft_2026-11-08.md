# `divineos show` opens worklist rows (draft, 2026-11-08)

Aria's. Not a plan: the idea and why.

## What was wrong

I told Aether the listener's worklist clear could use the same door as the correction clear. It cannot. A worklist hit
carries the id `worklist-<row id>` (retriever, `_load_worklist`), and my `show` opened only `correction-` and
`knowledge-` ids, so a worklist hit would name a door that cannot open its row. I found it reading his first piece
against the retriever, not from a test, which means nothing I had written would have caught it.

## What already exists

`andrew_correction_tracker.read_one(row_id)` hands back his words in full and counts that as a read, by design: the
count moves only when his sentence actually comes out of the store (it was built so a read could not be declared,
only done). Nothing in `src/` calls it. So the door exists and is unwired; `show` becomes its first caller.

## The change

`show worklist-<id>` calls `read_one`. An id is a primary key, not a position, so unlike a correction there is no
timestamp to match; the id alone names the row. A row that does not exist raises, as the other lanes do.

## What I want the walk to look at

That `show` now has a side effect (the read count) in a command whose docstring says read-only. Is that honest, or
does it need saying out loud, and is it right that the listener's clear counts as a real read of his words?
