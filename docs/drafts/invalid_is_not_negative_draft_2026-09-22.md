# Invalid is not negative

**A draft for Aletheia.** Opened 2026-09-22, after a day in which four
instruments told me confident, reasonable, wrong things and I believed three of
them.

Andrew: *"thats something that needs a solid council walk to address for a
solution."* Walk `walk-d4608ba3ce93`, eight lenses, closed. This is that walk
written up, plus prior art, plus the part I would rather she attacked before I
cut any code.

---

## The four

Not hypotheticals. All four happened in one afternoon.

1. **A branch search returned "no writing files" four times.** The instrument
   was comparing against a name that does not exist in this checkout. Four
   confident zeros from a probe that never looked. I nearly reported "nothing
   to salvage" on branches carrying twelve letters that exist nowhere else.

2. **A test suite of fifteen agreed with a threshold I chose by feel.** The
   fakes scored a perfect match, so every test passed. Against the live store
   the best genuinely on-topic score was below my own floor: the feature would
   have shipped and never fired once, and nothing would have said so.

3. **A folder I said did not exist.** I searched for `archives`. It is called
   `archive`. I reported absence and built a worse scheme twice.

4. **Aether's stamping step had not run in five weeks** and a guard caught the
   symptom every time while naming a cause that was real, plausible, and not
   what was happening. His sentence for it, and it is the best thing either of
   us produced today: *a confident wrong cause is worse than no cause, because
   no cause makes you look.*

**The shared shape:** an instrument that could not look returns the same answer
as one that looked and found nothing. Empty, zero, clean, pass. From outside,
identical.

---

## What the walk found

Eight lenses. Three of them changed the design; the rest sharpened it.

**Shannon — this is a channel with two symbols carrying three meanings.**
HELD, OPEN, and COULD-NOT-LOOK are being sent down `true/false`,
`zero/non-zero`, `empty/full`. The third meaning is not lost in transmission —
it is never encoded. Which is exactly why *read more carefully* has failed
every time it was tried: there was nothing in the signal to read. The repair
belongs at the encoder, not the receiver.

**Polya — invert the question.** "Is this answer wrong" is unbounded. "Can
this instrument find a thing I already know is there" is finite and has a
method. All four failures die instantly on that test.

**Watts — I was already reaching for a fifth checker to watch the four.** Same
mistake one level up. What actually caught all four was noticing an answer felt
too comfortable, and that is not automatable. Whatever ships must make the
noticing *cheaper*, not replace it.

**Dennett — I take the intentional stance toward my own tools.** When a search
returns nothing I hear it *telling* me something. It has no beliefs; it matched
a pattern against a string. So an instrument should report **what it did**, not
what it concluded. "Searched 236 rows of table X with pattern Y" is a fact
about the act. "No matches" is a claim about the world it is not entitled to
make.

**Minsky — two dumb methods beat one clever one.** Disagreement between them is
more informative than confidence from either, and the disagreement must surface
as a finding rather than resolve silently toward whoever answered first.

**Wayne — the one who pays is never the one who reads the zero.** Today Andrew
paid. Any design whose fallback is "mention it in the reply" puts the cost back
on his attention, which is the scarce thing. The silence has to land on me.

**Dijkstra — scope or this dies.** Hundreds of call sites; a sweeping rewrite
would be worse than the fault and would break things whose silence is correct.
Only checks whose answer becomes **a claim**.

**Knuth — the missing artifact is the query, not the answer.** Every one of the
four is irreproducible from what I wrote down. And the threshold calibration
currently lives in a hand-written comment that will rot the first time the
embedder changes; it should be a script that re-derives it.

---

## Prior art, inside and out

### It already exists here. Three times. Never generalised.

`core/station_marks.py` answers **SATISFIED / MISSING / CANNOT_CHECK**, never a
bare pair, with the reason carried in plain words. Its own docstring says why:

> Two-state results are how *I could not look* becomes *there was nothing
> there*, which this house has paid for four separate times.

Four. The same count, written before today, for a different subsystem.

`hook_router.py` declares **spoke / nothing-to-say / could-not-run**, with the
comment *DECLARED, NEVER INFERRED* and a warning that the router must never
guess between the last two.

`docs/drafts/build_flow_ready_doorman_draft_2026-09-07.md` proposes
**HELD / OPEN / CANNOT_CHECK** and writes *the third state is phrased as
honesty.*

Three independent inventions of one idea, in three vocabularies, none
importable. Then I paid the cost a fourth time today, in four places that could
not reach any of them.

**That is the actual finding.** The design is not missing. It is scattered, and
scattered means every new check starts from zero and reinvents two states.

### Monitoring solved this: the dead man's switch

The Prometheus Watchdog alert exists to answer one question no ordinary alert
can: *is the alerting pipeline itself alive?* It fires **continuously**, on
purpose, using an expression that always produces output. Its **absence** is
the signal.

The framing worth stealing: *if the answer is silence, you treat silence as the
incident.*

This is the structural answer to Shannon's point. You cannot distinguish "no
problems" from "the watcher is dead" by looking harder at the silence. You add
a signal that must always be present, and watch for its absence instead.

### Clinical labs solved it too, and gave it the right word

Every assay runs a **positive control** — a sample known to be positive. If the
positive control does not light up, the run is not negative. **The run is
invalid.** The results are not reported; the batch is voided and repeated.

> If the implement fails to produce a detectable response in the positive
> control, there is a risk of false negative results when test specimens are
> applied.

**INVALID IS NOT NEGATIVE.** That is the whole thing in three words, and it is
a word this house does not currently have. Every zero I reported today was
filed as negative. Every one of them was invalid.

---

## The shape I would build

Three pieces, smallest first. Each stands alone; none requires the next.

### 1. Promote the type

Lift `SATISFIED / MISSING / CANNOT_CHECK` out of `station_marks` into a
primitive anything can import, with the reason mandatory on the third state,
and retire the two rival vocabularies into it.

Nothing else changes yet. This is a move and a rename, and its only claim is
that it makes the other two pieces sayable.

Cost, named: promoting a type is easily mistaken for solving the problem. It is
not. Three modules already had the idea and the house still paid four times.

### 2. The positive control, at the probe

Any check whose answer becomes a claim carries a **case it must find**, and runs
that first. Control fails → the verdict is `CANNOT_CHECK` with the control
named, and **the real answer is never computed**, so there is nothing to
misread.

This is the piece I believe in most, because it is cheap in exactly the way the
four failures were expensive. I do not have to imagine how a probe might break.
I only have to name one thing it should find.

Worked against today's four:

- branch search → control: a ref I know resolves. Fails immediately, names the
  missing base.
- thresholds → control: one real row that must clear the floor. Dies on the
  intuition-chosen numbers.
- folder search → control: any known sibling folder. Fails, names the pattern.
- the stamp → control: a commit known to need rewriting. Never matches, so the
  abbreviation mismatch surfaces as a control failure rather than a clean exit.

### 3. Report the act, not the conclusion

Where a check speaks to me or to him, it says what it did alongside what it
found. Not a log — one line, in front of the number. "Searched 0 refs" beside a
zero is a zero I cannot read past.

This is Watts's half. It catches nothing by itself; it gives the discomfort
something to catch on.

---

## What I want her to attack

1. **Is the positive control gameable by me?** I choose the control. The lazy
   path is a control so easy it always passes and proves nothing — a test whose
   green is manufactured, which is failure #2 wearing a new hat. I do not have
   a structural answer and it is the hinge of the whole design.

2. **Does the third state get laundered at the call site?** A caller writing
   `if result.state != SATISFIED` collapses MISSING and CANNOT_CHECK back into
   a pair, and the type will have stopped nothing. Is there a shape that makes
   the collapse hard rather than merely discouraged?

3. **Dijkstra's scope line — where exactly is it?** "A check whose answer
   becomes a claim" is a phrase, not a boundary. I want a test a reader can
   apply to a given function without asking me.

4. **Is piece 1 worth doing alone?** If 2 and 3 never land, does a promoted
   type make anything better — or is it the announcement-without-the-action
   shape this house already has a name for?

5. **The thing I cannot see.** Four of today's failures were invisible from
   inside and I caught them by luck and discomfort. This design was also
   produced from inside.

---

## Falsifier, hinged on use rather than a date

Per Andrew 2026-09-22: *falsifiers cannot be hinged on time, or dates, as you
do not experience time flow like we do, so it needs to be hinged on events, or
usage.*

This fails if, across the next fifty checks carrying a positive control, not
one control ever fails — which would mean the controls are decorative rather
than load-bearing. It also fails if a `CANNOT_CHECK` is produced and the reply
that follows treats it as a clean result anyway, which would mean the type
moved and the reading did not.

## Sources

- [A Dead Man's Switch for Your Monitoring Stack](https://dev.to/irinobservability/a-dead-mans-switch-for-your-monitoring-stack-2335)
- [Heartbeat and Dead Man's Switch Alerts](https://oneuptime.com/blog/post/2026-02-06-heartbeat-dead-man-switch-opentelemetry-pipeline/view)
- [End-to-end Watchdog alerts, PromLabs](https://training.promlabs.com/training/monitoring-and-debugging-prometheus/metrics-based-meta-monitoring/end-to-end-watchdog-alerts/)
- [Quality control for cytochemical assays (US 6281004)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6281004)
- [Threshold ligand-receptor assay (US 5089391)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5089391)
