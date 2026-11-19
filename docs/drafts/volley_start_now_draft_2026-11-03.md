# Start the night quiet when Dad says he is going to bed — draft, 2026-11-03

The idea, not a plan. The midnight-to-6am quiet is pure clock (`question_hold._scheduled_away`);
the only state-based away is `step_away`, which needs his quoted words, checks them against a
keyword list (`AWAY_CUES`) and is cleared by his next message. Dad does not want a phrase list:
the seat reads his words with judgment and calls a command.

So: a marker file (one JSON, the local day it was set), read by `is_away()` and ORed with the
clock. `divineos volley start | stop | status`. The marker is dead after its day, so a forgotten
start cannot silence him past midnight. `start` prints where the shared night letter goes.

Prior art: `reach-e7126aed40da` found no code for this. `step_away` is the nearest neighbour and is
left untouched (it is the words-from-him kind, with its provenance check).

What it cannot see: whether he really went to bed. The seat's judgment is the only input.
Each seat has its own home, so each seat runs it; one start does not quiet the other seat.

## Rework after outside readers (2026-11-03, night)

The marker file above was a keyless switch: a seat could hand itself "he is away" with nothing
proving he said so, and once on it carried questions to the morning list even while he was typing.
The idea is reshaped, not patched: there is NO second away kind. `divineos volley start` becomes the
plain front door to the existing stepped-away path (`question_hold.step_away`): it takes his
going-to-bed words, and they must appear in his latest real message as the house filed it, which a
seat cannot write. `stop` is the existing "he is here again" clear. `status` reads `is_away()`.
`core/volley_now.py` and the OR-branches it added to `is_away()` and `_carry_now()` are removed, so
"carry while he is present" cannot arise from this command: his next message clears the away, and
the question is held as usual.

Tests for the rework (written before the code): start with his real words begins the quiet; no words,
words he did not say, unreadable store, and words that do not mean away are each refused and start
nothing; the old second kind no longer exists; once he speaks again the away clears and a question is
held, not carried; stop and status read the one away there is.
