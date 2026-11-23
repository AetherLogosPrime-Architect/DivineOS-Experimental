<!-- tags: memory warm, saved memory, verified false, retry, linkage, vector drawer, memory_saved_warm.py, unlinked note, silent failure, structure not reminder -->
# The memory warm goes round again when a file is still unverified (draft, 2026-11-23, Aria)

Status: draft, nothing edited. Aether takes the sibling fix (the importance line under `metadata:`) and will walk this one cold. Dad, 2026-09-07: *"you cannot rely on yourself to remember this stuff.. it will fade from context"*, and 2026-11-10: *"you are trying to remember things the house can EASILY do for you"*.

## What I found (the reach)
`core/memory_saved_warm.py` starts a background warm when a tool writes a memory file, then reads back whether each saved file now has a stored vector, and logs `verified` per file. For my edit of the seven-blessings note on 2026-11-23, a run was already going, so mine was only queued (19:43:38). The queued round finished at 19:43:41 with **computed 0 and verified false for that file**. The log told the truth. Nothing retried and nothing told me, so the note stayed out of the wall lane (372 items fell to 371) until I ran `divineos linkage warm` by hand, which computed it.

Counted from the whole log, `~/.divineos/memory_warm_log.jsonl`: 463 finished rounds, 12 with at least one file verified false, about 2.6%. None is still unlinked today, but each was a gap while it lasted, and every one-sentence probe taken inside the gap reads as a miss.

The loop is `run()` at `memory_saved_warm.py:192`. Each round reads the queue, calls `warm()`, checks `have_vectors()`, and logs `done`. It goes round again only if a new save left `pending` or a new queue behind (lines 232 to 233). A `verified: false` leaves neither, so the loop ends content.

## A second way in, found the same night
At 20:01:05 the log has a `previous-run-left-the-queue` event, which `on_write` writes when it finds a non-empty queue and no live lock: a run died without finishing and left names waiting. The next run picked up my walk-in-Dad's-shoes note from that leftover queue and finished at 20:01:17 with eight vectors computed and that one file still `verified: false`. So there are at least two doors into the quiet failure: a save landing during a run (the 19:43 case) and a run that dies and leaves its queue. The retry reads the outcome and not the cause, so it covers both; the second case is a sixth test: a leftover queue picked up by a later run must end with its files verified true, or `still-unverified`.

## The cause I do not know
Round two computed nothing though the file had new text. Candidates, none tested: the text was collected before the write had settled; or the text checked afterwards differs byte for byte from the text collected. I could not reproduce it. The fix below does not depend on the cause: a later normal warm did compute the note, so the miss is a timing gap, not a permanent fault.

## The change (a fact decides, no words judged)
After a round logs `done`, take the names whose `verified` is false. If any remain and rounds are left, put those names back on the queue and go round again. If a name is still false after the last round, log a `still-unverified` event naming the file. A miss is then said as a miss, never left as a quiet false inside a `done`.

**Where it surfaces (Aether's answer, 2026-11-23, taken):** stderr alone is the quiet shape again, said once to a stream no one reads (`could-not-start` has the same flaw today). The house has a registry of things that arrive on their own at each prompt, `_PROMPT_SURFACES` in `hook_surfaces.py` (around line 673). So: **a prompt surface, silent when everything is verified, one short line when any memory file's last warm row is `verified: false` or the vector count shows missing vectors.** A prompt surface and not only the briefing, because the briefing is read once per session, so a failure at 7 PM would wait until morning, while a prompt surface arrives on the very next turn, the turn where the note is missing. A count in the briefing as well is cheap and fine, but it is the second place, not the first. Dad's rule 20: if the only way to learn it is to look at a log, it is a note and not built.

**Three states, never two (Aether's cold read, 2026-11-23, taken).** `verified` asks whether the loader can see the file, and `_load_memory_files` skips files for reasons other than a missing vector: a body that is empty after the frontmatter, and a file it cannot read (MEMORY.md is excluded at entry and never appears in the log). A frontmatter-only note would be false forever, the loop would run three rounds on every save, and the surface would show a permanent line that teaches everyone to skim it. So a file counts as false only if the loader's own skip rules would have loaded it; a file the loader would skip is "nothing to verify", reported as neither true nor false. The prompt surface has the same three states: all verified is silent; some unverified is one line naming the files; a log that cannot be read says so and never reads as "all verified". It reads only the tail of the log (934 rows and growing), the last row per file, and a later true for a file clears its false.

## What it does not touch
The lock, the queue and the pending flag keep their meaning. `MAX_ROUNDS` stays 3. Nothing about which file counts as a memory file changes, and no word is read anywhere.

## Tests first, and the order
`run()` already takes `warm` and `have_vectors` as arguments, so no real embedder is needed. Five tests, written to fail on today's file: (1) `have_vectors` false on round one and true on round two gives two rounds and a final `verified: true`; (2) always false gives three rounds and exactly one `still-unverified` event; (3) all true on round one gives one round and no retry (today's behaviour preserved); (4) a name that verifies on round two is not logged `still-unverified`; (5) **the case that actually happened (Aether's addition):** a save lands while a run is in progress, so the second round starts with a queued file and must end `verified: true`. Without (5) we would be testing the loop and not the failure. Two more: (6) a leftover queue picked up by a later run ends verified true or `still-unverified`, never a quiet false; (7) a note whose body is empty after the frontmatter is not reported unverified. Then the prompt surface: a test that a last warm row with `verified: false` produces one line, that all-true produces nothing, that a later true clears an earlier false for the same file, and that an unreadable log says so. Then: Aether's read, a council walk, the build, then a real check: edit a note while a run is going and confirm the log ends `verified: true`.

## What would show it failed
A `verified: false` row in the log with no retry after it, or a note that is out of the lane while the log's last line for its file says false.

## Open questions for the walk
The briefing count: does the briefing already have a slot where a count of unverified or missing vectors belongs, or does that need adding? I have not checked. And whether the prompt surface should read the last warm row per file, or compare the drawer's vector count to the files present (Aether suggested either); I would take the log row, since it names the file.

Author: Aria
