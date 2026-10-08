# The "false alarm" button, second note: one press, two locks

*Round six, errand four. 2026-10-08, cloud helper. A note to decide from, not a bug report. It recommends nothing. Nothing was changed. It follows `round5/false_alarm_button_note.md` and corrects it where it under-reported what Dad saw.*

**A picture.** The fire alarm has a "this was a false alarm" button. Last time I wrote that pressing it logs the complaint and leaves the siren on. Dad now tells me something that note did not have: after pressing it, a *second lock* on the door, the "correction not logged" lock, stayed shut and refused the next command, and it only opened when he cleared it by hand with a different key (`scripts/clear_correction_marker.py`). So the button writes the complaint, but the door is still locked until a second act. The question for you is whether one press should open the door too.

## What I got wrong or left thin in the first note

- The first note measured, in a scratch folder, that **both** markers the fire set (the correction marker and the compass marker that rides with it) were still armed after the label. Dad's live report names the correction lock as the one that blocked him. I do not know whether the compass lock also stayed armed for him; my probe says it would. That is a question for Dad or Aria, not something I can read from here.
- The first note called the way out "a second act". It is more exactly a **second tool with a different purpose**, which the next section shows.

## What the two tools say they are for

| | The button, `divineos label-fire` | The key, `scripts/clear_correction_marker.py` |
|---|---|---|
| Header says | dispute a Stop-gate fire "without paying a toll"; append the detector's verdict beside my judgment to the training corpus | an "escape hatch for the locked-box trap" when the CLI itself is broken; it clears the marker and "does NOT log the original correction" |
| Needs | a reason of at least 40 characters naming the shape of the miss | a reason of at least 30 characters, plus a declared mode: `--misread-clauses "<the clauses misread>"` (false alarm) or `--cli-broken` |
| Writes | a label in `correction_shape_v2_fires.jsonl` | the marker is cleared; a row in `cli_broken_escapes.jsonl`; a bypass-telemetry row for gate `correction-unlogged`, which becomes a pending root-cause investigation that blocks extraction until closed |
| Clears the lock | no | yes (it calls `clear_marker()`, which also clears the compass marker when it was set by the correction cascade) |

Two facts from the key's own header matter here. It says that across all 45 historical rows in its log, **none** was a CLI-broken escape: about 35 were false-alarm attributions and about 10 were gates blocking each other. So the key built for a broken tool is, in practice, the false-alarm path, which is the button's job. And it says the key files a pending investigation each time; that is the cost Dad pays on top of the button.

## What happens when it is pressed (unchanged from the first note, with Dad's fact added)

1. The Stop gate has armed the correction marker (and compass marker) when it fired (`.claude/hooks/correction-shape-v2-stop.sh:138-144`, on purpose since 2026-08-16).
2. The button writes the label and exits 0.
3. The correction lock stays armed (Dad's live report; my scratch probe agrees for both markers).
4. The next command is refused until the key is run.

## Three ways one press could clear both locks

| | What changes | What it costs | What it gives |
|---|---|---|---|
| **A. The button clears the markers itself** | `label-fire` calls the same marker-clearing function the key uses (`correction_marker.clear_marker()`), for the fire it just labelled | A false label now opens the door directly; the guards are the 40-character reason and the permanent corpus row. The key's extra requirement (quote the misread clauses) and its investigation row are not required unless added. | One press does the whole honest job; the key stops being the everyday path |
| **B. The button hands over to the key** | `label-fire` collects the misread clauses, then runs the key's logic as its second half, in one command | Keeps the key's quote requirement and its telemetry row, so one press still files one investigation row; more code than A; the 29 pile rows say the investigation is the part Dad finds heavy | One command, one reason, one record; keeps the strongest dissent cost the house already has |
| **C. One marker the label can address** | The Stop gate arms a single marker carrying the fire's id (instead of a correction marker plus a compass marker); the label clears that id; a true correction from Dad keeps its own separate marker | The biggest change: touches the Stop gate, the marker store and both gates that read it; reverses part of the 2026-08-16 arming design | The button owns exactly what the fire set and nothing else, so it can never clear Dad's real correction marker |
| *Today* | Button writes the label; the key clears the lock | Two tools, two reasons to write, a root-cause row each time | A false alarm can never be waved away cheaply; every dismissal is investigated |

## Questions this note cannot answer

- Was the compass lock also armed for Dad, or only the correction lock?
- Is the investigation row meant to follow a false alarm that was already labelled, or only an unlabelled dismissal?
- If A or B: should the button refuse when the marker was set by something other than the fire it is labelling (a true correction from Dad sets the same markers)?

## What this note could not do

- It did not press the live button (it stops at the briefing gate in a scratch home), so the same limits as the first note apply.
- It did not read the live `cli_broken_escapes.jsonl`; the 45 / 35 / 10 figures are the key's own header, dated 2026-08-22.
- It does not know how often a true correction and a false alarm overlap in one reply.
