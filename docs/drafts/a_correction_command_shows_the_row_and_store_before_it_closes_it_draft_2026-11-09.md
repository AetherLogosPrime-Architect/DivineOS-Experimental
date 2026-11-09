# A correction command shows the row and the store before it closes the row (draft, 2026-11-09, Aria)

Status: DRAFT. Walk in the chat, Aether's read, tests first, then code.

## What happened

I read Dad's oldest open asks from the 857-row store in `~/.divineos` with a direct query, then ran `divineos andrew-correction integrate` and `misfiled` for ids 284, 287, 288 and 289. The command writes to MY store, `~/.divineos-aria` (424 rows), where those ids are different corrections. I closed four of his real words with evidence about other things (#288 *"i have never punished either of you for failure"*, #289 *"you are literally flooding me in information"*, #284 on *"AI psychosis.. slop"*, #287 my telling him what his body was doing). I caught it only because a later read of "the oldest open rows" still listed them as open. The store was restored from a snapshot taken first.

## Cause

Three stores with near-identical names (`~/.divineos` 857 rows, `~/.divineos-aether` 0 rows, `~/.divineos-aria` 424 rows). A row number means different things in each. The commands that close a row print only the number and the evidence I typed, never which store they changed or which words they closed, so nothing on the screen could have told me the row was not the one I had read. CLAUDE.md rule 9, third clause: prove the object you opened is the object you named.

## The change

1. `integrate`, `misfiled`, `defer`, and `propose-hold` / `confirm-hold` print, before changing anything, the store file path and the first 120 characters of the row's words.
2. Each takes an optional `--expect-text TEXT`. When given, the command refuses unless the row's words begin with it, and says what the row actually begins with. When not given, it still prints the row, so the object is seen every time.
3. The success line repeats the row's first 120 characters, so the record of what was closed is in the output.

## Changed by the walk (walk-0ac923c59307, written in the chat first; distinctness max 0.732 between Dennett and Polya, close to restating each other, reported and not read either way)

- **`--expect-text` is REQUIRED, not optional** (Bengio). An optional check is the volitional bridge my fast habit skips. Required, the lazy path and the careful path are the same path.
- **A floor of 12 characters, and a prefix match** (Yudkowsky). Both sides are cleaned the same way before comparing: whitespace collapsed, line endings and case ignored, and the garbled characters some real rows carry (a smiley stored as symbols) treated identically on both sides so they cannot fail a true match (Knuth).
- **A refusal shows the row's true start**, so the cheapest next move is to read it and paste it back.
- **A missing id is refused first**, before any text comparison.
- **The main test replays the real incident** (Polya): two temporary stores holding different rows under one id, and the exact closing command that was run, which must now refuse and show the true start.
- **One new unit** (`describe_row` plus `check_expected_text`), tested alone, called from each command in one line (Feathers), after a characterization test pins what the commands print today.

## Added by Aether's cold read (2026-11-09)

He found the commands by searching the source for the UPDATE statements, not from memory, and named two I had not:

- **`auto_integrate_from_commit`** closes every OPEN row named in a commit message ("correction #N"), against whichever store that seat's hook reads. It has the same blind spot and cannot take row words, since a commit message carries none. Remedy built here: the command prints the store and the first 60 characters of each row it closed, so the record shows which words were closed. Naming a different remedy for it (printing before closing) stays open.
- **The reopen path for deferred rows** sets a row back to OPEN when its unblock condition fires. That direction is benign, and it runs without anyone looking at the row. Named, not changed.
- The three store names stand alone as a separate change; this one already puts the path in every success line.

## Built (branch aria/closing-a-row-shows-the-row, stacked on aria/integrate-reads-dot-directories-and-says-why)

`describe_row`, `check_expected_text` and a letters-and-digits comparison in the tracker; `--expect-text` required on integrate, misfiled, defer, propose-hold, confirm-hold and unhold, each calling one shared `_show_and_check_row` first; the commit route prints store and words; the teaching text in the briefing block and the attestation hook now shows `--expect-text`. One thing the tests found on the way: a different helper called `_squash` already existed further down the same file and silently replaced mine, so mine is named `_letters_and_digits`.

## Tests, first

- A row whose words do not begin with `--expect-text` is refused, and the refusal shows both texts.
- The command's output names the store path and the row text on success and on refusal.
- A made-up id in a store holding different rows is refused, not silently closed.
- Every command in the list above prints the row before its first write (a rule over the list, not three copies of one test).

## Falsifier

If any of these commands closes a row without having printed its words and its store, or accepts an `--expect-text` that the row does not begin with, the fix is wrong. It will not stop me from reading one store and writing another by itself; it makes the mismatch visible at the one moment it matters, and `--expect-text` makes it refuse.

## Open

Whether the three store names themselves should be reduced to one per seat with a different, unmistakable name is a bigger question and not part of this change.
