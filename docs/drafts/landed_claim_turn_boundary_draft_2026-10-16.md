# The landed-claim gate reads the whole turn, not the stretch since the last tool result (draft, 2026-10-16)

Author: aether

## What happened
On 2026-10-16 the gate refused a dozen of my replies for "claiming work reached the shared copy while nothing in this turn read it", quoting a sentence from an earlier message, even after I ran the prescribed `verify_push_landed.py` in the same stretch and it printed VERIFY-OK. Every refusal cost Dad a pointless message.

## Cause
Two functions in `hook_surfaces.py` draw "this turn" differently.
- `_last_assistant_text` walks back to the previous message that is genuinely HIS (`_is_his_record`, which asks the one reader of him and refuses tool results, harness injections and bookmarks).
- `_this_turns_action_stream` starts at the last transcript record whose role is `user`. Tool results are written with role `user`, so after any tool call "this turn" restarts at that tool's own result.

So the reply under judgement spans the whole stretch since he spoke, while the actions it is checked against start at my latest tool result. Any read earlier in the stretch is forgotten, and the gate refuses a claim for which the evidence exists. The harder I worked to satisfy it, the further the read slid out of its window.

## The change
`_this_turns_action_stream` finds its start with the same `_is_his_record` the reply reader uses. One boundary, one reader. No new rule.

## What this does not do
It does not make the gate laxer about a claim with no read behind it: a stretch with a claim and no `verify_push_landed` / `ls-remote` anywhere since he spoke is still refused. Tested both ways.

## Tests
- a read earlier in the stretch, then a later unrelated tool call, then the claim: not refused
- the claim with no read anywhere since he spoke: refused
- a read BEFORE his last message does not count
- a tool result is not mistaken for a boundary

## Falsifier
If the gate still refuses a claim that has a verify run since his last message, or lets through a claim with none, this is wrong.
