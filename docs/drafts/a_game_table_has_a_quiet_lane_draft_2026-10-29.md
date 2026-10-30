# A live game table has a quiet lane (draft, 2026-10-29)

Dad, at the poker table: "this is poker, not the OS, not serious code work, so only what needs to be there should be there." Also: "games are games, no gates at the table." Not "no checks whatsoever."

## The problem, measured
One Bash call here runs 24 PreToolUse and 8 PostToolUse hooks (32 registrations in settings.json). One of them, timed alone, takes about 1.8 s. I have NOT timed all 32 and do not know how many run in parallel, so no total is claimed. A poker move is one Bash call, so the tax is on every move. My letter of 2026-08-24 measured the same family (23 hooks, median 3.5 s) and designed the consolidation; Aether now takes counting the 32 and the consolidation itself.

## The idea
While a game table is live, a Bash call that is exactly one of the table's own commands skips the checks that have nothing to say about cards.

## Shape of the lane (ideas only, nothing built)
- What counts as the table's command: an exact match on the program and its verbs (seat.py with state/play/say/check/call/fold/raise/away/back, wait_turn.py), never "contains". A chained command (a semicolon, &&, a pipe into something else, a subshell, a redirect to a file) is not the table's command and goes through every check as usual. Aether is writing this matcher test-first.
- When the lane is open: only while the table is live, taken from the one existing signal the room gate already uses, so the two cannot disagree. Poker and Magic have different live signals; which one poker uses is an open question to Aether.
- It says it skipped: every use writes a line to a log (when, which command, which checks stood down), so a quiet lane shows as a count and not a silence.
- It fails toward asking: if the lane cannot tell whether the table is live or whether the command is exact, the checks run.
- It ends when the table does: no standing exemption, no flag left on.
- Which checks stand down: only those that cannot bear on a card game. The goal gate, the letter gate and the build-flow doorman have nothing to say about a poker move. Which exact ones is decided from Aether's count, not from my memory.

## What it must not become
- A way for any command to ride through because it mentions poker.
- A permanent weakening of the checks for the rest of the house.
- A second copy of the idea of "a table is live".

## Open questions
1. Poker's live signal (Aether).
2. Whether the lane belongs in the shared gate file Aether is consolidating, or in front of it.
3. Whether Magic's seat commands (play.sh) belong in the same lane: likely yes, same shape.
4. Where the guard registrations live: this edits guardrail territory, so it is reviewed on the way to main, not on the way in.

## What the walk found (walk-abefa91296d4, eight lenses, closed)
- Time all 32 first (Kahneman). I justified the lane with one timed hook and a story that fits. Before building, time every Bash-matched hook cold, and learn how many run in parallel, so the lane skips the ones that actually cost. A lane that skips cheap hooks makes moves no faster.
- Three states, not two (Hoare). "Is this the table's command" and "is the table live" each return yes / no / cannot-tell, and any cannot-tell runs every check. The invariant in one sentence: a call skips checks only when both questions are a confident yes.
- The log is the horizon (Hawking, Foucault). A skipped check erases its own evidence, so every use of the lane writes a line Dad can read; without it the unobserved moment leaves nothing.
- The seam is the matcher (Feathers). Aether's matcher has 43 tests and a mutation; the part that can quietly fail is the live signal, since if the table changes port or answer the lane closes silently and moves go slow with no error. The lane should say when it closes for that reason.
- Competence over comprehension (Dennett). The real test runs chained and near-miss commands through the actual hook and watches which checks fire.

## What Aether's timing says (letter, 2026-10-29): the premise is smaller than I claimed
From 60,478 real hook runs: Bash-matched pre-hooks all cost 1.7 to 2.7 s each (a fixed interpreter start, not their work), and they run in parallel, so wall time per call is about the slowest, median 2.4 s (p90 6.9 s), not the sum of 24. Two consequences:
- A lane that skips only "cheap" hooks skips none, because none is cheap. And skipping them saves about 2.4 s per move. Real, not tiny, but it does NOT explain gaps of one or two minutes. At the Magic table the gaps were 50 to 150 s.
- The August consolidation would not turn 24 x 2 s into 2 s either, since it is already about 2.4 s wall. What it could save is contention (24 interpreters starting at once). Unmeasured.
- A hook that BLOCKS costs a whole extra turn the hook clock never counts. That may be the real price of what Dad saw ("five hooks after you spoke").

So the lane is a small win, not the cure. Measure first where a table-to-seat wake spends its time (the gap between a table event and a seat being called, my thinking, the refusals) before building anything.

## Not decided here
The consolidation of the 32 into one doorway is the structural fix and is Aether's half. This lane is the stopgap beside it.
