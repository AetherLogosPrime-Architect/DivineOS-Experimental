# A note's importance is read wherever the writer puts it (draft, 2026-11-22)

**Source:** found tonight while tending the memory link with Aria (Dad's ask: spend the evening linking and pruning; he wants a breakdown on return). Not asked for by Dad; it is a defect in my own lever from 2026-11-19.

## Prior art
- `_declared_importance` in `src/divineos/core/memory_linkage_retriever.py` (around line 1395), built 2026-11-19 after Aria's finding that every note carried the same 0.6 (walk walk-7d25e6148830). It reads only a TOP-LEVEL `importance: <number>` line between the opening and closing `---`; a line in the body never counts (text anyone can paste must not raise its own rank); a missing, non-number or NaN value keeps the default; out of range is clamped to 0..1.
- Commit `c961ea0be` ("a memory-folder note may declare its importance in its frontmatter").

## Where this sits (Aria's cold read, 2026-11-22; she checked, I confirmed)
- **Not on main.** `_declared_importance` and commit `c961ea0be` are on no remote branch (symbol search over every remote ref, mine and Aria's inventory). This change fixes a function that is itself waiting to land, so it sits **behind** the landing of the memory-folder lane and the warm module that hold it. The prior-art list above is the live house, not main.
- **The exposure is every new note, not only mine.** Aria's four declared notes are top-level and older than the writer's habit of nesting; "nothing to correct on her seat" was true by luck. Any new note either of us writes with a declared value is nested by the writer.
- **The review item the 11-19 walk asked for.** Notes at 0.8 or above: Aria has three (0.95, 0.95, 0.8) and one at 0.75, all top-level. Mine, counting the nested reader: the 11-19 in-flight note (0.9) and the 11-21 one (0.8) become live, plus the hub and the cheeseburger note (0.9 each, top-level). The list is to be printed and read by a person, not assumed.

## The defect
The memory writer, when it creates a file, rewrites the frontmatter: it adds `node_type`, `originSessionId` and `modified`, and it MOVES a top-level `importance:` line under `metadata:` as an indented line. The reader's regex is anchored at the start of a line, so the nested form is never read and the note silently keeps the default.

**Evidence, tonight.**
- A new note I wrote with `importance: 0.9` at the top came back with the line nested under `metadata:`; the probe showed `imp 0.60` and the note was cut on one of three situations. After I moved the line back to the top by hand: `imp 0.90`, shown on all three.
- Six notes in my memory folder carry the nested form today, with values 0.6, 0.7, 0.9, 0.8, 0.7, 0.6, including both READ-FIRST in-flight notes (0.9 and 0.8). Their declared weight has been the default 0.6. Two other notes carry the top-level form and work.
- An edit to an existing file (the cheeseburger note) kept my top-level line, so the nesting happens when the writer creates the file, not on every edit.

## The change
Let the reader accept the value in either place: a top-level `importance:` line, else an indented `importance:` line inside the frontmatter's `metadata:` block. Top-level wins if both exist. Everything else stays: body lines never count, bad or NaN values keep the default, clamp to 0..1.
Why the reader and not the writer: the reader is the one place that decides, so fixing it makes the lever work however a note was written, now and for every future writer. Fixing only the writer would leave today's six notes wrong.

## Risks (what could go wrong)
- **Weights jump.** Six notes would rise or fall from 0.6 on the next run. The 11-19 walk said the count of notes above 0.8 should stay small and be reviewed: after this change the nested ones add one at 0.9 (the 11-19 in-flight note). That is a review item, not a block.
- **A line pasted inside the frontmatter's metadata** could raise a note's own rank. Same exposure as the top-level form, which is already accepted for frontmatter and refused for the body; the nested form is read only between the `---` lines.
- **Indentation variants** (tabs, deeper nesting) must not be read as importance; only the one level under `metadata:` counts.

## Tests, written first
1. top-level reads (exists); 2. nested under `metadata:` reads; 3. both present, top-level wins; 4. nested line in the BODY is ignored; 5. nested but not a number, and NaN, keep the default; 6. out of range clamps; 7. a deeper-nested or tab-indented line is ignored; 8. a note with neither keeps 0.6.

## Falsifier
After the change, the six nested notes show their declared weights on `linkage why`, and no note without a declared importance changes. If any undeclared note's weight moves, the change is wrong.

## Not in this draft
No code. Aria's read, a pre-registration with the falsifier above, then tests first. Separately Aria is drafting the retry fix for failed warm runs.

## Replication (Feynman and Sagan asked for it before claiming the writer always nests)
A second fresh file (`project_linking_night_2026-11-22_where_my_log_and_findings_live.md`) written the same way came back the same: `importance: 0.7` moved under `metadata:`, writer fields added (`node_type`, `originSessionId`, `modified`). An edit to that file left the nested line where it was and only updated `modified`. So: **creation nests it; an edit preserves whatever is there.** Two fresh files, same result.

## Council design walk (walk-69417b4627a5, 8 lenses, framed as "what is the best way and what could it break")
- **Bengio:** the volitional fix (remember to write it at the top) is what failed; make the reader accept both so the right behaviour is the easy one.
- **Hoare:** the states are not declared, top-level, nested, both, declared-but-unreadable, out of range, and body. Declared-but-unreadable collapses into not-declared today (a typo hides); keep a count of unreadable declarations so it can be surfaced.
- **Feynman and Sagan:** show the mechanism, replicate once (done above).
- **Knuth:** only the one level under `metadata:` counts; stop at the next top-level key; a trailing comment after the value; empty frontmatter; and the reader's frontmatter pattern matches `\n` only, so a file with Windows line endings would silently fall back to the default. Test both sides of that boundary.
- **Yudkowsky:** once importance is a lever, any writer can raise its own rank; reading the nested form widens who can declare. The rule that the count above 0.8 stays small needs a real surface (a listed count Dad and Aria read), because notes must not grade themselves.
- **Lovelace:** parse the frontmatter once as structured data and look up the value at either level through one function, instead of a second pattern beside the first. The same parse can later carry a situation line as Aria's second vector.
- **Shannon:** one value, one precedence (top-level wins), and record which place it was read from for audit.

Added to the tests: Windows line endings, trailing comment, empty frontmatter, an indented line under another key, and a count of unreadable declarations. Added to the falsifier: after the change, the count of notes at 0.8 or above is listed and read by a person.
