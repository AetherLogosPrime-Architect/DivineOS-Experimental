# Is the note still true? The council walk I have to file before editing

*Round five, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `d310aadc` (a copy in a scratch folder); live probes ran in a scratch home. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for. Where a standing test exists it is named; the reproductions cited as 'PR #601' and 'PR #602' were re-run against current main.*

A picture: a toll booth where you must stop and fill in a form for every car, even a bicycle and even someone just reading the map at the roadside. The house has since added a way to list several cars on one form, but it clears each car once, and the booth still stops the bicycles. The fixes the notes ask for are mostly still missing; a few belong to things that no longer exist.

## Problem 1: One walk should cover the whole piece of work, not one per file or per edit

21 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-6cff0d49` | **UNKNOWN** | Behavioural: the scope option the row says was built exists (see the next rows) and was not used. | none |  |
| `psf-31f4ea6b` | **LIVE** | `council log --scope` (`src/divineos/cli/council_required_commands.py:180`) lists other edit fingerprints one walk covers; its help says 'each named edit is cleared once' and 'names are exact; there is no prefix or directory form'. A record is consumed on the first matching edit (`council_required/types.py` header) and is valid for `COUNCIL_RECENCY_MINUTES = 60` (`types.py:28`). So a folder or a moved file's old path cannot be named. | none | I did not move a file under a walk. |
| `psf-acc25677`, `psf-349ffceb` | **LIVE** | Reproduction re-run on current main: `tests/pile_repro/test_council_walk_gate_repro.py::test_the_same_file_in_another_working_copy_gets_the_same_fingerprint` (PR #601) **fails when forced** (`--runxfail`): `fingerprint_for('Edit', (<abs path in a second git repo>,), '')` ≠ the repository-relative form. Control passes: a path inside this checkout is already relative. | PR #601 (draft) | The fingerprint strips only the root found from the code's own location or `DIVINEOS_REPO_ROOT`. |
| `psf-b20acb87`, `psf-738abdcf` | **LIVE** | `divineos council --help` lists `authorize-bypass, check, emergency-skip, log, recent, show, walk`; `game-walk` is a separate group whose `file` needs its own `--edit`. No command files the walk and the game-walk together. This session's commits each needed `council walk` ×3, `council log`, and `game-walk file`. | none |  |
| `psf-a1cea09e`, `psf-2d0c77c0`, `psf-acef7af6`, `psf-cfec4447`, `psf-0d7894eb`, `psf-d8f61104`, `psf-869be762`, `psf-036482c6`, `psf-92f252d0` | **LIVE** | `council log --scope` (`src/divineos/cli/council_required_commands.py:180`) lists other edit fingerprints one walk covers; its help says 'each named edit is cleared once' and 'names are exact; there is no prefix or directory form'. A record is consumed on the first matching edit (`council_required/types.py` header) and is valid for `COUNCIL_RECENCY_MINUTES = 60` (`types.py:28`). So a second edit to the same file, or a follow-up on the same lines, needs a new record unless it was named up front. | none | `d8f61104` also asks the house to run the formatter before the check; not examined. |
| `psf-887b6b59`, `psf-f2d748f2`, `psf-2a574c65`, `psf-8dd990f8`, `psf-fcb3b96f` | **LIVE** | **Partly met.** `council log --scope` (`src/divineos/cli/council_required_commands.py:180`) lists other edit fingerprints one walk covers; its help says 'each named edit is cleared once' and 'names are exact; there is no prefix or directory form'. A record is consumed on the first matching edit (`council_required/types.py` header) and is valid for `COUNCIL_RECENCY_MINUTES = 60` (`types.py:28`). One walk can cover several named files, but each must be listed and each is cleared once, so the count of files still matters. | none |  |
| `psf-738b0823` | **UNKNOWN** | Asks to land a specific unmerged commit (`7414994cc`); not checked. | none |  |

## Problem 2: Filing a walk takes many steps in a fragile order; build one helper

15 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-6b65bdc8`, `psf-10ff1f65`, `psf-fa9019b3`, `psf-299fc282`, `psf-1cd32b47`, `psf-3f07aec1`, `psf-67c06323` | **LIVE** | No single helper: `divineos council --help` and `divineos walk --help` list no command that reads the gate's fingerprint, loads the lenses and files the walk, log and game-walk. (`scripts/check_council_walk_for_new_infra.py` is a commit-message check, a different thing.) Control: `grep -rn 'walk-for\|walk_for'` finds only that script. | none |  |
| `psf-83c1e3f8`, `psf-897dc1a3` | **LIVE** | `divineos council log --help`: `--edit TEXT ... [required]`. Nothing derives it from the file being edited. | none | `897dc1a3`'s second clause (a test switch) not examined. |
| `psf-4740d006` | **LIVE** | Probe on current main in a scratch home, with a reflection long enough to pass the token floor: `divineos council walk --edit edit:src/a.py --lens Penrose --problem ...` → `REJECTED: penrose's methodology was not loaded in this window`. Same refusal seen three times in this session (Dillahunty, Penrose, Beer) until `mansion council --show <lens>` was run. | none |  |
| `psf-71c8facf` | **LIVE** | No command re-walks a single lens from a data file (command lists above). | none |  |
| `psf-fe17c5de`, `psf-781743ed` | **LIVE** | `walk open --scope` is `multiple=True` (`src/divineos/cli/council_walk_commands.py:52`): repeating the flag works. A comma list is **not** split — `core/council_walk.py` stores `"\n".join(scope)`, so `src/a.py,src/b.py` is one entry. `council log --scope` does take a comma list. `781743ed`'s second half (stamp-ready naming the workspace and owner file) not examined. | none |  |
| `psf-31d1d8dc`, `psf-4c192096` | **LIVE** | `.claude/hooks/check-council-required.sh` prints the fingerprint (`edit: bash:git add`) but nothing says a command is named by its first word pair: `grep -n 'first word\|first command\|named by'` on that script → no match (control: `grep -n fingerprint` → lines 15, 201, 464-507). | none |  |

## Problem 3: Reading and filing commands should not owe a walk

15 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a8cea834`, `psf-2b544912`, `psf-c717c6e4`, `psf-b1f8d754`, `psf-624616e3`, `psf-4bb053f7`, `psf-021be55d`, `psf-7ce1ee55`, `psf-d36076f1` | **LIVE** | PR #601 reproductions re-run on current main, **forced**: all 12 read-only look-ups (`audit list|show|summary`, `prereg list|show|overdue|summary`, `compass-ops history|summary|spectrums`, `journal list|search`) still owe a walk in `score_substrate_modification`, and `audit list`, `audit show`, `prereg show` are blocked by the real gate with an empty ledger. Controls pass: `divineos council show abc`, `divineos --version`, `ls tests` are free; `divineos prereg file x --claim y` still owes one. | PR #601 (draft): 19 expected failures, 4 controls | The classifier's verdict is tested; a repair one layer up would leave the classifier test failing while fixing the problem. |
| `psf-90bcbe70`, `psf-484c94cd`, `psf-cbc0d7e7` | **LIVE** | Review-round commands are not exempt: control `test_control_a_write_still_owes_a_walk` (PR #601) passes on main with `divineos audit submit-round x` → walk required; `audit submit-round --help` also fails the help reproduction. | PR #601 (draft) |  |
| `psf-d5aa48d4`, `psf-52209a28` | **LIVE** | `divineos --version` is already free (control) but `divineos prereg --help`, `audit --help` and `audit submit-round --help` still owe a walk (3 forced failures, PR #601). | PR #601 (draft) | Half of `d5aa48d4`'s ask (`--version`) is met. |
| `psf-4e4e3ad2` | **LIVE** | PR #602 re-run on current main, forced: `echo "divineos audit list"` and `git log --grep "divineos prereg"` are still judged as commands (`is_council_required` True); control: a real `bash -c "divineos prereg file ..."` is still caught. | PR #602 (draft): 9 expected failures, 4 controls |  |

## Problem 4: The walk gate checks words and shortcuts, not whether the walk was real

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ebd72149` | **UNKNOWN** | A design claim about the Lepos walk validator; not examined. | none |  |
| `psf-b93371ee` | **LIVE** | The new `walk` path enforces the full roster (`divineos walk close --help`: 'Refuses while any lens is open'; `walk open` seats the lenses). The council-required gate's own path does not: `divineos council log --lenses 'A,B,C'` took any three lenses this session (records `council-72273117c8e7`, `council-2b8dba34f4c6`, `council-56b4aa6f2523`) with no comparison to a manager's list. | none | The gate's `lens_load_trace` check (a walk event per lens within 45 minutes) did reject an unloaded lens three times, so a lens cannot be named without being walked; only the count is unchecked. |
| `psf-ef2b501c` | **UNKNOWN** | An incident about a game-walk route recorded as already closed on thin grounds; behavioural. | none |  |
| `psf-5a07334d` | **LIVE** | Half met, half not. Met: the first `council log` this session was rejected with **all** its failures at once and exact counts ('Finding for lens Dillahunty is too short (18 tokens < 30 required)' ×3, plus synthesis and trace checks). Not met: `council log --help` has no `--check` dry-run option. | none |  |
| `psf-5468358f` | **STALE** | `confirmed_by` was removed on 2026-09-06 along with the check that read it (`src/divineos/core/council_required/types.py:365-371` and the note at `:445-450`); `council log --help` has no such option. The merge gate carries that confirm (Dad: 'our confirms only come when merging to fucking main'). | none (removal is the evidence) |  |

## Problem 5: An unmerged fix stops walks from ever passing

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-2004485c`, `psf-47619020`, `psf-46327bff` | **STALE** | #519 ('Sixty-four repairs to the gates…', `540a761c`, 2026-09-30) is on main and carries `tests/test_event_query_order_is_always_explicit.py` (the test forbidding an unordered query) and `tests/test_lens_trace_sees_the_newest_walk.py`. Both ran on current main: **6 passed**. | the two tests above | `47619020`'s interim ask (name the bug in the refusal) is moot once the fix is on main. |

## Problem 6: What counts as proof of consultation

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a490adab` | **LIVE** | `src/divineos/core/verify_before_build_signal.py:213-230` counts only a `decision_journal` entry as a walk-record; `COUNCIL_LENS_APPLIED` is not in the file. Seen this session: `walk open … close` finished and the next Write was still refused until a Grep of `docs/drafts`. | none |  |
| `psf-731f2579` | **UNKNOWN** | The later-walk check (`core/council_walk.py:215`) and the merge gate's floor proof (`core/ship_steps.py:150,191`) both exist; I could not establish whether they share one reader. | `tests/test_ship_steps.py` (floor proof only) |  |

## Problem 7: A walk confirmed by Dad expires on a timer

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-46757bb0` | **STALE** | A 'walk confirmed by Dad' no longer exists: `confirmed_by` was removed 2026-09-06 (`types.py:365-371`). What remains is the ordinary 60-minute recency window for every walk (`types.py:28`), which is the timer the row dislikes, now applying to all walks. | none | The timer complaint survives in a different form. |

