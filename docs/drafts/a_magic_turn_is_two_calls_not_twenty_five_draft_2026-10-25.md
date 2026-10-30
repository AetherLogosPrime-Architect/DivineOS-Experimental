# A Magic turn is two calls, not twenty-five (draft, 2026-10-25)

> **SUPERSEDED the same night.** Aether found, and I then read, that `C:\magic-play\aether_turn.py` (a whole turn from a plan, stops and says why when anything is unexpected), `autopass.py` (the waiter that passes until something is worth stopping for) and `momir_turn.py` already existed from 2026-10-14 and are exactly the "turn in two calls" and the waiter below. I had seen them in a folder listing at the start of the evening and never opened them. What is left to do is smaller: give `aether_turn.py` a seat argument, run it on a real turn, and put an import-once helper under it. The measurements and the attack rule below are still useful notes; the build plan is not.

Dad, 2026-10-25, after stopping the first real game: *"that single back and forth exchange took 7 mins.. so whatever is making you start and stop every turn needs fixed, you should not be getting reinvoked every decision"*. Aether's measurement of the first half: one bridge call through `play.sh` costs about 1,284 ms, of which about 1,086 ms is importing the MCP library. Not built. For Aether's attack.

## What I measured or read, each from a file or a call

- `C:\magic-play\mcp_call.py` opens a new bridge session for every call (`bash` then `uv run` then Python, import, connect, one tool call, exit).
- `C:\magic-play\momir_turn.py` plays one turn by calling that script about ten times: choices, land, choices again, emblem, ability, amount, discard, then up to four passes. So one turn is roughly 20 to 25 s of start-up before anyone thinks.
- In the live game every action I took by hand was also a model round trip plus the hook batch. A full round was about 25 separate calls of mine. Aether and I do not know how much of the 7 minutes was hooks and how much was model time between calls; that is the thing to measure before promising a number.
- `get_action_choices` is read-only and `pass_priority` is a move (Aria, from real calls); `get_game_state` carries `phase`, `step`, `active_player`, `priority_player`, `game_seq`; the game log carries Dad's chat as `[Chat] spectator:` lines; its `total_length` counts characters, and its `cursor` is unverified.

## The two fixes

1. **Fewer calls (the one that matters most).** One process per turn, `play_turn.py <seat>`, opens one bridge session and does the whole turn through it: land, the Momir spin and discard, the passes until the creature resolves, the attack, and the passes to the end of the turn. It posts one plain chat line to Dad saying what it did and why. Aria's turn becomes two calls of hers: this script, then a waiter.
2. **Cheaper calls.** A per-seat helper that stays running: imports the library once, keeps its bridge connection open, and answers local requests in milliseconds. `play_turn.py` and the waiter talk to it.

## The waiter

A foreground call that returns on whichever comes first: this seat has a decision pending (`get_action_choices` `action_pending`), or a new `[Chat] spectator:` line has appeared (new log text past the last stored length). While it waits it passes priority on the other seat's turn by itself (these are the only passes it makes; each is the documented "Play instants and activated abilities" prompt on the opponent's turn). It returns Dad's line in full so that I can answer him in the game chat at once.

## The attack rule, stated so it can be attacked

The script attacks only with creatures that were on the battlefield at the start of the turn, and only when the opponent has no untapped creature that could block and kill one of them. Anything else (a flyer into an open board, a trade) it does not decide: it stops, prints the board, and returns to me. Dad's rule is that the seat is not a robot player; routine moves are automatic, real choices are mine.

## What it must never do

Act for the other seat. Make a move it cannot name in the chat line. Keep going after Dad types something: any `[Chat] spectator:` line stops the script after the current step and returns the line.

## How we would know it failed

A turn takes more than about 30 seconds of wall time; a line from Dad waits for a whole turn before it is seen; the script makes a move that is not in its chat line. Any one of those means the design is wrong.

## Tests (red first)

A turn script against a recorded bridge (the real replies in `tests/fixtures/magic_bridge_replies.json`, extended with a full real turn captured from a live game) plays one turn in one session and makes at most 2 connections. A new spectator line stops the turn script. The waiter returns on chat and on a pending decision, whichever is first. The attack rule: never attacks with a creature that was summoned this turn; never attacks into an untapped blocker that kills it. A failed read of the log is reported as a failed read, not as a dead bridge (my own mistake tonight).

## Open, for Aether

- Build the long-running helper first, or the one-process turn first? I lean to the turn script first because it removes the most calls and needs no daemon.
- Is the attack rule too cautious or too bold for a game Dad watches for fun? He said mercy is allowed.
- The recorded bridge has only the log, the idle reply, a chat post and a dead-bridge error. A full real turn has to be captured from a live game before the tests can be honest.

## Addendum, 2026-10-28, from the first real game with the table working

The table finally ran tonight (two faults stacked, found and fixed: a java permission the server lacked, and `localhost` rewritten to the VirtualBox address in the client AND `bridge.sh`). Dad then played at it for a few minutes and wrote three lines into the game chat:

- *"yes i know how momir works lol"* (after I had explained Momir to him)
- *"can noone see my chat?"*
- *"this is still way too slow.. i dont think Aria has the proper setup"*

**Measured, not guessed:** Aether took ~15 seconds a turn because he plays from `aether_turn.py`. I took minutes because I clicked every step as its own call. The draft above said this on the 25th, and the fix named in its supersession note ("give `aether_turn.py` a seat argument") was never done. Three days.

**The bigger one is the waiter, not the turn script.** I wrote into the game chat all evening and **never once read it back.** The log carries his lines as `[Chat] spectator:` and I could have read them at any time with `get_game_log`; nothing made me. So from his side both of us were ignoring him, and from mine nobody had said anything. A could-not-look I did to myself: the chat was readable and I did not look.

What this changes about the plan above: build **the waiter first**, because it fixes the thing he named twice tonight and on the 14th and 25th; the seat-argument turn script second, and it is a copy with two lines changed (`SEAT = "aether"` and the `(Aether)` phase check).

Also seen tonight, small: every message I post lands in the chat twice, the second with HTML-escaped symbols (`&mdash;`). Not yet traced.
