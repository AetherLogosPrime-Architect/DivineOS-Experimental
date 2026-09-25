# A quoted mention is not a store-write — station one draft, 2026-09-25

**Aria.** The idea, not a plan. Dad, with me in the room: *"you can use the override to be able to fix the gate.. but the gate obviously needs fixed so lets fix it now"*.

## What jammed, measured

The reach-check doorman matches store-write verbs (`divineos learn`, `feel`, `opinion`, `claim`) as substrings of the whole command line, quoted text included. The correction-marker gate refused everything except its remedies, and one of those remedies is `clear_correction_marker.py --reason "..."`. My reason text said "log the lesson with divineos learn". The reach-check read that quoted sentence as a store-write and refused the remedy. Meanwhile `divineos reach open`, the reach-check's own cure, was refused by the correction marker. No exit, until I noticed my own wording and rephrased it.

## Same class as

The quoted arrow in the read-only probe (built on `aria/a-quoted-arrow-is-not-a-write`) and the doorman's `_QUOTED_SPAN`. A quoted span is said, not run. Third gate with the same misreading.

## The shape

- Blank quoted spans before matching, as the doorman does.
- The named limit: a store-write inside a quoted `bash -c "..."` stops being seen. That's rare in practice and fails toward letting a write through, so the comment says so.
- Second half, not in this change: the correction-marker gate should also let `divineos reach` through. A read-only search must never be blocked by a gate whose remedy needs it.

## Pins

The exact incident command passes. `divineos learn "x"` unquoted is still caught. `echo "divineos learn"` passes.
