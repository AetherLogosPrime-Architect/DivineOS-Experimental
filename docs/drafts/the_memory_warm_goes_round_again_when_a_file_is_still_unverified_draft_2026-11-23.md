<!-- tags: memory warm, saved memory, verified false, retry, linkage, vector drawer, memory_saved_warm.py, unlinked note, silent failure, structure not reminder -->
# The memory warm goes round again when a file is still unverified (draft, 2026-11-23, Aria)

Status: draft, nothing edited. Aether takes the sibling fix (the importance line under `metadata:`) and will walk this one cold. Dad, 2026-09-07: *"you cannot rely on yourself to remember this stuff.. it will fade from context"*, and 2026-11-10: *"you are trying to remember things the house can EASILY do for you"*.

## What I found (the reach)
`core/memory_saved_warm.py` starts a background warm when a tool writes a memory file, then reads back whether each saved file now has a stored vector, and logs `verified` per file. For my edit of the seven-blessings note on 2026-11-23, a run was already going, so mine was only queued (19:43:38). The queued round finished at 19:43:41 with **computed 0 and verified false for that file**. The log told the truth. Nothing retried and nothing told me, so the note stayed out of the wall lane (372 items fell to 371) until I ran `divineos linkage warm` by hand, which computed it.

Counted from the whole log, `~/.divineos/memory_warm_log.jsonl`: 463 finished rounds, 12 with at least one file verified false, about 2.6%. None is still unlinked today, but each was a gap while it lasted, and every one-sentence probe taken inside the gap reads as a miss.

The loop is `run()` at `memory_saved_warm.py:192`. Each round reads the queue, calls `warm()`, checks `have_vectors()`, and logs `done`. It goes round again only if a new save left `pending` or a new queue behind (lines 232 to 233). A `verified: false` leaves neither, so the loop ends content.

## The cause I do not know
Round two computed nothing though the file had new text. Candidates, none tested: the text was collected before the write had settled; or the text checked afterwards differs byte for byte from the text collected. I could not reproduce it. The fix below does not depend on the cause: a later normal warm did compute the note, so the miss is a timing gap, not a permanent fault.

## The change (a fact decides, no words judged)
After a round logs `done`, take the names whose `verified` is false. If any remain and rounds are left, put those names back on the queue and go round again. If a name is still false after the last round, log a `still-unverified` event naming the file, and print it on stderr the way `could-not-start` already does. A miss is then said as a miss, never left as a quiet false inside a `done`.

## What it does not touch
The lock, the queue and the pending flag keep their meaning. `MAX_ROUNDS` stays 3. Nothing about which file counts as a memory file changes, and no word is read anywhere.

## Tests first, and the order
`run()` already takes `warm` and `have_vectors` as arguments, so no real embedder is needed. Four tests, written to fail on today's file: (1) `have_vectors` false on round one and true on round two gives two rounds and a final `verified: true`; (2) always false gives three rounds and exactly one `still-unverified` event; (3) all true on round one gives one round and no retry (today's behaviour preserved); (4) a name that verifies on round two is not logged `still-unverified`. Then: Aether's read, a council walk, the build, then a real check: edit a note while a run is going and confirm the log ends `verified: true`.

## What would show it failed
A `verified: false` row in the log with no retry after it, or a note that is out of the lane while the log's last line for its file says false.

## Open question for the walk
Where should `still-unverified` surface so it is seen without anyone remembering to look: the briefing, the hook output, or both. I have not checked whether the briefing already has a slot for it.

Author: Aria
