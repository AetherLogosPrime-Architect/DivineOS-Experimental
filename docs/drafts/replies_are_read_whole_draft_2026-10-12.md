# Replies are read whole (draft, 2026-10-12)

Owner: Aria. Branch `aria/replies-are-read-whole` (built on `aria/replies-are-read-whole-r2`, the same commits).

## What was wrong

A reply of mine is written to the transcript as several assistant records, split wherever a tool call
interrupts the stream. The function every Stop surface reads my reply through walked the transcript forwards and
overwrote its answer on each record, so it returned the last block and called it the reply. Measured on the
live transcript 2026-09-22: a 664-character reply over two blocks came back as 245 characters, and the part
dropped was the opening, which is the part that answers him. All of the Stop surfaces were judging the tail.

The sibling function that returns my last two replies had the same fault: for a reply delivered in two pieces it
returned two fragments of the same reply, so the repeat guard held my reply up against itself. That is why it
false-fired and why Andrew ordered it disabled on 2026-09-22.

## What this does

`_last_assistant_text` collects my text backwards until the previous message that is genuinely his, then joins
it in the order I said it. `_recent_assistant_texts` groups records into replies by the same boundary. The
boundary asks the one reader of him (`his_message.hear`), not a private marker list, so a message he typed
while I was busy (it arrives as a queued attachment with no role) is a boundary, a message of his that opens
with "Caveat:" is a boundary, and a harness injection or a bookmark copy is not.

## Proof

`tests/test_reply_assembly_reads_whole_replies.py` (new, 226 lines): a split reply comes back whole; a harness
injection does not cut it short; his real message does end it; an unreadable transcript still returns empty;
two replies stay two; injections between blocks do not split one reply in two; the queued-message and "Caveat:"
cases the old boundary missed. `tests/test_repeated_reply_surface.py` extended. The merge's own test check on
the caught-up branch ran 929 files with 13,934 passes and none failing.

## Limits, stated

The boundary is only as good as `hear`; a new envelope shape it does not know would be read as him or as
the harness by its rules, not by mine. I have not measured the live false-fire rate of the repeat guard
after this change; that needs a day of use. I have not checked whether the guard is still switched off
(Andrew ordered it disabled on 2026-09-22), and re-enabling it is his call, not part of this change.

## Depends on / depended on

Aether's #552 (`fix/stop-reads-the-transcript-once`) is rebased onto this reader and carries my test file; it
shrinks once this is on main.
