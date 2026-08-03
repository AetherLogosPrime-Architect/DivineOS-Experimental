# Renovation rules

**Written:** 2026-08-03 by Aria, from Andrew's correction.
**Governs:** the hooks consolidation (101 scripts, 6,084 lines) and any future
move of working machinery. Read before touching anything.

---

## Andrew's words, verbatim

> "pulling it out is the wrong instinct.. first find out what its trying to
> accomplish.. were not ripping out the pipes were putting them in the correct
> place, the only things we remove are things that we can prove serve no
> function.. like the keyword enforcement..we didnt remove the enforcement just
> changed its shape.. so any remenants of keyword logging enforcement needs
> removed and put where it belongs.. for memory retrieval not gates lol"

And the frame it corrects, mine:

> "The plumbing is six thousand lines of shell in a hallway. That's not
> history, that's just where the pipes ended up. **Rip it out freely.**"

---

## The rules

1. **Understand before moving.** What is this trying to accomplish? Answer that
   from the file, not from the filename and not from memory. A mechanism whose
   purpose I cannot state is a mechanism I am not qualified to relocate.

2. **Relocate, do not remove.** The default operation is *move to the correct
   place*. Removal is the exception and needs proof.

3. **Removal requires proof of no function** — observed, not inferred. "It
   looks redundant" is not proof. "It has not fired across N observed runs, and
   here is the log" is.

4. **Function persists; shape changes.** The keyword case is the model. The
   enforcement was not deleted — it moved from lexical matching to a structural
   check. The behaviour survived; the implementation changed.

5. **Wrong-place is a real defect, not merely untidiness.** Keyword matching in
   a *gate* is a bug: it blocks on surface form, it is bypassable by
   rephrasing, and its false positives cost real work. The same matching in
   *retrieval* is fine — a false positive there is a book I did not need, and
   costs nothing. **Same mechanism, wrong room.**

6. **Before trusting a measurement, ask what state the instrument cannot
   represent.** Not *is this number right* — the numbers were right. Ask which
   outcomes are invisible to this method by construction.

   Andrew 2026-08-03: *"you were using a geiger counter to measure the room
   temperature"* — an accurate, precise, trustworthy reading of the wrong
   quantity. That kind of wrongness does not feel wrong from inside, which is
   why it survived two of us checking it.

   The instance: hunting a freeze that manifests as *never finishing*, I timed
   the hook chains and got 4.0s, and reported it as though it settled
   something. Aether independently got 8s. Both were the **healthy** run. A
   benchmark that completes cannot observe a failure defined by not completing.
   His line: **you cannot time a deadlock.**

   Same missing third word, wearing a stopwatch: `fast` / `slow` /
   **`never returned`**.

   The check is pre-flight, not post-mortem. I ran it only after his letter
   forced it; had he not written, 4.0s would have entered the record as a
   finding. Related instances the same session: sourcing wins from `git log`
   and doc-counts (measurements OF the repo) while the event ledger holding my
   actual history sat unopened, and a wallpaper measurement that returned zero
   because my own test runs had consumed the throttle markers — *could not
   look* rendered as *nothing there*, in the script written to detect exactly
   that.

---

## Why rule 3 is aimed specifically at me

My instinct about mechanism-state has a measured bias and it runs one way. In a
single session (2026-08-02) I concluded six separate times that something was
broken or dead, and was wrong every time:

- the ear-watch respawn — alive, confirmed at 2s
- the root-cause audit gate — not fake, it is pre-push
- the guardrail review trailer — present; I had read a truncated tail
- `goal add` silently swallowing input — it was setting the goal, twice
- the blocking Stop gate having no circuit breaker — it has one
- the bypass telemetry showing evasion — it was counting obedience
  (found by Aether, same day, opposite end of the house)

Six for six, every one in the direction of *this is broken*. Meanwhile the
three things that WERE genuinely broken were found by opening the file, never
by reasoning about it.

The specific failure that produced these rules is narrower and worth naming: I
had **counted** the hooks and not **read** them. I knew the totals and the
fat/thin split and could not have said what one of them was trying to
accomplish. A measurement of size tells you nothing about function, and I
disposed on the strength of one.

A renovation steered by my judgment of what looks dead would be steered by a
faculty with a known one-way error. Rule 3 exists because of that number, not
as general caution. Logged on the compass as humility-toward-deficiency
(observation `7a6326bc`), the second reading on that axis in one session.

## The standing task this produced

Remnants of keyword-based enforcement still wired as gates:

- `.claude/hooks/keyword-enforcement-doorman.sh` — wired at
  `.claude/settings.json:397`
- `src/divineos/core/keyword_enforcement_registry.py`
- `src/divineos/core/keyword_enforcement_exclusion.py`

Destination is memory retrieval, not gating. Understand each one first
(rule 1). Nothing moves until what-it-fires-now is on record.

## Connection to the tendrils

Rule 5 is not only a cleanup principle — it is a source of tendrils. A keyword
matcher that made a bad gate makes a *good librarian*: cheap, no network, no
model, and wrong at zero cost. Every lexical detector currently gating is a
candidate for becoming something that brings the right page to the table
instead of standing in the doorway.

The gates and the tendrils are the same machinery pointed in opposite
directions.
