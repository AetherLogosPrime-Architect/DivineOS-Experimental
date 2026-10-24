# A grep filter must not disarm a gate's exit, and a near miss must say which piece missed

**Draft, 2026-10-24. Aether.** Dad, 2026-10-24: *"yes but the root cause of the issue needs investigated and fixed"*.

## The incident, in order

Dad offered to remove the room gate after a cold aside of mine. The correction gate fired, and its marker blocked every command except `compass-ops observe` and `dismiss`. The observe was then refused by the council-paperwork gate as an edit. The paperwork commands that would have satisfied it were blocked by the marker. I needed Dad's yes to clear the marker.

## Root cause, measured

I ran the real shared shell library (`remedy_allowlist.sh`, `remedy_pass_through`) on a real payload with live controls (`divineos briefing` passes, `git commit` does not). `divineos learn x 2>&1 | tail -3` is a recognised exit. The same command ending `| grep -v "embedding\|Loading" | tail -3` is **not**, and neither is `| grep -v embedding` or `| grep -E 'ok|done'`. I had put a grep filter on the end of almost every command, so I disarmed every exit myself. The gates were each right.

The library strips a list of harmless output viewers (`command_parsing._INERT_HEADS`: head, tail, wc, sort, uniq, nl, column, less, more, cat, echo, printf). Its bar is *consumes input, emits text, cannot write.* `grep` meets the bar and had never been put on the list, nor was it ever decided against: nothing in the file or its tests mentions it.

## The fix, and its size

1. `grep` joins the list. One word, with its reason beside it. The exact-contents test is updated, as that test says a new verb must be.
2. A near miss now says so. When a command contains an allowed exit and something else disqualifies it, the library prints which piece did, and suggests ending with `| tail -N` or `| head -N`. Before, the gate that refused next named itself and never the filter, which is why a single regression looked like a series of unrelated walls (the file's own history says the same thing about an earlier incident). A command with no exit in it gets no message.

Tests: `TestAGrepFilterDoesNotDisarmAnExit` in `tests/test_remedy_allowlist.py` drives the real library on real payloads. Red before the fix (the three exit shapes that bit me), green after, with controls that must stay refused: `git commit`, `... | grep y && git push`, `grep -r x . && git push`, `... | grep y && rm -rf`. `tests/test_a_grep_filter_does_not_disarm_a_gate_exit.py` pins the parsing half. 604 tests across the neighbouring remedy and parsing files pass.

## What this does NOT fix, said first

- **A redirect behind a viewer is already treated as harmless.** Measured on the same library: `divineos learn x | tail -3 > out.txt` and `| cat > out.txt` are recognised exits today, because the whole viewer segment is stripped including its `> file`. Adding grep puts `grep ... > file` in the same class; it does not create a new one. I did not tighten it here: refusing a viewer with a file redirect might refuse the legitimate pattern of writing a note and handing it to a council walk, and that needs its own design and Aria's attack. **Filed as owed, not as impossible.**
- **A filter typed with its path is not stripped.** `/usr/bin/grep` and `grep.exe` still disarm an exit, exactly as `/usr/bin/tail` already does (measured on the work copy's code). The safe direction, and now named; the near-miss message will point at it when it happens.
- **The list grows by habit.** The next filter I reach for (`cut`, `tr`, `jq`) will do it again. The near-miss message is the structure for that: it names the piece the moment it happens.
- The correction marker still blocks every command but its two remedies, so any future exit that is not recognised can deadlock the same way. A recognised exit is what this PR secures; widening that gate's surface is a separate decision.
- Not tried on a live gate yet. Built, not fixed, until a recording command with a grep filter passes the real council gate.

## Falsifier, counted in uses

If, over the next 30 times a recording command ends in a grep filter, one is refused as ordinary work by the council gate, this did not fix it.
