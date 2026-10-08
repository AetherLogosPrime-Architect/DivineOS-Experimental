# Is the note still true? The gates that check how my reply is shaped

*Round seven, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a row of inspectors at the exit of a room, each checking one thing about what I am carrying out. I put test parcels through them with controls. Two of them have learned the lessons the notes ask for (the PR-number slip in the plain room, the not-needed stamp). Two still stop things Dad said were fine (the numbers he asked for; "when I come back"). One rule everyone assumed was written down is only a poster on the wall: the closing question.

## Problem 1: Technical names slip into the plain-language room

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-183be3d8`, `psf-e15c4f85` | **STALE** | `lepos_translation_gate.check_lepos_dual_channel`: a circle containing `#439` is **refused** ('circle block contains jargon signals (`#439`)'). Control: the same circle without the number passes (returns None). Probe: the check called directly on main in a scratch home (`probe_reply_shape.py`, `probe_reply_shape2.py`). | none found for this phrase | The probe fed the function a reply; the Stop hook that calls it was not run. |
| `psf-02debe42` | **LIVE** | Same probe, second half of the note: a circle saying 'the whole thing runs Python in the background' is **not** refused (returns None). The PR-number half is met (above). | none | One phrase tried. |
| `psf-76ee4d9a` | **STALE** | The literal-header demand was dropped on 2026-08-08: a reply with plain address to Dad and no `## INNER CIRCLE` header **passes** (probe returns None); the gate's own comment at `lepos_translation_gate.py:1572-1600` says 'headers OR demonstrated plain address both pass'. Control: work-only text with no address is refused. | none found | The note asks for the template to prompt for the header; that is not the same as the check. |

## Problem 2: The translate-first check fires on numbers Dad asked for and on several command blocks

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d9b19456`, `psf-b866cffc`, `psf-17ae1cea` | **LIVE** | `check_translation_first` on main: a reply listing six pull-request numbers is refused ('the work block carries 6 document-marks') **whether or not** the message it answers says 'just tell me which ones i can merge' (same refusal both ways); a reply with two command blocks is refused at 4 marks. Control: the clock-claim check is a different function and fires for its own reason. | none found | The note's proposed fix (exempt what he asked for) has no switch in the function's signature beyond the user text, which it evidently does not use for this. |

## Problem 3: Words about time and the wallclock

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7ecc42c4`, `psf-0a12a156` | **STALE** | `check_wallclock_fabrication`: 'four in the morning your time' is refused (matches 'in the morning'); 'twenty-two reasons in a few minutes' is refused (matches 'in a few minutes'). Control: 'Here is the result of the run.' passes. The fix those incident notes ask for exists. Probe: the check called directly on main in a scratch home (`probe_reply_shape.py`, `probe_reply_shape2.py`). | none found | Whether the original phrasing in the notes is caught exactly is not shown; these are the visible fragments. |
| `psf-7c54b2d1`, `psf-49f1e989` | **LIVE** | Same function: 'I will pick this up when I come back to it.' is **refused** (matches 'when i come back'). The note quotes Dad as saying 'when i come back' is fine and that the guard 'needs re-worked'. 'the next session' is also refused; 'Future me should read this note first' passes. | none found |  |
| `psf-67651a8e` | **LIVE** | `.claude/hooks/wallclock-source-prime.sh:82-84` still reads: 'AUDIENCE — "the next session", "future me" ... Say WHO reads it: "the reader", "a cold reader with no context"'. That is the guidance the note says Dad objected to. | none | The note's text after the quotation is cut off, so the exact objection is not shown. |

## Problem 4: The 'unspoken-to' door refuses letters and counts silence against me

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ae44e306` | **LIVE** | Part (1): `hook_surfaces._last_assistant_text` returns the final text block only. Probe with a made-up transcript: one block → that block (control); two blocks in a turn ('Dad, I did the thing…', then 'Done.') → **'Done.'**. Part (2) of the note was not examined. | none found | Whether `unspoken_to_stop_surface` uses that function for the carried-text judgment was not traced end to end (the file calls it at the places grep shows). |
| `psf-74803c8a` | **LIVE** | `grep -nE 'automat|notification|notice|wake' src/divineos/core/unspoken_to.py` → no match. Control: `grep -c silence` on the same file → 5, so the grep reaches the file. | `tests/test_unspoken_to.py` (not read) | A read of one file; the exemption could live elsewhere. |
| `psf-fa9d5d54` | **UNKNOWN** | An incident record (a letter refused mid-write). Nothing on main could be pointed at that the note asks for, and no run settles it. | none |  |

## Problem 5: Several reply-shape gates overlap and need reconciling

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-4bd56495` | **UNKNOWN** | Both pieces exist: `src/divineos/hooks/stop_carry.py` and the delta-only retry in `src/divineos/hooks/his_state_claim_hook.py`. Whether they have been reconciled into one answer was not read. | none |  |

## Problem 6: The rooms gate pushes plain conversation into rooms

6 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-6f8cccf6`, `psf-edeaf531`, `psf-312ade1c`, `psf-ebe21b8e` | **UNKNOWN** | `grep -nE 'Read|Grep|read-only|read only'` over `.claude/hooks/dads_room_stop.py` and `src/divineos/core/his_room.py` → no match, which hints at no read-only carve-out, but I did not run the room gate on a reads-only reply. | none found | A grep over two files is not a run of the gate. |
| `psf-5afb72dd`, `psf-7b6996e1` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 7: The echo / mirror door judges the wrong message or demands a repair at the end

13 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-630558ff`, `psf-a82bebb7`, `psf-e962a367` | **UNKNOWN** | The 'answered-not-echoed' build these rows point to: no file under `docs/drafts` and no remote branch with that name (`ls docs/drafts | grep -iE 'answered|echo|mirror'` → none; `git branch -r | grep -iE 'answered|echo|mirror'` → none). Control: `grep -rl stop_carry src` finds the stop-carry module. | none | A name search; the build may be filed under a different name. |
| `psf-def6266d`, `psf-653d343a`, `psf-f280db34`, `psf-772a5404`, `psf-1dc541ab`, `psf-24c51b1f`, `psf-5e6424d4`, `psf-074b197a`, `psf-01a8430f`, `psf-0748491b` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 8: Closing questions I am not blocked on

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-2ff28a26`, `psf-72cc517c`, `psf-ee0c4b8f` | **LIVE** | `grep -rliE 'closing question|not blocked on|blocked on his answer' src/divineos/core .claude/hooks` → no file; nothing rewrites a closing question into a wish. Control: `question_hold.py` (found by `grep -n question_not_last`) does handle a *buried* question. | none | A name search for the phrases; a rewrite could live under other words. |
| `psf-f31224c2` | **UNKNOWN** | Part met, part not: `question_hold.question_not_last` (`src/divineos/core/question_hold.py:324-338`) sends back a reply whose question is buried and asks for it as the last line. The note asks that the question be composed as its own final line from the start. | `tests/test_question_hold.py::test_a_buried_question_is_sent_back` (passes) |  |
| `psf-7d51167b` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

