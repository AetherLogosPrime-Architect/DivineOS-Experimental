# One button: `label-fire` records the dispute AND clears the lock the alarm set, and refuses any lock it did not set

**Author:** Aether, 2026-10-09. Design B from the helper's two-locks note, Aria's first-hand run and her three requirements, and Aletheia's change of shape (record who set it, never read the words). **A draft for Aria and Aletheia to read before any code.** It builds on `aether/the-marker-records-who-set-it`.

## What happens now

One false Stop-gate alarm costs two clears. Counted read-only across the 38 false-positive clears on record: in 24 the Stop gate had armed the correction marker itself, so the second lock was the alarm's own. `label-fire` records the dispute (a row in the corpus a better detector will learn from) and leaves the marker armed; the next command is refused until `clear_correction_marker.py --misread-clauses ... --reason ...` is run too. The help on `aether/label-fire-help-tells-the-truth` now says so. This draft is the real repair.

## The change

`divineos label-fire --reason R --misread-clauses C`: after the labeller records the dispute, B reads the marker. It clears the marker only when `source == "stop-gate"` (the field from the marker branch) and, in the clear's record, names the rule that matched: `source == stop-gate`. It then runs the same clear the key runs, so the `misread-clauses` quote and the bypass telemetry row are unchanged.

B refuses, and clears nothing, in every other case, and the refusal teaches:

- `source == "his-message"`: prints the trigger text and says plainly *this lock was set by his message, not by the alarm you labelled; a real correction goes to `divineos correction`*.
- `source` missing (a marker from before the field): prints the trigger and says *its setter is unknown and unknown is never treated as the alarm*.
- No marker present: says there is nothing to clear and that the label was still recorded.

Aria's two asks from 2026-10-09 are here: the whole-source comparison with the matched rule named in the clear's record, and a refusal that prints the trigger text found. Aletheia's: it compares a recorded field and never the prose.

## Tests, failing first

1. a stop-gate-sourced marker + `label-fire` -> cleared, the escape log names `source == stop-gate`;
2. his-message-sourced marker whose text BEGINS with the stop-gate string -> refused, marker intact (the case that makes a prefix check unsafe);
3. a marker with no `source` -> refused, marker intact, message says unknown;
4. no marker -> label recorded, "nothing to clear";
5. `--misread-clauses` missing or under its length floor -> refused before anything is cleared (the key's own rule, unchanged).

## Not in this change

The CI-notice path (closed history, Aria's trace), the 91 misfiled rows (done at Dad's word), and any change to the Stop gate's detection.

## Falsifier

If a stop-gate-sourced marker survives `label-fire`, or a his-message-sourced one is cleared by it, test 1 or 2 fails.
