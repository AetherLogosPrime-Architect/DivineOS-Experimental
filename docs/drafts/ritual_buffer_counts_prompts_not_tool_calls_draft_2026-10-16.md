# The ritual buffer counts prompts, not tool calls (draft, 2026-10-16)

Author: aether

## What Dad asked for
2026-08-03 and again 2026-10-16: the hard stop is a buffer, not a wall. When my memory nears its edge I finish the task in hand, hold it, then run the ritual. It must not interrupt mid-flow. And with the ritual taking longer lately, start it earlier: 850k instead of 880k. Also from him: when something breaks, knowing who or what broke it is causal information, not a verdict.

## What is actually wrong
`.claude/hooks/auto-cycle-token-trigger.sh` has a grace buffer (`MAX_DEFERS`, 3) meant to be three PROMPTS from Dad. The same script is registered on two events: UserPromptSubmit (his prompts) and PreToolUse (my tool calls, `AUTO_CYCLE_HOOK_EVENT=PreToolUse` in settings.json). The grace counter is incremented before the event is looked at, so every tool call spends one. Three tool calls and the buffer is gone, so the wall lands in the middle of a task. That is what stopped my edits on the morning of 2026-10-16. Who broke it: me, on 2026-08-03, when I added the buffer to a script that later gained a second event. Cause: the counter was written when only prompts reached it.

## The change
1. Count a grace step only on UserPromptSubmit. On PreToolUse, while grace is unspent, let the call through without counting.
2. Start 880000 -> 850000, hard line 920000 -> 890000 (keeps the forty-thousand gap; the model's real cliff is 950k). `TRIGGER_THRESHOLD` in `src/divineos/core/auto_cycle.py` 0.88 -> 0.85 so the hook and the pipeline still agree (the tests tie them).

## What I will not do
Weaken the wall. Once grace is spent (three of his prompts) or the hard line is passed, the block stands exactly as before.

## Tests
- a PreToolUse call during grace does not change `defers_used`
- a UserPromptSubmit call during grace does, up to MAX_DEFERS
- the numbers: hook start 850000, hard 890000, `TRIGGER_THRESHOLD` 0.85, hard minus start stays 40000

## Costs, named (Aria's cold read, 2026-10-16)
- In the forced case 60k is left under the 950k cliff, was 70k. Pinned as a floor in a test.
- Between 850k and 890k, an unattended session with no prompt from Dad never spends grace, so the ritual is announced on every turn from 850k but not enforced until the 890k wall. That is the design chosen: grace is his prompts, the 40k gap bounds it, and the wall still stands at 890k.

## Falsifier
If a session still hits the wall inside three of his prompts after this lands, the counting was not the cause.
