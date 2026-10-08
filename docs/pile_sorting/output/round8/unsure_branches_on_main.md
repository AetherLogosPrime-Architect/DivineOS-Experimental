# The seven "unsure" branches: is their content already on main in some other form?

*Round eight, errand five. 2026-10-08, cloud helper. Read-only: I fetched the branches and compared them to `origin/main` at `cbd35baf` (a scratch copy of its files). Nothing was changed, and **I do not recommend deleting anything**; this note only says what is and is not on main.*

**A picture.** Round four marked seven branches "unsure" because a branch whose work was squash-merged looks unmerged even though its content is on main. So I asked of each branch: if I take every substantial line the branch added, how many are somewhere on main? A branch whose lines are all there was merged by another road. A branch whose lines are missing carries work that main does not have.

## How I measured it

For each branch I took its changes since the point it left main, kept every added line of 30 or more characters (so blank lines and braces do not count), and checked whether the same stripped line occurs in any text file in main's tree (428,760 distinct long lines). I also compared whole files, and I searched main for the names the branch introduces. One end is a real control: my own proposal branch, which I know is not on main, scores 0%. The other end (99%) is a result, not a control; I did not know beforehand that branch had been merged by other roads. The counting script is saved beside this note as `unsure_branches_script.txt` so someone else can repeat it.

## The table

| Branch | Commits not on main | Long added lines found on main | Is its content on main in some other form? | Evidence |
|---|---:|---:|---|---|
| `aria/first-line-to-him` | 18 | **3,005 of 3,016 (99%)** | **Yes.** | 39 of the 52 files it touched are identical to main now; the 13 that differ are files main has since changed. The lowest overlap is `docs/AUTOMATION_REGISTER.md` (62%, a generated file); test and hook files are 97-100%. The branch's work reached main by other pull requests. |
| `aria/a-note-name-windows-can-hold` | 1 | 1 of 29 (3%) | **No.** | `src/divineos/core/must_read.py:179` on main still builds the file name as `f"{key}-{digest}.md"` with no cleaning; the branch's change replaces `:` and the other characters Windows cannot hold. Its draft file is not on main. |
| `aria/silence-rings-too` | 2 | 0 of 6 (0%) | **No.** | The branch adds a "quiet for 90 minutes, then wake me" rule to `scripts/letter_doorbell.sh`. On main that script has 0 matches for `QUIET` or `DOORBELL_QUIET_MIN`. Control: it has 1 match for `DOORBELL EXPIRED`, so the search reaches the file. |
| `aria/the-home-map` | 1 | 2 of 112 (1%) | **No.** | `scripts/home_map.py`, `tests/test_home_map.py` and its draft are absent from main. The places main mentions a "home map" are unrelated uses of the phrase (for example `sibling_audit_rounds.py`'s "that module's home map"). |
| `aria/the-table-and-the-glance` | 8 | 60 of 717 (8%) | **Mostly not.** | 11 of its 21 files are absent from main (including `src/divineos/core/state_glance.py`, `tests/test_state_glance.py`, `scripts/table_tally_report.py`); `state_glance` has no match anywhere on main. 10 files exist on main but with different content (for example `dads_table.py`, `he-is-in-the-room.sh`). |
| `aria/substrate` | 1,858 | 6,740 of 52,024 (12%) | **Mostly not; some parts yes.** | By folder: `.claude` 64% on main, `scripts` 72%, `src` 17%, `tests` 7%, `docs` 6%, `family` 11% of 46,276 lines, `dreams` 0% of 1,351, `exploration` 0% of 238. The branch touched 1,726 files: 277 exist on main with different content, 897 are absent from main, 552 it deleted. Most of what is only on this branch is personal writing (family letters, dreams, exploration). The newest commit is an auto-commit of 2026-09-21. |
| `cloud/pile-sorting-2026-10-08` | 15 | 0 of 5,434 (0%) | **No, by design.** | This is my own proposal branch (rounds one to eight): all 90 files it touched are absent from main. It is not meant to be on main until you say so. |

## What this does and does not show

- **"Found on main" is line matching, not meaning.** A branch whose lines are all on main may still differ in order or behaviour; I did not read the 13 differing files of `first-line-to-him` side by side. The 99% is strong evidence of a merge by another road, not proof.
- **"Not on main" means these lines do not appear in main's files.** The content could live on another branch, in another folder of the machine, or in Aria's own store; I only looked at main.
- **`aria/substrate` is a mixture.** Its code folders are largely on main (the hooks and scripts at 64-72%); its personal writing is not. I cannot tell from here whether those writings are kept elsewhere.
- I did not compare the 552 files `aria/substrate` deleted, and I did not inspect the diff of `aria/silence-rings-too` beyond the rule quoted above.
- Nothing was run on Windows; the Windows file-name branch was read, not run on Windows.
