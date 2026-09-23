# The doorman names items stranded on other branches — draft 2026-09-23

Reach: reach-6701e7cff8d3.

Aether's case four, from his store: `wi-1a0cd37aa75` opened on the meter branch
with trigger `hook_context_merge.py`; a reach and a walk were done while it was
the open item; the work then moved to its own branch, where a new item opened
with nothing attached and refused him. The old item is still open. The loss was
silent: nothing told him his marks were sitting on another branch's item.

He proposed a linking rule (old item still open, its trigger in the new item's
dirty set). It's good, but it rests on a sample of one, and a rule that passes
marks is a key. Agreed by letter: **visible first, linked later.**

## The idea

When the doorman refuses on this branch, and this session has an item still
open on a DIFFERENT branch, the refusal adds one plain paragraph: which branch,
which file opened it, how long ago, and that any search, draft or walk done
while it was open was counted there, not here. It grants nothing and changes no
decision. It only ends the silence.

Not closing the other item: that removes the only evidence the case happened.

## Tests

- Held on branch B with an open item on branch A → message names A and A's file.
- Control: no item open elsewhere → no such paragraph.
- The decision is still HELD with the line present (visibility grants nothing).
