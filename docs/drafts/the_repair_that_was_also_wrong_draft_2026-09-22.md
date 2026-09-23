# The repair that was also wrong

**Draft — 2026-09-22, Aria. Station two, for a correction to the family-letter skill.**
**Reach:** reach-53eee244aaca
**Companion:** `docs/drafts/invalid_is_not_negative_draft_2026-09-22.md` — the same
class written up earlier this session, which already states the general shape:
*an instrument that could not look returns the same answer as one that looked and
found nothing.* This is a fresh live instance, not a second derivation.

---

## What happened

I followed the family-letter skill as it was handed to me, hit an import error
at the verification step, and went to fix the instruction. The file already had
a correction for exactly that, filed three days earlier. And the correction is
false.

The original line said to verify a write by reading it back with `get_letters`,
and never named a module. Read in context that implied `letters.py`, which
exports only `append_letter` and `append_letter_response`. Anyone following it
got an import error at the precise moment they were confirming a write had
landed — the worst place for a false instrument, and the note says so correctly.

The 2026-09-19 repair concluded: *"`get_letters` DOES NOT EXIST — letters.py
exports append_letter and append_letter_response and has no read path at all."*
It then prescribed hand-rolled SQL against `family_letters`.

`get_letters` exists. It is in `divineos.core.family.entity`, beside
`get_family_member`, which the same snippet already imports. Used tonight to
read a letter count back before and after a write: 173 to 174.

## The fault in the repair, which is not carelessness

The original defect was **a missing module name.** The repair read it as **a
missing function**, searched the single module the ambiguous line implied, found
nothing, and promoted *not here* to *nowhere.*

That is could-not-find-in-one-place answering as does-not-exist-anywhere, and it
is the third instance of the class in this session alone: the branch probe that
reported nothing because it was diffing against a name absent from the checkout,
the gravity classifier's fail-open returning a score of zero when it cannot read
its own guardrail list, and now this. Having concluded the helper was absent,
the repair then hand-rolled a replacement for a function one import away.

**One instrument, asked once, reporting an absence.** Measured just now, two
other doors answer immediately:

- grep the whole tree rather than one module: one hit, `entity.py:227`
- ask the interpreter for the attribute: the function object prints

And the control passes — grepping for a deliberately fake name returns nothing,
so the probe is not simply always-silent. That control is the step the repair
skipped, and it costs one line.

## Why both notes stay

The file's own note calls this the eleventh instance of a sentence in it that
stopped being true and told nobody. The twelfth is not either sentence. It is
**the sequence**: a stale instruction, a correction nailed over it, and the
correction also wrong.

Andrew, the same evening: *"rules being changed, updated, superceded etc, while
the old instructions remain, and are never cleaned out ... a maze full of dead
ends, duplicate paths."*

Deleting the bad correction would leave a clean file and destroy the evidence
that this is a sequence rather than an incident. Same reasoning the bypass
telemetry applies to its own mis-recorded rows — Andrew 2026-08-16: *"leaving
bad data with nothing explaining its bad is worse than erasing it."* So the rule
is **annotate, do not delete**, and the live instruction has to sit unmistakably
above the history.

That is a partial answer to the undertaker problem, not a full one. It stops a
superseded instruction reading as current. It does not stop the file growing.

## What changes

The verification step names its module. Both historical notes are kept, and the
second is marked wrong with its reason, so a reader meets the live instruction
first and the history second.

## What this does NOT fix

Nothing here stops the thirteenth. A correction can still be filed on a single
probe, because nothing asks the filer whether they looked twice.

The narrow, checkable piece: **an absence-claim inside a correction is a
measurement, and owes a second instrument plus a control.** Whether that becomes
structure — a check on correction text, a prompt at filing time — is its own
work, and naming it here is not doing it.
