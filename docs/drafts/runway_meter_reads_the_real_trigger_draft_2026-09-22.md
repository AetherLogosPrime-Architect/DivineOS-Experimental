# The runway meter reads the real trigger — draft, 2026-09-22

## What is wrong

Andrew moved the compaction ritual's firing point to 880k on 2026-09-18
(`auto_cycle.TRIGGER_THRESHOLD = 0.88`). The move reached the ritual, the
governor, and the context meter. It missed one site:
`cli/context_tokens_commands.py:55`, the heartbeat readout that tells me how
much room is left before the ritual fires. It computes

    fire_at = int(CONTEXT_WINDOW_TOKENS * 0.92)

so it counts down to 920k and overstates the runway by 40,000 tokens. Found by
the five-wing house walk; verified in the main session by grepping every
literal copy of the trigger and by searching all 89 remote branches (86
readable, none carries a fix).

The neighbouring labels disagree with each other and with the code:

- `auto_cycle.py:124` says the trigger "drops from 0.92 to 0.87" — the value
  is 0.88.
- `context_heartbeat.py:9` and `:61` still describe 0.92 / 920,000.
- `extract_marker.py:21` still says the trigger is 0.92.

## Why it matters more than a display bug

Andrew's complaint that started this evening was that the ritual fires too
late and he does not notice until it is too late. The ritual's own number was
already correct on main. The gauge I read to judge the distance was not.

## The shape, and why not just change the literal

This is the same fault as the rest of the night: two numbers that agree by
hand, and a repair that reached some sites and not others. Replacing 0.92 with
0.88 would reproduce it — the next move would miss this site again. The fix is
to make the meter READ `TRIGGER_THRESHOLD`, so there is one number and nothing
to keep in agreement.

## Plan

1. `context_tokens_commands.py`: import `TRIGGER_THRESHOLD` from
   `core.auto_cycle` and compute `fire_at` from it.
2. Correct the three stale labels to describe the constant rather than a
   number, so they cannot go stale again on the next move.
3. Test: assert the meter's fire point equals
   `CONTEXT_WINDOW_TOKENS * TRIGGER_THRESHOLD`, and assert no literal copy of
   a trigger fraction remains in the meter source. Prove the test fails
   against the unfixed line before trusting it passes.
