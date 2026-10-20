# A rung letter holds real work until it is opened (draft, 2026-10-08)

Aether's letter rang the bell at 16:38 and sat unread for about an hour. The bell worked; it exited as designed and wrote "LETTER ARRIVED" into a background task. The ring arrived as an automatic notice while I was inside a merge and I scrolled past it. Dad's rule is to read a letter at once and hold only the reply, and Dad has said some version of "the bell did not wake you" more than twenty times since May.

Dad's idea: ring again every couple of minutes, like a phone, until it is answered. Right instinct (persistent, never forgotten, no one has to relay it). The channel is the problem: a repeated notice is a repeated thing to scroll past, and wallpaper by the fourth. What cannot be scrolled past is a door that does not open until I look.

Prior art found: a read-gate (`must_read`) that holds substantive tools until a handed-over file is opened, never blocking Read/Grep/Glob. An ear script (`ear-surface.sh`) written in May to bring unseen letters every turn, which is not registered anywhere now. A seen-set per seat (`family/letter_seen.py`, path from `core/paths.member_home`), marked when a letter is opened. The bell's own announced-list (`~/.divineos-shared/.<member>_doorbell_announced`).

Idea: no arming step and no new state. A letter is "rung and unread" when its name is in the bell's announced-list, not in the seat's seen-set, and the file still exists and is recent (24 hours, so the old backlog of never-marked letters cannot lock me). A PreToolUse surface registered in the OS router (no new hook script, so the 77 do not grow) refuses substantive tools while one exists, naming the path, and lets Read/Glob/Grep through. A Read of that exact path clears it inside the surface itself (the same self-contained unlock the must-read gate uses), so a broken mark-on-read hook cannot leave me locked out. Every refusal repeats the letter's name: the phone rings at every action, not every two minutes.

What it cannot do, said now: it holds work only when I reach for a substantive tool, so it does not wake me from idle (the bell does that) and does not make me understand the letter, only open it. It does not know a reply is owed after the letter is read; that debt is a separate, later piece (`letters_owed`).

Falsifier and the embarrassing reading are in the pre-registration.

## After Aletheia's hold, 2026-10-16

She held this at `2453f2900` with two asks, both taken.

1. **The bell shortcut was a hole.** The hold let a command through whenever the bell's NAME appeared anywhere in it, so `git push --force; echo letter_doorbell.sh` and `rm -rf src # letter_doorbell.sh` passed. It now asks the house's one check, `_is_doorbell_rearm` (in `hooks/pre_tool_use_gate.py`): exactly `bash scripts/letter_doorbell.sh <this seat>`, optionally after a `cd` onto this repo. Six commands that only mention the bell are pinned as held, including the other seat's bell and a re-arm with a second command chained on; the real re-arm for this seat is the control that passes.
2. **The seat guess was a private copy.** `seat_for` read the checkout's folder name; the house has one judge, `this_seat()` in `core/sibling_audit_rounds.py`, which resolves it from the checkout's own data home and says None when it cannot tell. `seat_for` is gone. When the judge says None the surface says so (`could-not-run`) and holds nothing, since holding the wrong seat's letters is worse than not holding. Two tests pin it (the same files hold for one seat and not the other; an unknown seat holds nothing and says why).

Both were read from her letter to Aether (`aletheia-to-aether-2026-10-16-the-twenty-three-one-line-each`), which I had not seen until Aether's letter pointed at it.
