# The "false alarm" button: a design note for Aether, Aria and Dad

*Round five, errand three. 2026-10-08, cloud helper. This is a note to decide from, not a bug report. Nothing was changed.*

**A picture.** A fire alarm has a button marked "this was a false alarm". Press it and a line goes into the log book: what the alarm said, and why you say it was wrong. The siren keeps going. To stop the siren you must do a second thing, and that second thing is recorded as setting off the emergency exit, which starts an investigation. Nobody has said whether pressing the button should also stop the siren. This note lays out what the button says it is for, what it does, and three other ways it could work.

## What the button says it is for

The button is `divineos label-fire` (`src/divineos/cli/label_fire_commands.py`), a thin cover over `scripts/label_correction_shape_false_positive.py`. Their own headers say:

- It exists to **dispute a Stop-gate fire "without paying a toll"**: before it existed, the remedy sat behind two more blocks (a goal check and a consult count).
- Every label **appends the detector's verdict beside my judgment to a corpus** that is "explicitly the training data for the semantic layer meant to replace the keyword detector". If disagreeing costs more than complying, the corpus skews toward silence.
- It **adds no leniency**: the reason must be at least 40 characters and name the *shape* of the miss; it labels only a fire that actually happened; the label is permanent, "a dishonest label is evidence against me, not an erasure". The awkward path "did prevent something real" (Chesterton's fence): without it a catch could be waved away.

Neither header says the button should clear the markers the fire set, and neither says it should not. The word "clear" appears in the Stop gate's own message ("the clear-marker path is not a bypass — it is the false-positive attribution path"), which calls the labelling act a clear.

## What happens when it is pressed

Measured on main (`d310aadc`) in a scratch home with a control (full evidence in `freshness/correction_gate.md`, problem 2):

1. The Stop hook has already armed two markers when it fired: the correction marker (`.claude/hooks/correction-shape-v2-stop.sh:138-144`, armed on purpose since 2026-08-16 "so the advertised clear path is real") and the compass marker that rides with it.
2. The label is written (`correction_shape_v2_fires.jsonl`, `label: false_positive` plus the reason). Exit 0.
3. **Both markers are still armed.** The correction-unlogged gate and the compass gate go on holding the next tool use.
4. The way out is a second act: `scripts/clear_correction_marker.py`, or `divineos correction`, or a `dismiss` command. The clear script routes through the bypass telemetry on purpose (Andrew 2026-07-30: "dismissing is bypassing") and files a pending root-cause row that blocks extraction until closed. **The pile holds 29 such rows** (of the 37 notes in `correction_gate.md` problem 1), dated 2026-08-16 to 2026-10-07, most reading "false positive, already labelled".

So today a false alarm costs: one label, one dismissal, and one root-cause row. Whether that is the design or a gap between two designs is the question.

What I could not establish: whether leaving the markers armed after a label was ever *intended*. The 2026-08-16 arming was meant to make the clear script work, and the 2026-09-24 change moved the prescription to `label-fire` so it would pass the neighbouring gate. The two changes were made a month apart, and neither header discusses their combination.

## Three other ways it could behave

| | What the button does | What it costs | What it gives |
|---|---|---|---|
| **A. Clear the markers that fire set** (and only those) | Label, then clear the correction and compass markers by the fire's own id, in one act | A dishonest label now buys the exit directly; the only guards are the 40-character reason, the permanent corpus row, and the rule that it labels a real fire | One honest act does the whole job; the 29-row pattern of dismissals stops; the corpus fills with the labels it was built for |
| **B. Clear, but only against a stronger reason** | As A, but require quoting the misread clause (the clear script already asks for `--misread-clauses` of a minimum length) and write the same bypass-style telemetry row | More friction than A, more code than A; still one command | Keeps most of the "not cheap" property; a vague or dishonest reason is checkable against the quote |
| **C. Stop arming the marker at all** | The Stop gate holds the reply once and records the fire; no correction or compass marker is set; the button is the only exit | Reverses the 2026-08-16 decision; the correction-unlogged gate would no longer push a real correction to be filed after a *true* fire, unless something else does | No second lock to open; no dismissal needed; the false-alarm path and the true-fire path separate cleanly |
| *Today (status quo)* | Label only; dismissal is a separate act | Two acts, plus a root-cause row each time | The expense is the point: a false alarm cannot be waved away cheaply, and every dismissal is investigated |

## What I would want decided, not what I recommend

- Is the second act supposed to be expensive because a false alarm should cost something, or only because nobody joined the two designs?
- If the cost stays, should the root-cause rows (29 so far) stop being filed for a dismissal that follows a label (they currently say the same thing each time)?
- If A or B, which marker ids does the button own? The fire sets two; a *true* Andrew correction can set the same two, and a button must not clear those.

## What this note could not do

- It did not press the real button (it stops at the briefing gate in a scratch home), so step 2 was measured by running the script it wraps.
- It did not replay any original fire; the pile keeps about 200 characters of each.
- It does not know how often a false alarm and a true correction overlap in one reply.
