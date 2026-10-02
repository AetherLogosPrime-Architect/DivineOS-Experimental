# The council gate's key names every file a command writes (draft, Aria, 2026-09-23)

Item 1 of my arc-4 reading of #519, handed to me by Aether ("do the reader swap
in the hand that owns the reader... and take the multi-write half with it").

## What is wrong, measured on 01f9ea198 and unchanged at 765cac4d8

`fingerprint_for` names a shell write by its file, which is right, but finds the
file through `gravity_classifier._shell_write_targets`, which:

- does not know `cp`, `mv`, `install`, `git mv`, `sed -i` or `patch`. So
  `cp src.md notes/scratch.md` and `cp src.md docs/foundational_truths.md` both
  fall through to the act-anchor and key as `bash:cp src.md` -- the SAME key. A
  walk filed for the harmless copy clears the copy onto the kiln.
- has no command boundaries: `echo x > a.md; echo y > b.md` keys as
  `write:a.md;`, semicolon inside, second write gone.
- reads a quoted arrow as a redirect: `echo '>' notes.txt` keys as
  `write:notes.txt`.

And it keys on `written[0]` only, so a command writing three files is keyed by
whichever one the reader reached first; a walk for that one clears the other two.

## The idea

1. Move `shell_write_targets` (and its helpers) into `command_parsing`, byte for
   byte as it stands on my branch -- one home, not a fifth copy. Replayed there
   against 22,849 real commands.
2. `fingerprint_for` asks it.
3. Several files written: ONE key naming all of them, sorted and deduplicated,
   joined with ` + ` -- `write:a.md + write:b.md`. The gate keeps its single-key
   API, so decide(), the hook, the refusal and the game-walk need no change, and
   the refusal still names a key a person can copy and file against.
4. `_covers` learns one thing: a compound key is covered by a record whose own
   key plus its enumerated scope contains EVERY part. That is Aether's "key three
   times" -- a job-scoped walk that listed all three files clears the command,
   a walk for one of them does not.

## Directions, said out loud

- Permitting direction closed: a walk for one file can no longer clear a command
  that writes others.
- A filename containing ` + ` splits into parts that match nothing, so it
  REFUSES. Fails toward asking for a walk, never toward waiving one.
- Malformed quoting: the reader approximates with a whitespace split rather than
  crash (its existing convention). The key may be odd; the refusal names it, and
  filing against the named key works. Exposing could-not-read instead is the
  tokeniser-merge work, not this change.
- Unchanged and still open: `gravity_classifier` keeps its own reader for
  SCORING, so whether the gate fires at all is still decided by the weaker
  reader. Named, not fixed here -- that is the scorer's half of the merge.

## What the walk changed (walk-421eaefacb8f, eight lenses)

- **Pearl widened the scope, on a measurement.** `cp src.md
  docs/foundational_truths.md` scores gravity 0 at 765cac4d8 -- the gate never
  runs, so its key is never consulted. Fixing only `fingerprint_for` would pass
  every key test and change nothing for the headline case. So gravity's
  `_shell_write_targets` reads through the same shared reader too. Aether gave me
  item 1 as the key; this makes it the key AND the scorer, and I say so to him
  rather than letting it arrive as a surprise in the diff.
- **Feathers:** my reader has no `/dev` filter, so raw it would turn
  `git commit ... 2>/dev/null` into `write:/dev/null`. The filter from gravity's
  `_as_target` travels with it (`/dev/*`, `nul`, `-`). Single-write keys stay
  byte-identical so every walk already on the ledger still matches. The
  `TestWhatItCannotSee` cp/mv cases are meant to fail when closed -- they move to
  a "now seen" class; `python write_it.py` stays pinned as invisible.
- **Beer:** gravity keeps its own could-not-read check (unbalanced quotes ->
  None -> scrutiny) IN FRONT of the shared reader, which approximates rather
  than refuses. The direction of that caller does not change.
- **Wayne:** properties, not examples -- a subset walk never covers; key is
  order-independent; single-write key unchanged.
- **Turing:** the key is a lower bound on the write set. `python -c` writing the
  kiln still keys `bash:python -c` and scores 0; stated as open, not implied closed.
- **Minsky / Peirce:** compound key is one `--edit` value (`--scope` splits on
  commas, `+` is safe); a game-walk for a multi-write is filed against the
  compound key -- a second price for one act, left with the cost finding.
- **Distinctness 0.429** against a 0.44 reference for nine restatements, max
  pair Meadows/Pearl 0.675. My reading: Meadows restated Pearl's conclusion in
  leverage terms and added little; the other six each changed the plan. Not
  re-walked to move the number.

## Proof I owe

- Tests that fail on 765cac4d8 and pass after: the cp/mv collision, the
  semicolon key, the quoted arrow, the multi-write key, the compound-coverage
  rule (all parts -> covered; one part missing -> not covered).
- A live before/after through `divineos council check` if it runs in the
  worktree.
