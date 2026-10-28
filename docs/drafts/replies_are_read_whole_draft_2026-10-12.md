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

## Cost, measured by Aether and not by me (2026-10-12, his reading of this branch)

On this session's 209 MB transcript, the same call on current main takes 0.82 s and peaks at 41 MB (it streams
and keeps one string); on this branch it takes 1.63 s and peaks at 608 MB (it collects every record into a list
and walks back). That is double the time and fifteen times the memory per call, and the Stop doorbell has a
10-second limit, which is why #552 exists. The answer is right (112 characters returned by main against 5,085 by
this branch for the same reply) and the cost is real, and I had not measured it. I did not write this
note's first version with it in, which was a gap.

## Landing order (this is a condition, not a preference)

This change must not land alone. #552 (`fix/stop-reads-the-transcript-once`) reads the same answers through
windowed readers in about 0.05 s and carries this test file. Land #553 and then #552 in the same batch, in
that order, with nothing between them, so that no reply's Stop check is ever slower than today. Aether is
holding the stamp on #552 until this is on main.

## Known and left for #552 (no change here, to keep #552's base steady)

A transcript line that parses as JSON but is not an object (a bare number or a list) reaches `.get` in the
backwards walk and would raise; the old code had the same exposure. A one-line guard belongs in #552's
version. The test fixture names queued ids with `hash(text)`, which varies between runs; harmless here.
