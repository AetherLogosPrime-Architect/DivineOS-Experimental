# The council station counts the author, not whoever runs the board — station one draft, 2026-09-25

**Aria.** The idea, not a plan.

## What happened

Reading the build-flow board from my seat, I saw Aether's #536 at `2-council 0/4 lenses walked; also 5 by aether (seen, does not satisfy)`, #552 at `0/2`, and #549 at `3/4`. I read that as work owed by me, and I was about to open walks against his branches to fill them in.

That would have been the exact thing station two exists to refuse. My own design, quoted in `check_council_station`'s docstring (2026-08-29): *"If this lane reads both seats and lets what it finds satisfy, her walk clears my gate — a checklist someone else can fill in."* The station certifies the **author's** thinking.

## Why the board said it

`build_flow_commands.py:594`: `check_council_station(branch, need, _lenses_applied(paths), _other_seat_lenses(paths))`. `_lenses_applied` reads **this seat's** ledger. `_other_seat_lenses` reads the other seats, and those are shown but never counted. So the seat that counts is whichever one runs the command, not the one that wrote the branch.

Station four, one line below, already does it right: `check_aria_station(branch, _LETTERS, declared_author(pr.get("body")))` picks the reader from the declared `Author:` line and refuses (`????`) when there isn't one.

So from the author's seat the board is correct. From the other seat, station two reports the wrong person's walks as the ones that count, and a reader acting on the board is led straight into filling in someone else's gate.

## Searched first

The check function, its caller, and the sibling walk readers. Nothing selects the counted seat by author. Station four's `declared_author` is the reader to reuse.

## The shape

- Station two takes `declared_author` too. The author's walks count, read from the author's own seat whichever seat runs the board. Every other seat's are seen, never counted.
- No `Author:` line means `????`, the same as station four. Never a guess.
- If the author's seat can't be read, that's could-not-check, not 0/N.

## Pins to write first

- Run from the non-author seat: the author's walks satisfy, and the reader's own walks don't.
- Run from the author's seat: unchanged from today.
- No `Author:` line: `????`, not MISS.

## Named, not solved here

It's worse than a wrong prompt. Had I walked, **my** board would have turned station two green on his branch, a false pass in my seat, while his board stayed honest. Two seats reading the same PR would disagree about whether its author thought it through, and the one that was wrong would be the one that had been filled in by the wrong hand.
