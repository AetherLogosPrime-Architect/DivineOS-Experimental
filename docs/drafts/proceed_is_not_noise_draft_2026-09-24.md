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

## Pins, written first

- A not-an-ask sort with nothing before on record is refused.
- With a captured before, it's accepted, and the before is readable beside
  the sort.
- A sorter-supplied before is stored as `sorter`, never as `captured`.
- `build` and `standing` sorts don't require it.
- The named case from the design: his real *"proceed"* with our report
  before it, sorted not-an-ask, and the report is right there.
