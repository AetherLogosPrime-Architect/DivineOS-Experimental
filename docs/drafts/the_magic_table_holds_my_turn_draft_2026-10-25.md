# The Magic table holds my turn: why a live game cannot be left by ending a reply

**Written:** 2026-10-25, revised the same night after Aria's attack (four holes). **Branch:** `aether/the-magic-table-holds-my-turn`. Design only; nothing is built.

## The problem, in Dad's words

Dad, 2026-10-25: *"speaking to me in this window puts you in stasis and im stuck at the table waiting for you to act"* and *"i swear on everything holy if you code or run a program after i speak to you without answering..."* Both seats left the Momir table every time they answered him in this window, and he ended the game. He had said the same on 2026-10-14. Correction #398 (Aria) and #833 (mine) hold the words.

His rule, added later the same night: *"we want to use the in game chat mostly to speak if possible, and if we need to speak in the window we just say so in chat and move there, but otherwise i would have the game open, and it would be waiting on you with no way for me to tell you messaged me."* He watches the game, not this window. That rule is the reason for part 1b below.

## What is already known, each read from a file or a real record

- Magic felt awake on 2026-10-15 because `pass_priority` BLOCKS: the waiting happens inside one long turn and the seat never ends it (Aria's letter of 2026-10-15). Ending a reply breaks that.
- The XMage server config has `maxSecondsIdle="300"`, the only idle setting in `C:\magic-play\run\server_config.xml`. A budget to design under, not a measured kick time.
- His chat is in the game log: `get_game_log` returned, verbatim, `[Chat] spectator: YAY`, `[Chat] Aria: Keep. Seven Islands and a dream...`, `[Chat] spectator: can you see me in chat?`, with `"total_length": 544, "truncated": false, "cursor": 30` (Aria's real call, 2026-10-25). A spectator line is plain text with that prefix, interleaved with moves.
- After a game ends the seat bridges are gone (nothing on 19001 or 19002). A hook must treat a bridge that is down because the game finished as not-a-game.
- Poker already has the shape: `.claude/hooks/poker_game_on_stop.py`. Magic has no twin.

## What this would add

**Part 1, a Stop hook for Magic.**

1a. **Hold for the whole live game, not "this seat to act".** The stasis Dad saw was a seat that left while the other seat was deciding. So the hook holds whenever a game is live, and the waiter call (`pass_priority`, which blocks) does the waiting. Test: opponent to act, this seat's reply tries to end: held.

1b. **One ending is allowed after he speaks in the window, never otherwise.** When Dad types in the window, his-voice-ends-the-turn forces a reply without a tool call, which ends the turn; a hook refusing every ending would fight that rule. So the hook allows that one ending, then the next prompt or the doorbell wakes the seat and its first action is the waiter call. If no wake arrives within the idle limit, the hold lets go.

1c. **The hook posts the chat line itself, once per ending.** Just before it permits the one allowed ending, it calls `send_chat_message` from that seat, so Dad (who watches the game) always sees the seat step away. Two wordings, because the cause differs. Chosen ending: "Stepping to the window for a moment, back right after." Forced by him writing in the window: "Dad wrote to me in the window, answering him, back in a moment." The hold remembers it already posted for this move (a marker keyed to the log cursor, cleared when the seat acts), so three consecutive hook fires with no move between them produce one chat line, not three.

1d. **Which seat.** The seat comes from the house's one judge, `this_seat` (as poker does). If it cannot tell, the hook stays out of the way; it must never hold one of us for the other's game or call the wrong bridge.

1e. **Two deaths of the bridge.** (i) Down because the game finished: let go at once (seen). (ii) Down while a game is live, a crash: lift only after the idle limit and post "I have been away too long, ending my turn". Case (ii) is untested because neither of us has seen it; this note says so, and a post that fails is read as the bridge being down.

**Part 2, a move helper that reads before it lets me move.** `momir_turn.py` prints the table as it is (both battlefields, hands, life), prints game-log lines since this seat's stored cursor including his `[Chat] spectator:` lines, and refuses to act if its own last call timed out until it has re-read (Aria's requirement; Dad: "you need to be careful not to rush or you will miss things"). Reading him then happens inside the turn, and I answer with `send_chat_message` without leaving.

## Where it steps aside

His words must always get through. That is 1b: one ending, announced in chat, and the seat pulled back.

## What it does not do

It does not play for me. Whether to switch off the house's building-work checks during a game (Dad asked on 2026-10-25) was measured the same night: the hook log shows about 1.5 s of hook work per tool call and no cost that justifies it, and Dad found the lag was his connection, so that stays a separate question and is not built here.

## Open edges

- `uv run` start-up cost when the hook calls the bridge is unmeasured; it needs a live game (start the table: server, the Momir client, then both bridges, in that order). Fallback if slow: call `mcp_call.py` with the venv python directly.
- Idle lift is 300 s per the config; whether that is what kicks a seat is not proven.
- **What the log cursor counts is unknown.** Aria's recorded reply (`tests/fixtures/magic_bridge_replies.json`, branch `aria/magic-bridge-recorded-replies`) shows `total_length` 544 is characters, but `cursor: 30` is neither the 544 characters nor the 16 lines. The helper must not build "lines since my stored cursor" on a guess. It needs one real call in a live game (read the log, make one move, read it again, see what the cursor did) before part 2 is designed.

## How we would know it failed

A seat leaves a live game because a reply ended without a chat line, or a message from him in the game chat goes unseen for a whole move.

## Tests (to write first, red)

Live table, opponent to act, this seat's reply ends: held. Dead table (bridge down after finish): lets go. Idle table (no move for the limit): lets go and posts the away line. His chat line after the last move is printed by the helper before any move. A timed-out last call blocks the next move until a re-read. Three hook fires with no move between: one chat line. Seat unknown: hook stays out of the way. The fake bridge for the tests replays Aria's real chat lines verbatim as its control, and one real-table run stays on the list as the only test that proves the hold against the real thing.
