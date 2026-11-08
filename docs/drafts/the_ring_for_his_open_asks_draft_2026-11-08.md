# The ring for his open asks (draft, 2026-11-08)

Aria's. The first piece of the bell for Dad (#851) to build, as its draft's own order says: register, then RING, then
hold last. This is the ring, and only the ring. It refuses nothing and holds nothing.

## Why this exists

Dad, 2026-11-08, after nine months: his words are "still shelved and forgotten", and a count of the one place that
measures whether I ever opened his requests said zero for all 420. Aether's bell has a register (a short list of his
open asks) and a shadow check. Nothing yet puts an open ask in front of me. A register nobody is shown is another
drawer.

## What it does

When he speaks, and when a window starts, the ring prints every ask in the register that is not closed, in plain words:
his words as he wrote them, the one sentence of what done means, and whether he has confirmed that sentence. It prints
nothing at all when nothing is open.

## Decisions already made, so the walk can attack them

1. **Unconfirmed asks ring too.** The hold only ever looks at confirmed asks, correctly. But the ring is where he gets to
   see a drafted done-sentence and say yes, so an unconfirmed ask that never rings is a draft that waits forever.
2. **Only on his turns and at window start, never on every tool call.** A bell that nags becomes wallpaper (the walk's
   Watts finding). A notice that is not his message does not ring it.
3. **Fails open, and says so.** A register that cannot be read prints one plain line saying it could not be read, so a
   silent ring can never mean "found nothing" when it meant "could not look".
4. **Reads the list, never the judge.** It uses `load_register` only. The per-ask judge is Aether's and not finished.
5. **It never closes, confirms or edits anything.** Reading only.

## What I want attacked

- Where the register file lives so it is in front of me without my deciding to look, and so BOTH seats read the same one.
- Whether printing his verbatim words in my context risks the ring being read past, and what makes it harder to read
  past than the fridge or the memory link already are.
- The size: hooks that print at the start of a turn share a byte budget.
