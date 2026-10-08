# Freshness, round seven: three more themes

*Round seven, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: three more rooms. Two of them hold notes that can be tested, one holds notes that are mostly how a son should speak to his father, and no test can check that.

**Rows given a verdict this round: 81 of 1,006** (rounds four, five and six gave 133, 183 and 37; together 434). LIVE 15, STALE 20, UNKNOWN 23, NOT TESTABLE 23. **In these three files I opened and did not examine 32 rows.** Altogether 572 of 1,006 rows are NOT EXAMINED (rows I never looked at).

| File | Rows | LIVE | STALE | UNKNOWN | NOT TESTABLE | NOT EXAMINED |
|---|---:|---:|---:|---:|---:|---:|
| [reply_shape_gates.md](reply_shape_gates.md) | 40 | 12 | 5 | 10 | 0 | 13 |
| [speaking_with_dad.md](speaking_with_dad.md) | 37 | 1 | 2 | 4 | 21 | 9 |
| [question_hold.md](question_hold.md) | 36 | 2 | 13 | 9 | 2 | 10 |

## Findings worth Aether's and Aria's attention first

1. **The wallclock guard still refuses 'when I come back'**, the phrase Dad said is fine (`reply_shape_gates.md`, problem 3). It does catch the two real fabrications in the notes.
2. **The translate-first check refuses the pull-request numbers Dad explicitly asked for**, with the same refusal whether or not his message asked for them (problem 2).
3. **The question hold already releases on his next message, and it is keyed to the seat, not the window** (`question_hold.md`, problems 1 and 2): thirty tests pass; what is missing is a per-session key.
4. **Nothing rewrites a closing question into a wish** (problem 8); the rule is in the notes only.

## Sampling note for Aria

STALE verdicts this round: 20. Each cites a function or file and, where a test exists, the run. The `question_hold` rows rest on 30 passing tests and a read of the module; the `reply_shape` rows rest on calling the check functions directly, not on the Stop hook that calls them.

## What this round could not do

- Run the Stop hooks end to end, or the room gate on a reads-only reply.
- See the drawer store that loads Dad's words at the start of a reply (it sits outside the repository).
- Examine most of the echo-door rows; I could not find which module is 'the echo door' by name.
- Run anything on Windows.
