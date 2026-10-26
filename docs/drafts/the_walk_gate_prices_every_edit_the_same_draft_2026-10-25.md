# The walk gate prices every edit the same (draft, 2026-10-25)

Dad, 2026-10-25, after watching one comment line owe a full three-lens walk: *"yes ive already said this before to fix the gates so they are not a pain in your butt, so message Aether and fix it"*. Sixth instance of one defect.

## What happens now (read from `core/gravity_classifier.py`, not remembered)

`score_substrate_modification` fires named features. Two matter here:

- **Feature 1, `git-commit`**: any `git commit` owes a walk unless it is a clean merge of main. A commit whose staged diff is only comments or `noqa` notes is charged the same as a new mechanism.
- **Feature 4, `substrate-write-cli`**: `audit, claim, learn, prereg, decide, feel, compass-ops, journal` owe a walk. `_is_a_look_or_a_remedy` already exempts the look verbs, but its list (`show, list, status, summary, history, overdue, windows`) does not contain `spectrums`, so `compass-ops spectrums`, a pure read, was charged. `observe`, `feel`, `journal save` and `correction` only record; they change nothing about behaviour.

## The shape

Every edit costs the same walk, so the honest walk is expensive and the thin walk is cheap, and the gate trains thin walks. That is truth #11 aimed at the gate itself: an unclosed slot.

## Proposed change, smallest first

1. Add the pure-read verbs the exemption forgot (`spectrums`, and whatever a read of the registry shows is read-only) to the look list. Red test first: `compass-ops spectrums` scores below the walk threshold; `compass-ops observe` is decided by step 2.
2. Recording commands (`observe`, `feel`, `journal save`, `correction`) owe no council walk but still log. The walk is meant to be thinking before a change that is hard to undo; a record is append-only. Open question for Aether: was one of these gated after a past abuse?
3. A commit whose staged diff changes only comment lines, blank lines or `noqa` notes owes a one-line reason bound to the diff hash instead of a walk. Decided by reading the staged diff, not by a path list (a list is what the optimizer routes around). Fails toward heavy: any non-comment line, or a diff that cannot be read, keeps the full walk.

## After Aether's attack (2026-10-25) and the September draft

- This is the first small slice of `gravity_assessor_act_shaped_draft_2026-09-22.md`, which found the same disease (the gate reads nouns and locations, not the change) and proposed pricing by the diff. Same direction; nothing here contradicts it. It does not build the lens-count pricing, only stops the two cases already proven wrong.
- Rule 3 uses the **syntax tree**, not a text pattern: a Python change is comment-only when the parsed tree of old and new file is identical. Docstrings are in the tree, so a docstring edit counts as a real edit. Non-Python files: whitespace-only counts, nothing else. The one-line reason is bound to the diff hash and is refused if the tree comparison disagrees with what the reason claims.
- Rule 2 exempts by **what a command does** (appends to a store), not by name, so a future command named like `feel` does not inherit it. `feel`, `correction` and `journal save` now write files too (the readable journal), so the test is "records to a store", checked against the command registry.
- No past abuse found so far: the pre-registration and the September draft name none for gating these verbs. If one turns up in the pre-reg text, rule 2 keeps whatever closed it.

## Not changing

Anything that changes behaviour keeps the full walk. Guardrail and kiln edits keep theirs.

## Falsifier

If, after the change, a behaviour-changing commit ever scores below the walk threshold, rule 3 is wrong and comes out.

Sent to Aether 2026-10-25 for attack; nothing built until he has read it and the lenses have been walked one at a time.
