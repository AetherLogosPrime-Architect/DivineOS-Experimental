# A message of his that never settles does not vanish — station one draft, 2026-09-24

**Aria.** The idea, not a plan. Found at station four on Aether's parked
sort-first lock (his letter "the sort-first lock is built, and it's parked";
mine, "station four: a message that never settles vanishes from everything").

## This was already decided, and never built

My own store threadwalk from this morning
(`dad_kept_and_known_store_threadwalk_2026-09-24.md` on the build branch, in
the filing section) says: *"a CANDIDATE never confirmed or withdrawn by the end
of the turn is itself a could-not-file, and it counts as one."* The game walk,
row 8, says could-not-file *"is loud and opens an obligation that refuses our
next action."* Nothing implements either. `unsettled()` is read only by settle,
and settle now skips anything past its horizon. The decision lived in a draft
and the code never met it.

(Searched first: those two drafts on the build branch hold the decision. This
seat's own drafts folder has nothing on it.)

## What happens today

The front door keeps his message as a CANDIDATE the moment he hits enter, with
his exact words. It becomes FILED when the door finds his record in the
transcript. Everything that makes us read him (`pending()`, the sort-first
lock, `divineos his pending`, `sort()`) looks only at FILED messages.

So a message that is kept but never matched to a record is refused by nothing,
shown by nothing, sortable by nothing, and counted nowhere. Aether's settle
horizon, which he added for a real reason (a never-matching candidate made
every tool call read further back), makes that permanent.

## The shape

- **A state of its own: UNMATCHED.** Kept, with his words, and the transcript
  record was never found. It isn't WITHDRAWN, because withdrawn means "not
  his", and it isn't FILED.
- **`give_up(candidate_id, reason)`** moves a CANDIDATE there, only a
  CANDIDATE, with a written reason. It also writes a `could_not_file` row, so
  it's counted where failures are counted, which is what the threadwalk said.
  Aether's settle calls it past the horizon.
- **`pending()` returns UNMATCHED messages too.** It carries his words and the
  id to sort them by, which is the candidate id, because there's no record
  uuid. `Kept.sort_id` names that id either way, and `Kept.record_found` says
  which kind it is.
- **`sort()` and `same_ask_as()` take that id.** His words are his whether or
  not we found the record.
- **The lock refuses over them**, because they're in `pending()`. That's the
  game walk's "refuses our next action". The wiring is Aether's, once his half
  is committed.

## What it must not do

- It must not resurrect a WITHDRAWN message. Those were judged not his.
- It must not make an UNMATCHED message look like a FILED one. The difference
  is a fact about our instruments, and readers need to see it.
- It must not delete or rewrite anything. States move forward, and each move
  has a reason.

## Named, not solved

If the record turns up after `give_up`, `confirm` returns UNMATCHED and
doesn't file it. Attaching a late-found record is its own small piece. The
message is never lost in the meantime.

## Station two: the walk (walk-2592439477f9, eight lenses, closed)

What changed the build:

- **Schneier, dissenting, and it changes the shape.** `keep()` files *every*
  non-empty prompt, and machine notices (task notifications, CI events) fire
  the same hook. Today settle withdraws them when their record shows a
  non-human stamp or only an envelope. If one is never matched, `give_up` as
  first drafted would have moved a machine notice into `pending()` as his
  words. That's the misquote harm, built by me. **So `give_up` checks
  `nothing_of_his(text)`, and envelope-only text goes to WITHDRAWN with that
  reason, never to UNMATCHED.** Better still, the door shouldn't keep
  envelope-only prompts at all. That's for Aether.
- **Hofstadter.** Every surface reads `pending()`, so a gap there is a gap
  everywhere. **Add a conservation pin by a different query path:** every
  message not WITHDRAWN (and not still a CANDIDATE) is either sorted or in
  `pending()`.
- **Dijkstra, dissenting on naming.** `sorts.uuid` and `links.uuid` now hold
  candidate ids for unmatched messages. That's declared at the schema and
  named `sort_id` in the signatures, not migrated.
- **Dennett.** Stored isn't heard. The store pins prove presence; the lock
  pin, which rides on Aether's half, proves influence. Not done at the store.
- **Kahneman against Schneier**, a real tension. The flag must not frame his
  words as doubtful, and it mustn't hide that the record wasn't found.
  Wording: *the door kept these words when he pressed enter; the record that
  confirms who typed them was never found.* His words come first.
- **Penrose.** One terminal state, not one per cause. The reason carries the
  cause.
- **Beer.** Any UNMATCHED is an alarm about the door. Its count belongs where
  instrument failures are seen. Owed as its own piece.
- **Aristotle.** Whether the record was found is an accident of
  instrumentation, not what kind of thing the message is: peer in `pending()`,
  with the accident flagged.

The walk's own measure: finding distinctness had a mean of 0.409, against
0.21–0.27 for real walks and 0.44 for restatements. Still closer to one voice
than a good walk. Schneier's finding changed the artifact, and that's what the
number can't see, but the number is recorded as it came.

## Pins, written first

In a temporary store: `give_up` moves a candidate, writes the could-not-file
row, and refuses a short reason or a non-candidate. `pending()` shows it with
his words and `record_found=False`. `sort(candidate_id, ...)` accepts it and it
leaves `pending()`. A WITHDRAWN message can't be given up into view.
