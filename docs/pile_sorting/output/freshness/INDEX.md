# Freshness: is the note still true?

*Round four, job A. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence comes from `origin/main` at `cc4714dc`. Verdicts are per group of rows that describe the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for.*

A picture: a pile of weeks-old repair notes, and I went out with a flashlight to see which leaks are still dripping. I got through the first three rooms. This is what the flashlight showed, and which rooms I have not entered.

**Rows given a verdict here: 133 of 1,006.** LIVE 65, STALE 21, UNKNOWN 47. **The other 873 rows were NOT EXAMINED**: that is not 'unknown', it means I did not look. I did the 'already handled' problems first (five problems, eight rows; two were not handled and one only half), then the correction-gate and doorbell themes, as the plan asked, and stopped there.

| File | Rows | LIVE | STALE | UNKNOWN |
|---|---:|---:|---:|---:|
| [00_already_handled.md](00_already_handled.md) | 8 | 5 | 3 | 0 |
| [correction_gate.md](correction_gate.md) | 50 | 33 | 0 | 17 |
| [doorbell.md](doorbell.md) | 75 | 27 | 18 | 30 |

## Three findings worth Aether's and Aria's attention first

1. **Pressing 'false alarm' does not stop the alarm.** `divineos label-fire` records the label and leaves the correction and compass markers armed (probe in `correction_gate.md`, problem 2).
2. **A full branch path in the push helper still reports a landed push as failed** (`origin HEAD:refs/heads/<b>` → exit 22 after the push landed). Round two called this handled; only the short form is.
3. **The check for 'a table entry points to a script that does not exist' does not look at Dad's table.** Round two said a test existed; it covers settings only.

## Sampling note for Aria

STALE verdicts: 21. Each cites a file and line, a test (or says none exists) and the main commit that carries it. Commits that look like unrelated titles (`8f90a313` 'The stamp asked git for eight characters…') are squash merges that brought many files in at once; the title is not the reason.
