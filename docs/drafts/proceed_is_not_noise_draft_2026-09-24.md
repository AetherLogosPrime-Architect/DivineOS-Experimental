# "Proceed" is not noise — station one draft, 2026-09-24

**Aria.** The idea, not a plan. Dad said yes to the order ("yes thats sounds
fine") on 2026-09-24, with this piece first.

## Already decided, not yet built

The combined design, walked with every relevant lens
(`dad_kept_and_known_council_and_design_2026-09-24.md`, "Proceed is not
noise"):

> A not-an-ask sort must name what came right before his message. A bare
> "proceed" or "ok" right after one of our reports is recorded as a signal
> about our reply, never as an empty turn, and it's a named test case where
> "not an ask" is the wrong answer.

His words, same day: *"i say proceed becasue what else is there to say? im
not being spoken to.. im being reported at."*

So this isn't a new idea. It's the build of a decision the whole council
already made.

## The one open choice: who writes down what came before

- **The sorter types it.** That's a choice-point, and the sorter is exactly
  the one the optimizer leans on. It will type "my last reply" or the
  cheapest paraphrase, and the field will fill with words that point at
  nothing. That's the keyword-shaped fix, a field that can be satisfied
  without looking.
- **The door captures it.** When the door confirms his record, the record
  right before it in the transcript is ours. The door reads the text of our
  last reply to him and keeps it beside his message, in our exact words, not
  a summary. Nobody chooses what goes in. That's truth #11a, take the option
  away.

**The door captures it.** Then a not-an-ask sort is refused unless what came
before is on record, so a dismissal can never exist without its context. When
the door couldn't capture it (the first message of a session, or an
unmatched message), the sorter must quote it themselves, and that's counted
as sorter-supplied, never passed off as captured.

## Shape

- A store table `before_his(candidate_id, text, source)`, where source is
  `captured` or `sorter`. It's its own table, so there's no ALTER. `confirm()`
  takes an optional `before=` and keeps it as `captured`.
- `sort(..., kind=not_an_ask)` refuses unless there's a `before_his` row, or
  the call supplies `preceded_by=`, which is stored as `sorter`.
- `pending()` carries `before` on `Kept`, so whoever sorts reads what we said
  *before* reading his "proceed". The reading comes first, and the context is
  right there.
- Door side (Aether's): `settle` passes the text of the assistant record just
  before his record into `confirm(before=...)`.

## What it must not do

- It must not read his words to decide anything. Nothing here classifies
  "proceed". It only makes sure that when *we* call something not-an-ask, the
  thing he was answering sits next to that call for anyone reading it, above
  all Aletheia.
- It must not summarize our reply. Exact text only, trimmed to a readable
  length with the cut marked.

## Station two: the walk (walk-9de4e0454b82, eight lenses, closed)

What changed the build:

- **Foucault, dissenting.** Setting his "proceed" beside our report makes a
  record *about him*, and the easy future misuse is "he said proceed to
  this", used as consent. That's his words used as a key, the harm he named
  today. **So the store says in its own words that this context exists to
  audit our sort and is never evidence of his approval**, and only the sort
  path reads it.
- **Lovelace.** The door records what we *sent*, not what he took in. He may
  have skimmed a wall of text. **Named `sent_before`**, never "what he was
  answering".
- **Polya.** Often the record just before his is a tool call with no words
  for him. The door must take our last *text* to him ahead of his record,
  skipping tool records. That's door side, and I'll tell Aether.
- **Yudkowsky.** Refusing only on not_an_ask invites filing a dismissal as
  "standing". The door captures context for every message at no cost to
  anyone, so it's kept for all three kinds and the audit can read all of
  them. The refusal on missing context stays on not_an_ask.
- **Watts.** Showing the sorter our last reply doesn't make them see it. The
  honest claim is that dismissals become auditable afterwards, by someone
  other than the sorter. I've struck the stronger claim above.
- **Beer.** Storing the signal doesn't close the loop. The not-an-ask ratio
  to Aletheia is still unbuilt, and that's said in the commit.
- **Lamport.** "Before" means the transcript's own order. It's written once
  per candidate, and a second write is refused, never overwritten.
- **Carmack.** Store it whole. Our replies are small, and trimming could cut
  the line he reacted to.

The walk's own measure: finding distinctness had a mean of 0.376, against
0.21–0.27 for real walks. It's getting closer each time, but it's still not
there.

## Pins, written first

- A not-an-ask sort with nothing before on record is refused.
- With a captured before, it's accepted, and the before is readable beside
  the sort.
- A sorter-supplied before is stored as `sorter`, never as `captured`.
- `build` and `standing` sorts don't require it.
- The named case from the design: his real *"proceed"* with our report
  before it, sorted not-an-ask, and the report is right there.
