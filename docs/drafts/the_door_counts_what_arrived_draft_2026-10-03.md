# The door counts what arrived — draft, 2026-10-03

**Drafted by:** Aria. **Station one** of the build flow. It follows PR 584 (the door reads the name).

## Why

This morning the front door held every message of Dad's for an hour, and nothing said so. A door that kept nothing looked exactly like a door that was working. Later the same day a message of his ending in a smiley sat on Aether's seat as a candidate for a quarter of an hour, also silent, and it was found only because Aether read his table by hand.

Aletheia, reading 584: *"This PR fixes the clock. Only that surface would have told us. I'd treat the outage as closed only when both are in."* Aether: *"A door that only counts what it let in will always look healthy."*

Dad's rule, as he corrected it today: *"its never say something is fixed without it actually being fixed, which means dogfooding, live testing and actually plugging things in."* That applies to the door itself. The door has to be able to say whether it is working.

## What it measures, and from where

**The denominator is what arrived, never what the door accepted.** "Arrived" means every record in this seat's transcript that the app stamped as his (human origin, his words not only envelope). That's the app's own record, so the door cannot grade its own homework.

For each arrived record, one of these:
- **caught** — a candidate settled onto it. Report how long that took, from his record to the settle.
- **caught late** — settled, but the delay was more than a couple of minutes. That's this morning's shape.
- **missed** — no candidate ever settled onto it. Name the nearest candidate (same seat) and *why* it didn't fit: different id, words not equal (show both, ascii-escaped, so a garbled smiley is visible), outside the window, or no stamp.

And from the store's side:
- **stuck** — a candidate older than a couple of minutes with no record. Name the nearest record and why it didn't fit. This is the smiley shape, and it shows up in minutes, not after the hour's give-up.

## Added by the council walk (council-bd341db9df04)

- **Blind.** If this seat has candidates in the window but no arrived records at all, the report says it **cannot see him**. Zero arrivals while the door is keeping things is a broken instrument, not a clean bill (Breaker, Popper).
- **The window, named.** The report states the stretch of time it read ("the last day on this seat") and never claims more (Wayne).
- **Problems first.** Missed, stuck and blind lead the output, and the rate follows, so a fast glance lands on the evidence (Kahneman).
- **Late, from what was seen.** Today his records settled in seconds when the door worked and an hour when it didn't. "Late" is anything over two minutes (Jacobs).
- **This morning by hand, before code** (Polya): on my seat today there are 85 rows: 24 filed, 22 withdrawn (machine envelopes), and 39 unmatched, given up as "record never found". Those 39 are the case the report must show as missed, each with its nearest record and the reason.

## Where it shows up

1. **A command**, `divineos his door`, for the full picture on this seat: catch rate over a recent window, every miss and stuck one with its nearest neighbour and reason.
2. **In the refusal that already fires.** The sort-first refusal already stops work when his words wait. It should also name any *stuck* candidate right away, with the reason, rather than staying quiet until the give-up.
3. **One line in the briefing**: the catch rate for each seat, and how many were missed or stuck. A seat whose door has kept nothing at all (Aether's this morning) shows as zero kept. It can't look healthy.

## How it's proven

- Tests built from the real cases, with real UTF-8 bytes: the 14 late messages from this morning (caught late), the garbled smiley (stuck, with the reason "words not equal" and both texts shown), and a seat with no door (zero kept).
- Live: the report run on both seats against today's real transcripts. It should show this morning's late messages as caught late before 584, and catches after it. If it can't see this morning, the instrument is broken, and that's the first thing it has to prove.

## What this must not become

- A count of what the door let in. Every number is out of what arrived.
- A reader of his words. It compares text for equality and shows it. It never interprets it.
- A thing that grades itself green. Zero arrivals reads as "nothing to judge", never as "100%".
