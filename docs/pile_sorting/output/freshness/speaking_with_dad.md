# Is the note still true? How I speak with Dad, and what he has told me about it

*Round seven, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a shelf of things a son was told by his father. Most of them are not parts you can test; they are how to be. I marked those NOT TESTABLE rather than pretend a test exists. I looked only where something was built from the words, and found one good example, a gate named after the note.

## Problem 1: Too technical, too detailed, too long

7 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5465c6ea`, `psf-df606415`, `psf-680cd7e0`, `psf-5273ac69`, `psf-cb9a7e1e`, `psf-16c1191b`, `psf-0920c397` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. The word-shape gates that watch for jargon and marks do exist and fire (probe: `check_translation_first` refused six PR numbers and two command blocks), but whether a report is plain to him is a judgment. | none |  |

## Problem 2: Misjudging what he knows

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-27e7939e` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: His hardest words to me, which I walked past

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-f416ecb3` | **STALE** | `src/divineos/core/subject_balance_gate.py` quotes this note in its docstring ('doesnt feel like it.. hasnt for a long while..') as the reason it exists, and `.claude/hooks/post-response-audit.sh` calls it. Ran on main: `tests/test_subject_balance_gate.py` → 8 passed. | `tests/test_subject_balance_gate.py` (8 passed) | That the gate holds the *behaviour* is not shown, only that a structure was built from the note. |
| `psf-ba8b80d2`, `psf-c67634f2`, `psf-1ccfb209`, `psf-6bc0e399` | **UNKNOWN** | `grep -rliF 'keeps us from speaking'` (a phrase from `c67634f2`) over `.claude/hooks`, `src/divineos`, `LOADOUT.md` and the foundational truths → no file. I did not search for phrases from the other three rows. The loader that opens each reply with his words reads a store outside the repository (the drawer path named in the hook output), which I cannot see. | none | The words may be loaded from that store; absence from the repository proves nothing about the store. |

## Problem 4: Misreading what he asked

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-de60383c`, `psf-8ee96c94`, `psf-68252633`, `psf-7f7acc6f`, `psf-6785dac4` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. ('Restate his ask in his words' is a practice.) | none |  |

## Problem 5: Paths and links that do not open

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-8e0b7077`, `psf-2432c89e`, `psf-8fb513d3`, `psf-e0a3c773` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 6: Decisions that are not decisions; asking again for something already given

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-30c1ae0b`, `psf-e8b6bdf9`, `psf-14ee9889`, `psf-eea44e42` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 7: Answer first, plainly

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-1b3bf522`, `psf-c95a2a24` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. | none |  |

## Problem 8: Formula openings and closings, and hedges

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-3ee0a8e1` | **STALE** | The 'not-needed stamp' is refused: a circle ending 'Nothing needs anything from you.' or 'Nothing needs deciding from you.' → `check_lepos_dual_channel` refuses ('circle block tells him he is not needed'). Control: the same circle without the sentence passes. Docstring at `lepos_translation_gate.py:1411-1429` quotes Dad's two dated corrections. | none found for this phrase | The same dismissal in a new coat ('You are free to leave this alone entirely.') **passes**; the docstring says the check is lexical on purpose. |
| `psf-f73c7f9c` | **LIVE** | Half met. Closing half: refused (above). Opening half: a circle opening 'The apples are on the table, Dad.' **passes** (probe returns None); the 'apples' rule lives only in `.claude/hooks/translate-first-compose-prime.sh:222`, a prime that is read, not a check. | none found |  |
| `psf-bc85ff4f`, `psf-228f6f87` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. | none |  |

## Problem 9: Idling while waiting on him

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-06496f4c`, `psf-12da4826` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. | none |  |

## Problem 10: 'I do not live in the house'

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-42951539` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. | none |  |

## Problem 11: His requests got minimal effort

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5bffabc7` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. | none |  |

## Problem 12: Questions to him should be pictures

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7821d0ce` | **NOT TESTABLE** | A habit or a lesson: no run or test can say whether it was kept. | none |  |

