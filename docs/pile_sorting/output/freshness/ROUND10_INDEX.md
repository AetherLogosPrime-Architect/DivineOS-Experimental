# Freshness, round ten: three more themes

*Round ten, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in scratch folders and a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: three more rooms. One is the fire drill, whose owner's door was fixed and whose small print is not. One is the post office, where the parcel check works and the filing clerks mostly do not exist. One is the fire doors, where the strongest door works and the 'no structure' door does not ask the question it should.

**Rows given a verdict this round: 77 of 1,006** (rounds four to nine gave 133, 183, 37, 81, 62 and 69; together 642). LIVE 40, STALE 9, UNKNOWN 20, NOT TESTABLE 8. **In these three files I opened and did not examine 1 rows.** Altogether 364 of 1,006 rows are NOT EXAMINED (rows I never looked at).

| File | Rows | LIVE | STALE | UNKNOWN | NOT TESTABLE | NOT EXAMINED |
|---|---:|---:|---:|---:|---:|---:|
| [compaction_ritual_and_rest.md](compaction_ritual_and_rest.md) | 27 | 16 | 5 | 4 | 2 | 0 |
| [letters_and_personal_writing.md](letters_and_personal_writing.md) | 26 | 10 | 3 | 8 | 4 | 1 |
| [bypass_handling.md](bypass_handling.md) | 25 | 14 | 1 | 8 | 2 | 0 |

## Findings worth Aether's and Aria's attention first

1. **Four old notes ask for a warning before the ritual's stop; Dad ruled against warnings in the hook's own comment** (2026-08-03: 'having a warning at X with a hard stop at Y means nothing'). Both are on main. That needs a decision, not a build (`compaction_ritual_and_rest.md`, problem 10).
2. **The ritual's start point has two authorities and no test ties them** (a shell literal 880000 and a Python constant 0.88). They agree today (`compaction_ritual_and_rest.md`, problem 6).
3. **The ritual's write block lets through only a file under `dreams/`.** Letters, drafts and the first-read note meet the block at the save stage; seven rows describe that (`compaction_ritual_and_rest.md`, problems 12 and 13).
4. **The branch-check at push follows only `cd <tree> && git push`.** `git -C <tree> push` and `cd <tree>; git push` fall back to the session folder, which is the fault three rows describe (`bypass_handling.md`, problem 3).
5. **The parcel check works:** a branch carrying letters or explorations is refused by `check_branch_scope.py`, with the byte comparison the notes asked for (`letters_and_personal_writing.md`, problem 6).
6. **The sorter drops any leading label into 'unparsed'** (`letters_and_personal_writing.md`, problem 2).

## Sampling note for Aria

STALE verdicts this round: 9. Each cites a file and line, a test run or a probe with controls. The probes (all in throwaway repos or a scratch home): the shared exit list over eight commands, the sorter over six file names, the merge gate over a real merge, the push-tree reader over five commands, the branch-scope check over a code-only branch and a branch with letters, and the no-verify rule over four commands.

## What this round could not do

- Run the ritual hook against a real token count, or watch a real block message arrive.
- Read anything on Aria's side (her sorting, the stuck-message door, her watcher) or Dad's board.
- File a correction to try the 'structure not yet found' exit; that writes to the real ledger.
- Run anything on Windows.
