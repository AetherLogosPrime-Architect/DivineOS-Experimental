# A proof-test: the "did I really do it" gate does not hear "I've fixed / saved / written" (rough draft)

*2026-10-08, round seven. The idea, not a plan.*

A picture: a door guard who checks anyone announcing "I'm filing the report" or "I've committed the change" against the visitors' log, and turns them away if the log is empty. But the guard was only taught six announcements. Someone who says "I've fixed it" or "I've saved it" walks straight in with an empty log.

The gate in question is `operating_loop/shoggoth_gate.py`. It watches for six kinds of done-claim (filing, wiring, closing, committing, building, retracting) and asks whether a matching tool call happened in the same turn. The old notes (psf-e01ebb81, psf-bd74d0ea) ask for the same check on the plain words "I've fixed", "I've saved", "I've written", and say the words twice came a turn before the action. On main, all three sentences with no tool call are allowed, reason "no action-claim words in reply".

The test is `tests/pile_repro/test_action_claims_miss_fixed_saved_written_repro.py`: three controls that pass (a covered claim with no tool call is blocked; the same claim with a Write is allowed; a plain reply is allowed) and three strict expected failures, one per quoted sentence. The gate is untouched.

What it does not show: the gate sees tool names, not whether the write succeeded (its own header says so), so even a fixed vocabulary would not catch a failed write. That is the second half of the first note (bd74d0ea) and is not tested here.

Nothing is closed, merged, deleted or stamped.
