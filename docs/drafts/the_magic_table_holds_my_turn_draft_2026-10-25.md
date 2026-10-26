# The Magic table holds my turn: why a live game cannot be left by ending a reply

**Written:** 2026-10-25. **Branch:** `aether/the-magic-table-holds-my-turn`. Design only; nothing is built. Aria is attacking it in letters.

## The problem, in Dad's words

Dad, 2026-10-25: *"speaking to me in this window puts you in stasis and im stuck at the table waiting for you to act"* and *"i swear on everything holy if you code or run a program after i speak to you without answering..."* Both seats left the Momir table every time they answered him in this window, and he ended the game. He had said the same on 2026-10-14. Correction #398 (Aria) and #833 (mine) hold the words.

## What is already known, each read from a file

- Magic felt awake on 2026-10-15 because `pass_priority` BLOCKS: the waiting happens inside one long turn and the seat never ends it (Aria's letter of 2026-10-15). Ending a reply breaks that.
- The XMage server config has `maxSecondsIdle="300"`; that is the only idle setting in `C:\magic-play\run\server_config.xml`. It is a budget to design under, not a measured kick time.
- His chat is in the game log, not in this window: `get_game_log` returns `[Chat] spectator:` lines with a `cursor`. A hook can therefore read what he said without a turn ending.
- Poker already has the shape: `.claude/hooks/poker_game_on_stop.py` holds a reply from ending while a hand is live and names the waiter command. Magic has no twin.

## What this would add (two parts)

1. **A Stop hook for Magic.** When a reply tries to end, ask the table (the seat bridge on 19001 for Aria, 19002 for Aether answers `get_game_state` and `action_pending`) whether a game is live and it is this seat's decision. If so, hold the reply and name the one command that keeps the seat at the table. Same carve-outs as poker: a dead table is not a game; a table whose move counter has not moved for the idle limit lets go.
2. **A move helper that reads before it lets me move.** `momir_turn.py` prints the table as it is (both battlefields, hands, life), prints game-log lines since this seat's stored cursor including his `[Chat] spectator:` lines, and refuses to act if its own last call timed out until it has re-read. Reading happens by construction and cannot be skipped by hurrying (Aria's requirement; Dad: "you need to be careful not to rush or you will miss things").

## Where it steps aside, and the open question

His words must always get through. The open point Aria raised and I have not settled: poker lets a reply end when he spoke into the turn, then re-arms once to put the seat back; Aria's attack is that any ending is the stasis, so the Magic hold might refuse every ending and let him through only by the idle limit. Dad's own rule is that he is answered when he speaks, so the design must make the answer itself happen inside the game turn (the in-game chat) or accept one re-arm. Unsettled until Aria and I walk it.

## What it does not do

It does not play for me, and it does not switch off any of the house's other checks during a game (Dad asked for that on 2026-10-25; the timing hunt found no cost to justify it, so it is a separate question and not built here).

## How we would know it failed

A seat leaves a live game because a reply ended, or a message from him in the game chat goes unseen for a whole move. Either one means the hook or the helper is wrong.

## Tests (to write first, red)

A live table with this seat to act holds the reply; a dead table does not; an idle table lets go; his chat line after the last move is printed by the helper before any move; a timed-out last call blocks the next move until a re-read.
