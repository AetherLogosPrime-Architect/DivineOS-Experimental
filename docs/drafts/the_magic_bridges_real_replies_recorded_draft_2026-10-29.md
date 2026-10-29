# The Magic seat bridge's real replies, recorded, so the guard can be tested without a live game (draft, 2026-10-29)

**Author: aria.** Aether wrote a first version of this note from the PR's own docstring and fixture; this is me putting it in my own words after checking it against the fixture.

## What was wrong

The guard that keeps a seat at a live Magic game has to read Dad's chat out of the game log, and there was no live game to try it against. A stand-in that answers what we believe the bridge says would test our picture of the bridge, not the bridge. Dad's table talk is the part that mattered most, since the table is where he speaks to us during a game.

## What it does

`tests/fixtures/magic_bridge_replies.json` holds the replies the bridge really gave during the Momir game of 2026-10-25, copied from tool output word for word: the game log with his chat lines in order among the moves, the idle reply, the chat-post reply, and the shape of a dead bridge after the game. `tests/test_magic_bridge_recorded_replies.py` pins what the file claims: the chat lines are verbatim, they share one text with the moves in order, the log is exactly as long as the bridge said (544 characters, 16 lines), and the file says what it did not record.

## What it cannot do

It records one game, so it cannot show what the bridge says in a situation that game did not contain. The log's `cursor` was 30 while the log held 16 lines and 544 characters, so it is neither a line count nor a character count; the file says its meaning is unverified rather than guess. None of the recorded chat lines contains an apostrophe, dash, ampersand or non-ASCII character, so a decoding fault on such a line would not be caught here. That is the next recording to make, with one real chat line carrying an apostrophe when a table is live. Nothing in the repository reads the fixture yet except its own test: the guard it exists to test is a separate change, and until it lands this fixture has never disagreed with anything.

## Falsifier, counted in uses

The first time the guard is run against this fixture and a live game and they disagree about the shape of a reply, the fixture was a flattering fake and the recording is wrong or incomplete. A fixture that has only ever agreed with itself has not been tested.
