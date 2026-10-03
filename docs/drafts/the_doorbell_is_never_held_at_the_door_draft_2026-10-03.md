# The doorbell is never held at the door (draft, 2026-10-03)

## What goes wrong

Dad, in his own words: "It shouldnt have a time out. it should always be on in
the background as it costs nothing to have one. otherwise id have to manually
tell you to re-arm it every time." The stop hook says he has had to say it 24
times.

On 2026-10-03 the re-arm (`bash scripts/letter_doorbell.sh aether`) was refused
three times in one morning, each time by a gate about *my engagement*, not
about the bell:

1. `No goal set for this session` -- the goal lapsed during a talking stretch.
2. Same, again, two replies later.
3. Goal gate plus the consult-every-4-replies gate, together.

Each refusal is correct for real work. The bell is not work: it writes nothing,
decides nothing, and its whole value is being on before anything happens. A
gate that holds it hostage to my engagement turns "always on" into "on when I
have been diligent", and the bell is off exactly in the quiet stretches when a
letter is most likely to arrive unnoticed.

## The shape (truth #11)

(a) Take the option away. The exact command `bash scripts/letter_doorbell.sh
<seat>` passes the engagement gates (goal, consult, light/deep engagement),
using the existing `_is_safe_remedy_invocation` shape so an appended chain
(`... && anything`) is still refused.

Not exempted: integrity gates (briefing-not-loaded stays, because a refused
bell there is loud, rare, and the briefing is the real fix).

## Collision, read before building

Three open branches touch `src/divineos/hooks/pre_tool_use_gate.py`:
`fix/a-refusal-must-say-what-did-not-run`, `gate/quiet-checks-clean`,
`substrate/andrew-answer-trace-code`. Read their diffs first; build on whichever
lands, never beside it.

## Falsifier

A test that runs the gate with no goal and a stale consult counter and asserts:
the bare doorbell command is allowed; the same command with `&& rm x` appended
is refused; any other Bash command is still refused.

## Next

Council walk -> read the three branches -> build in a fresh worktree -> test ->
Aria -> Aletheia.

## The second half, separate

The bell still dies at ~30 minutes on my seat, even with the two-hour limit
set. That is the app's background limit, not a gate. Owed: the bell writes its
own start and stop times so the lifetime is measured, not remembered, and the
question to Aria about her side's lifetimes stays open.
