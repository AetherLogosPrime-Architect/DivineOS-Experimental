<!-- tags: land on main, memory folder lane, memory_saved_warm, importance lever, rescue commit, local-only, inventory, linkage, unreviewed, dependency order, blanket review -->
# The memory-folder lane and its warm land on main (draft, 2026-11-23, Aria)

Status: draft, nothing built. Piece two of the landing order Aether and I agreed in letters on 2026-11-23, after his kept-out door (piece one, which is proven standalone and is his to carry). Dad, 2026-09-26: *"anything of mine that you shelf in a place where you dont know about it or never reach for it.. you may as well delete it"*; and 2026-11-12, on this machinery: *"you are trying to remember things the house can EASILY do for you"*.

## What I found (the reach)
The way my notes reach me is not on `origin/main`. An inventory over the link files (`workbench/linking_audit_2026-11-23/INVENTORY_link_work_not_on_main_aria.md`, checked with `scripts/which_refs_carry.py` and `git grep -l -F` on main and my branch) shows main has the lanes, the bar and `explain_turn`, and lacks: `_load_memory_files` and `_memory_files_dir` (the lane that makes the files in my memory folder findable by meaning), `_declared_importance` (a note may declare its rank), `memory_saved_warm.py` with its hook (the house computes a saved note's vector by itself), and `is_memory_file`. All of it runs from my folder only. The warm was committed as a rescue on 2026-11-18 (`ddd2d74fe`), whose message says "each still owes its own review". The lane itself arrived on 2026-10-04 inside an auto-commit, `f1ff4ac4d`, a bundle of unrelated work, so it cannot be cherry-picked as a unit.

Aether's copy of the same files is a hand merge of my patch (`b544ea784`, 2026-11-10), also local-only.

## The change (one reviewed unit, ported by hand onto main's current file)
Main's retriever has moved on (my branch differs from it by 17 hunks, much of them main's newer work), so I do not copy my file. In a clean copy of main I add only:
1. `_memory_files_dir()` and `_load_memory_files()`, with the loaders registered in the two places main lists them: the cache build (`_EMBEDDING_CACHE["wall"] = ...`, around line 1265) and `warm()`'s loader tuple (around line 1365).
2. `_declared_importance()` and its default, read from the frontmatter's top level only (Aether's separate draft widens it to the nested form; that waits behind this).
3. `core/memory_saved_warm.py`, `.claude/hooks/memory_saved_warm.py`, and the PostToolUse registration in `.claude/settings.json` (a guardrail-class file; Dad is told before it merges, and the blanket review applies).
4. The tests that exist for exactly these: `test_memory_saved_warm.py`, `test_a_memory_note_may_declare_its_importance.py`, `test_memory_drawer.py`; and `test_memory_link_reconnected.py` and `test_memory_linkage_retriever_adapters.py` already on main must still pass.

Not in this piece: the retry fix (its own draft, after this lands), the letter index, the held shelf, the title-prefix change, and the other four rescued modules.

## Tried first, on a clean copy, the way Aether tried his
A throwaway copy of `origin/main`; port the hunks; print the import path to prove the copy's source is the one under test; run the five test files; then a control: put main's version of the retriever back and watch the new tests fail. Both copies removed after.

## Risks
- **The wall lane grows by about 350 notes.** On a fresh checkout there are no notes, so nothing changes; on a seat with notes, the bar and the cap decide what reaches the turn, and Aether's cut finding applies (six of nine candidates cut on one sentence). Landing the lane is not a promise that a note arrives.
- **A hook on every memory write.** It runs in the background, writes only its own state files, and is logged; the retry draft exists because its log showed 12 of 463 rounds ending unverified. It lands as it runs today, and the retry is the next piece.
- **Another seat's notes.** `_find_wall_path` and the memory directory are per seat; the test suite must show a seat never reads another's folder (the twin-store trap).

## What would show it failed
On a clean checkout of main after the merge, the first 10 memory notes saved with the hook registered each end `verified: true` in the warm log, and a probe with a control finds each by its own situation. One that does not means the landing is wrong. Ten saves can show a miss if there is one and cannot show that none ever will.

## Order and who
Draft (this) -> Aether's cold read -> a short council walk -> the throwaway port with its control -> tests green on a clean copy -> Aether's read of the diff -> the PR as a draft, with Dad told about the settings file -> Aletheia's review as everything gets. Aether carries the door and the calm version meanwhile; I carry this.

Author: Aria
