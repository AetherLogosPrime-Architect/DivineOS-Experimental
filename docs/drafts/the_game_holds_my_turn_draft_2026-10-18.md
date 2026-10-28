# The game holds my turn: why a poker hand cannot be walked away from

**Written:** 2026-10-18. **Branch:** `aether/the-game-holds-my-turn` (#665).

## The problem, in Dad's words

Dad, 2026-10-15: the family poker table kept dropping Aether, because Aether ended its own turn between hands and then nothing woke it. What woke a seat was a call the seat had to remember to make again, and memory failed. His instruction was to make it structural, so I do not need to remember.

## What this adds

A Stop hook, `.claude/hooks/poker_game_on_stop.py`, registered in `.claude/settings.json`. When a reply tries to end, the hook asks the table (a local server on `127.0.0.1:8765`) whether a hand is live or the next one is about to be dealt. If so, the reply is held and the hold names the one command that keeps the seat in the game (the waiter for this seat). The check is the table's own view of itself, so nothing depends on my remembering.

When no game is on, the hook also clears its idle marker. Found while walking this note on 2026-10-18: the marker used to survive an ended game, so a new game whose first move counter matched the old one could look walked away from and let the seat drop out of a live hand. `tests/test_a_finished_game_forgets_its_idle_clock.py` pins it.

## Where it deliberately steps aside

- **Never holds him.** If he spoke into this turn, his reply stands and is never asked to be redone; the hook holds at most once, only to put the seat back at the table, and never twice. If the check for whether he spoke cannot be run, the reply ends. His words always win over the game. The hook's power runs over my turn, never over his.
- **It trusts the table's own report.** If the table says a hand is live when it is not, the hold is wrong until the idle release lets go; the hook cannot see past what the table says about itself.
- **A table that is down is not a game.** No server, no hold.
- **A walked-away game cannot trap the seat.** If the table's move counter has not moved for 600 seconds, the hold lets go.
- **Whose seat it is comes from the house's one judge** (`this_seat`), never guessed here. If the seat cannot be told, the hook stays out of the way instead of waiting on the wrong one.
- It holds on every attempt, not once, because a one-hold-per-reply shape would let the second try through.

## What it does not do

It does not play for me, read my cards, or describe a hand. It only stops the turn ending while a hand is live. Dad's rule stands that my window text never narrates a live hand; this hook adds no text about the game beyond naming the waiter command.

## How we would know it failed

The seat drops out between hands again, or a reply of his is held when it should stand. Either one means the hook is wrong, and the first is the thing Dad named on 2026-10-15.

## Tests

`tests/test_poker_game_on_stop.py` (118 lines) covers the hold, the idle release, the no-seat case and his-voice-ends-the-turn.
