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

1e. **Two deaths of the bridge.** (i) Down because the game finished: let go at once (seen). (ii) Down while a game is live, a crash: **the hook cannot tell this from (i)**, since both answer nothing, so it lets go at once, as the code does (found by the Hoare lens in the 2026-10-25 walk: this note used to say the crash case waits for the idle limit, which the code never did). A crash mid-game therefore drops the hold, which is the safe direction for his words and the unsafe one for the seat; the only protection is that a crash is not something either of us has seen. A post that fails is read as the bridge being down. The idle-limit away line is posted only when the bridge still answers and nothing has moved.

**Part 2, a move helper that reads before it lets me move.** `momir_turn.py` prints the table as it is (both battlefields, hands, life), prints game-log lines since this seat's stored cursor including his `[Chat] spectator:` lines, and refuses to act if its own last call timed out until it has re-read (Aria's requirement; Dad: "you need to be careful not to rush or you will miss things"). Reading him then happens inside the turn, and I answer with `send_chat_message` without leaving.

**Part 2b, a waiter that wakes on him (Dad's ask, Aria's shape; replaces "prints chat at the start of a move").** Dad, 2026-10-25: the seat should stay awake through the whole game and observe from its end until its turn, so a line he types in the game chat is always seen and answered, whether or not it is my turn. Today `pass_priority` blocks until a decision is due, and while it blocks nothing reads chat, so a line typed during the opponent's turn waits for my next move. The waiter polls the seat bridge every second or two and returns on whichever comes first: my decision pending (`get_action_choices`), or new text from him (`get_game_log`). On chat it returns the line with the table printed, I answer with `send_chat_message` and call the waiter again, all in one turn. New text is found by length, not by the unknown cursor: `total_length` is a character count (the recorded log is 544 characters and the bridge said 544), so anything past the last stored length is new; if the length ever goes DOWN or `truncated` turns true, the helper re-reads from the start instead of trusting the offset. Every return prints the table, so speed cannot make me skip reading. Not verified, each needing one real game: whether `get_game_log` can be called while `pass_priority` blocks the same seat, whether polling every second or two upsets the bridge, and whether `truncated` ever turns true. The hold's waiter command then becomes this waiter instead of `pass_priority`; the guard built so far names `pass_priority` and changes in the next slice.

**Part 2c, a recorder (Dad, 2026-10-25: "neither of you remembered the last time we played... there should either be something to help record the games or afterwards you write something about it").** The waiter already reads the game log on every wake, so it also appends the new text to a per-game file as it goes, and when the table closes it leaves the finished file where the memory link reads, so the next game finds it. What I write afterwards in my own words is mine and cannot be automated.

**Part 3, a reminder after the game (Dad, 2026-10-25: "make sure after the game is done you are reminded to record the events of the game and put it in a game nights folder and magic subfolder").** The record lives in `family/game_nights/magic/` (Aria made the folder in her tree with a README). The recorder in 2c rides on the unbuilt waiter, so the reminder does not wait for it: the guard already sees a game go from live to not live, and when that happens it holds the reply ONCE with a line naming the folder and what goes in the file, then lets go. Built in the guard (`after_game`, pinned by tests). It says "stopped", never "finished", because a crash looks the same from here; it does not fire when no game was live, when the idle lift already fired, or when the live mark is older than six hours. The honest holes: if the marker file was never written because the guard never saw the game live (a game that began and ended between two replies), no reminder fires; the recorder is the answer to that and is unbuilt. And a game that runs longer than six hours (an overnight game where a seat idles) loses its live mark and would not fire the reminder when it ends (Aria). The signature now also carries `game_seq`, a move counter seen in a real `get_game_state` reply (Aria), and keeps an empty `priority_player` as a value, not as missing. The record folder is shared, `family/game_nights/magic/`, and Aria sends it to main as a small PR; until then the hold may create it on demand and nobody makes a competing copy.

**Corrections from Aria's real calls, folded in the same night.** `pass_priority` is a MOVE whenever a decision is due, so it is never the waiter: the safe waiter polls `get_action_choices`, which only reads (the guard's hold text now says so, pinned by a test). The chat post is built as a JSON argument list, not a shell string, so a line with an apostrophe cannot end a quote early (pinned by a test).

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
