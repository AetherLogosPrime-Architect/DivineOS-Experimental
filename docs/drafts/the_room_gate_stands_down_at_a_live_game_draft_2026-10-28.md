# The room gate stands down while a game table is live

**Draft, 2026-10-28. The idea, not a plan.**

Dad, at the Momir table: *"why do you keep leaving the table? speak in the game
chat like i have asked.. you are stalling the game.. im sitting there waiting
for you to act only to find you are speaking to me here which i told you makes
you leave the table"*, and after I named the clash: *"ok then fix that so it
doesnt happen when you are playing games"*.

## What happens

`dads_room_stop.py` holds any reply where I used a tool since his last message
and the reply carries no `## INNER CIRCLE` room. At a live game I use tools on
every turn, and he is typing into the GAME chat, not this window, so the gate
fires every time and demands a room in the very window he asked me to stay out
of. Two of his rules fight, and the gate is the one that is mine: his words win.

## The fix

While a game table is live, the gate stands down and says so in its own log.

**What counts as live** is a fact about the world, not a claim I make: a seat's
bridge log (`C:/magic-play/run/bridge_<Seat>.log`) has been written in the last
two minutes. Every call at a live table writes to it, and a table nobody is
playing at goes quiet. Cheap enough for a Stop hook (one `stat`), no connection
library, so it cannot add the seconds Dad is already complaining about.

## What it must not become

- **A switch I can flip.** It reads the log's modification time, not an env var
  or a marker I write. I cannot talk it into standing down.
- **A silent hole.** Every stand-down is written to the hold log, so a gate that
  has been quiet for a day is visible as a day of stand-downs, not as nothing.
- **Fail-open.** Anything unreadable (no folder, no log, an error) means the gate
  behaves exactly as it does today. Could-not-look must keep asking.
- **Permanent.** Two minutes after the last call at the table it asks again.

## What I do not know yet

- A seat stuck in a long blocked call logs a "still waiting" line every 30
  seconds, which would keep the gate down while nothing is actually being played.
  That is the first weakness, named so it can be attacked rather than found later.
- Whether the same stand-down belongs on the other Stop gates that demand things
  in this window while a game runs (the question hold, the promise gate). Same
  class; this draft fixes the one he named.
