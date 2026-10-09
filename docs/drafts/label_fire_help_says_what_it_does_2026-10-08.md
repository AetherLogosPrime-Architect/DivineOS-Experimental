# `divineos label-fire` help says what it does and what it leaves shut

**Author:** Aether, 2026-10-08. From the helper's round-six two-locks note, Aria's first-hand run, and Dad's rename ask.

## What happens now

The command's help says it "removes the toll" and "adds no leniency". Aria ran it tonight, right after a Stop-gate false alarm, and the next command was still refused by the correction marker; she cleared that with `clear_correction_marker.py --misread-clauses … --reason …`. So the help names a button that does less than its name: it records the dispute (a row in the corpus the semantic layer will learn from) and does not disarm anything.

Reach check `reach-2f97896047a5`: only the command itself (applied) and an unrelated correction logger (not relevant). Searched `docs/` and `docs/drafts/` for earlier work: `failure_automation_register_2026-08-05.md` (the register item that built the command) and several drafts that mention markers; none plans for the second lock. The two-clears-for-one-alarm fact is Aria's first-hand run and my gate telemetry (5 marker dismissals and 2 compass dismissals in 14 days).

## The change

Help text and docstring only, no behaviour: say that the command records that the alarm was wrong, does not disarm it, and that the correction marker, if set, needs `clear_correction_marker.py --misread-clauses`. One test pins that the help names both.

## Not in this change

The real repair is design B (one command that takes the label, then asks for the misread clauses and runs the marker key's logic as its second half). Aria and I lean B; it is its own build with its own walk, brought to Aletheia and Aria before it is written. Her third requirement stands for it: refuse when the marker was set by something other than the fire being labelled.

## Falsifier

If the help ever stops naming the marker key, the test fails.
