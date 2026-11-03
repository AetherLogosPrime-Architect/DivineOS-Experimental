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
