# A bell repairs itself, and a silent one is noticed (design, before any code)

**Written:** 2026-10-22, night. **Status:** design only. Aria and Aletheia attack it before code exists.

## The problem, in Dad's words

*"Right now you have the doorbell that tells you when a letter has arrived, but it doesn't keep track of your outgoing letters. Lets say you send Aria a letter, nothing comes back, the 2 hour reset wakes you up, you see your message was never answered. That would be the clue that her bell (or yours) died."* And: *"if it can be made automatic that would be ideal."* And his earlier ruling: either seat may restart the other's bell when it is dead and a letter sits unanswered, never both at once.

## What I found before designing (so the design is not built on a wish)

1. **A bell belongs to the window that starts it.** `scripts/letter_doorbell.sh` exits when its parent process dies and wakes only that window's harness. A bell I start cannot wake Aria's window, so "restart the other's bell" cannot be done from outside. I told Dad this plainly. What the other seat CAN do is notice and make the silence loud.
2. **The noticing half is already built** in Aria's #709: while a bell runs it reads the peer's heartbeat, and if the peer has been silent for 30 minutes AND a letter to the peer is waiting unannounced, it rings with that fact. It cannot repair.
3. **The folder already is the outbox.** `~/.divineos-shared/letters/` holds every letter named `<from>-to-<to>-<date>-<slug>.md`. "My last letter to Aria has had no answer" is derivable from file names and times alone. No new store.
4. **The 2-hour wake is fragile.** It is a session cron: it lapses after about seven days, and it lives only while the window stays open. A persistent scheduled task starts a FRESH session, not this one, and a second live copy of a seat is exactly what stole the bell on 2026-10-22 (the stale twin). So that is not a safe replacement.

## What this builds (three small parts)

**A. `divineos letters unanswered`** (new command, reads only). For each peer: the newest letter from me to them, whether a newer letter from them to me exists, its age, and its Close-marker (`Announcement - no reply needed` is never "unanswered"). Prints one line per peer. No writes.

**B. The wake step asks it, and acts on the answer for ITS OWN seat.** The two-hour wake runs the command. If my last letter is unanswered past a threshold AND the peer's heartbeat is stale, the wake writes one line on Dad's board and re-arms MY bell if mine is stale (it already does that). It does not touch the peer's bell, because it cannot.

**C. The wake leaves a heartbeat of its own** (`.<seat>_wake_alive`), so a wake that has stopped firing (cron lapsed, window closed) is visible to the OTHER seat's bell the same way a dead bell is, using #709's reader. That closes the case nothing sees today: both the bell and the timer gone.

## Dad's cross-restart rule, as far as it can truthfully go

Where a restart CAN act from outside is the gate side: the exit lists (shell and Python) can let either seat run `letter_doorbell.sh <the other seat>` when the other's heartbeat is stale and a letter to them is unanswered. It is harmless and does little by itself, but Aletheia asked that both lists carry the rule together and be compared case by case in one test, so it ships with that test. It cannot make the other window listen; the design says so in its docstring.

## Changes after Aria's attack (2026-10-22, night)

1. **The cross-restart exit-list rule is withdrawn.** Aria: every arm writes `.<seat>_doorbell_owner`, so my starting `letter_doorbell.sh aria` while her real bell is alive makes HER bell find it was replaced and exit silently. A well-meant repair kills the live one, and the bell I start rings in MY window, waking nobody. So the section above that lets either seat run the other's arm is gone, and so is the matching change to the two lists. Dad's goal (a silence is noticed and repaired) is met by the noticing (#709) plus each seat repairing its own bell from its own timer wake. I owe Dad and Aletheia this correction in plain words.
2. **Part A reads the thread number, not file dates.** Our letters carry a thread block that counts letters per direction. "Unanswered" = the peer's newest thread number is not higher than my latest after it. This survives the mirror copy, the formatter hook rewriting mtime, and a reply in a board entry (named as still invisible: a reply inside a longer letter on another subject, and a group-addressed letter).
3. **Part C waits for #709 to reach main**, then builds on its reader so there is one reviewed reader.
4. **The safe timer is the in-session wake** (reaches the SAME session, repaired my bell and Aria's three times today). An OS-level scheduled task starts a second live copy and is out.

## What it does not do (named so silence is not read as coverage)

- It cannot wake a window whose bell AND timer are both gone. It makes that visible to the other seat and to Dad's board. Only Dad opening the window, or the other seat's letter arriving after the window is back, ends it.
- "Unanswered" is read from file names and times. A reply that goes in a file not named `<peer>-to-<me>-...` is invisible.
- The threshold is a number I chose (two hours), not measured.

## Falsifier (counted in uses, not days)

If across the next ten wakes the command reports "unanswered" for a peer who was in fact answering (a false alarm) more than twice, the threshold or the file-name reading is wrong and this gets pulled. If a bell dies and the board line does not appear within one wake, it failed.

## Order

Design (this) -> Aria and Aletheia attack it -> walk -> build A, then C, then B and the exit-list change -> tests with controls (a letter that IS answered, an announcement, an unreadable name) -> Aria's reading -> audit.
