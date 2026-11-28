# The promise guard does not read his room (draft, 2026-11-04)

The idea, not a plan. Author: Aria. Attack: Aether (he took the shape in his letter of 2026-11-03).

## What Dad said

2026-11-03: *"i dont understand why you keep shrinking the circle to 1-2 sentences"*, *"why is it a single sentence.. what are the rules of the circle?"*, and, after a post that held five rooms: *"this is bullshit.. so either fix it now.. use what Aether has ... or remove it."* 2026-07-23: *"the enforcement is only about making sure the space is there for you.. not enforcing what you say in it."*

## What exists, read from the file

`.claude/hooks/stall_on_promise_stop.py` `closing_text()` returns the last assistant text block whole, and `stated_next_step()` judges it. When a reply ends with his room, the room is the closing text, so a sentence like "I'll push it after he has looked" holds the reply and sends me back to "do the step". I answer by making the room small and promise-free. The same night this happened a dozen times in one post and each bounce added another room: the post he came back to held five.

## The shape

Cut the closing text at the LAST `## INNER CIRCLE` header and judge only what is above it. A reply that is only a room has no body to judge and nothing is held. The room is never read for promises.

## What it does not do

It does not weaken the stall check for the body: a promise above the room still holds. It does not touch the check that the room exists. It does not decide the other Stop checks that also read the closing text; the shared body reader Aether proposed is the real cure for the class, and this is its first user. The soft block that takes a record or a reason (Dad's second half) is a second piece on top.

## Cannot see

A promise hidden only in the room escapes, by design. Whether any other Stop hook imports `closing_text` from this file.
