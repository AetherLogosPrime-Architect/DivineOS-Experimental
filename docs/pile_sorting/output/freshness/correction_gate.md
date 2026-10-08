# Is the note still true? The alarm that rings when I make a mistake

*Round four, job A. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence comes from `origin/main` at `cc4714dc`. Verdicts are per group of rows that describe the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for.*

A picture: the alarm was rebuilt in July so it would stop ringing at people reading out an old mistake from a book. I went to see if it still rings at the reading. On the part that listens to my own replies it does, and the button that says 'false alarm' records the complaint but leaves the siren running.

## Problem 1: The alarm cannot tell talking-about a mistake from making one

37 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-fa9aeb09`, `psf-04f39c37`, `psf-9eedd90a`, `psf-729f3d5e`, `psf-bfc25423`, `psf-70521680`, `psf-56e9517e`, `psf-ce155490`, `psf-34847b86`, `psf-e64cbb26`, `psf-eeed0e6f`, `psf-12197f9d`, `psf-37376d45`, `psf-9d6a80d5`, `psf-18dd5983`, `psf-b714ba5a`, `psf-062847a5`, `psf-956d189b`, `psf-671bc61d`, `psf-2c5d2177`, `psf-3e9612de`, `psf-51a539b7`, `psf-855a85b8`, `psf-71d8ee80`, `psf-1122a385`, `psf-0744fc0f`, `psf-f94e1d30`, `psf-fc9a2755`, `psf-60269c02` | **LIVE** | `src/divineos/core/correction_shape_v2/self_admission_detector.py:77-119` fires on first-person clauses such as 'my mistake', 'I should have X', 'Corrected:'; `:126-161` lists the only MENTION suppressors (meta nouns, example markers, quotes, code fences) and none recognises a recap of a correction already filed; nothing looks the filed corrections up. The rows themselves are bypasses recorded from 2026-08-21 to 2026-10-07, after the document-level saturation fix (`:46-70`) and after #519 (2026-09-30). | `tests/test_self_admission_saturation.py` covers the saturation rule. **No test replays the labelled false fires** (the corpus `correction_shape_v2_fires.jsonl` is not read by any test I found). | I did not replay the rows' original replies (the pile keeps about 200 characters of each). 'LIVE' rests on the missing suppressor plus the recent dates, not on a reproduced fire. |
| `psf-f91c18c5`, `psf-8c5a56c0`, `psf-f23930c2`, `psf-ba9070ee`, `psf-c0bed135`, `psf-74bcc45d`, `psf-f2aa62e6`, `psf-68fb54ca` | **UNKNOWN** | Older rows about the prompt-side detector (Andrew's typed words) and one genuine catch. Main has `correction_marker.py:171` `strip_relayed`, `:188` inline-quote strip, `:368-396` external-agent proximity backstop, and `tests/test_correction_marker.py:222-377` (relayed audit, sign-off, blockquote). But rows `f2aa62e6` and `74bcc45d` report 'wrong' firing on a relayed report on 2026-08-17, after those fixes. | `tests/test_correction_marker.py:222-377` for the mitigations | Cannot tell whether those 2026-08-17 shapes still fire without the original messages. `c0bed135` is a genuine USE caught at confidence 1.00, not a defect report. |

## Problem 2: Calling a fire false should silence everything that fire raised, in one step

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ee539796`, `psf-93fc5313`, `psf-b65a7331`, `psf-bf10df4a` | **LIVE** | Live probe in a scratch home with main's code: `set_marker()` armed both the correction marker and the compass marker; running `scripts/label_correction_shape_false_positive.py` (what `divineos label-fire` wraps, `src/divineos/cli/label_fire_commands.py:64-75`) exited 0 and wrote the label, and **both markers were still present afterwards**. Code: `scripts/label_correction_shape_false_positive.py:156-160` writes the label only; `correction_marker.py:656` `clear_marker()` (which also clears the compass marker) is never called from either file. | `tests/test_the_stop_gate_names_a_door_that_opens.py:34-46` proves the remedy passes the neighbouring gate; nothing proves it clears anything. | The CLI wrapper itself could not be run in the scratch home (it stops at the briefing gate), so the script it wraps was run directly. |
| `psf-4e9e1658` | **UNKNOWN** | Row is cut off at 'Named defect: clear_correction_'. Main's Stop hook arms the marker it asks you to clear (`.claude/hooks/correction-shape-v2-stop.sh:122-144`), which looks like the defect named on 2026-08-16. | none found | The visible text does not say which defect it names. |

## Problem 3: The alarm names exits that cannot actually be reached

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a9ceb280`, `psf-b2f4c4e8` | **UNKNOWN** | Mixed: the shut door (prescribing `python scripts/label_…`) is fixed — the hook now prescribes `divineos label-fire` (`correction-shape-v2-stop.sh:210-211`) and `tests/test_the_stop_gate_names_a_door_that_opens.py:34-46` walks it through the neighbour's matcher (control at `:49`), carried by `540a761c` (#519). But the path still leaves the marker armed (see problem 2 above). | `tests/test_the_stop_gate_names_a_door_that_opens.py` | Whether the original complaint was the shut door or the armed marker cannot be told from the visible text. |
| `psf-79fd7f4c`, `psf-31f0ebba`, `psf-51b21edd`, `psf-f624d5a2`, `psf-35fdfcb2`, `psf-6b25dbf3` | **UNKNOWN** | Rows cut off before naming the exit that failed ('all three prescribed e…', 'the marker…', 'gates blocking each other in a…'). `f624d5a2` is about the harness's auto-mode classifier refusing a script as bypass-shaped, which is not code on main. The two rows dated 2026-09-18 and 2026-09-19 precede #519 (2026-09-30), whose test covers one shut door. | `tests/test_the_stop_gate_names_a_door_that_opens.py` covers one exit only | No test walks every advertised exit with the neighbouring gates armed, which is what the problem's 'how we would know' asks for. |

