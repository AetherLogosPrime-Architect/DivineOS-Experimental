# The stall hold moves into the router (draft, 2026-11-04)

**The idea.** Dad, 2026-11-04, afternoon: hooks are the issue that affects him most, "popping up one
after the other". Measured the same day: the live settings register 24 Stop hooks and exactly one,
`doorbell-stop.sh`, is the router that `hook_order` can order. The other 23 are separate processes,
each with its own message and its own copy of the retry rule. After one reply I was handed up to five
separate refusals (buried question, the room, the stall hold, the reflection hold, the bell). The
`hook_order` table orders only what is inside the router, so it cannot touch them.

**What this adds.** The first of those standalone holds, `stall_on_promise_stop` (94 lines, a thin
door over `core/stall_on_promise`), moves into the router as a Stop surface. The thinking moves into
one core function, `core/stall_hold.verdict`, which the router surface and the old script both call, so
there is one copy of the logic and a test can argue with it. The surface keeps every behaviour of the
script: one hold per reply (`stop_hook_active` stands down), stand down when he spoke into this turn,
and a transcript that cannot be read is could-not-run, never a pass. It gets a row in `hook_order`
(Stop, tool call) so it speaks through the table. The standalone registration comes out of
`settings.json` in the SAME change that registers the surface: a migration that leaves the original
registered has moved code and retired nothing (the 2026-09-08 router note says exactly this).

**What it cannot do.** It folds in one hold of 23. The room, buried-question, reflection and bell
holds, and the poker hold, move in after, one at a time, each with its own test. The two protocols
differ (the scripts block with a JSON decision, the router with exit 2 and stderr); I check that on
this first move before moving a second.

**Falsifier.** The surface and the old script disagree on a transcript; or both are registered and fire
twice; or a hold that used to stand down when he spoke stops standing down.

**Owed.** A walk, Aria's read, Aletheia's confirm, Dad's yes. Stacked on the order-table branch.
