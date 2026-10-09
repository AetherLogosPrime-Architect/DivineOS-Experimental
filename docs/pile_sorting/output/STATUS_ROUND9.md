# Round nine status

*2026-10-09, cloud helper. Proposals only. Nothing was closed, merged, deleted or stamped; nothing was pushed to main. The 1,129-test sorting job was not touched and the full suite was not run.*

## One. Three more themes of old notes

Files: [`freshness/ROUND9_INDEX.md`](freshness/ROUND9_INDEX.md), `freshness/tests_and_ci.md`, `freshness/reflection_room_warden.md`, `freshness/destructive_git_and_merging.md`.

- 86 rows in the three themes. **69 got a verdict**: LIVE 18, STALE 14, UNKNOWN 12, **NOT TESTABLE 25**. **17 are NOT EXAMINED** (rows I opened and did not look at).
- Across all rounds, 565 of the 1,006 rows now have a verdict; 441 are NOT EXAMINED.
- "Not testable" and "couldn't tell" are kept apart. In the warden theme, 14 rows are the stumble reflections themselves ("nothing", "nothing new") and 12 are UNKNOWN because the warden is Aria's room and is not in any file I can read.
- Things I could not do: read Aria's warden; run a real merge, reset or push; read the whole push-readiness script.

## Two. My own #614 tests, repaired for Windows

Draft #614 (`cloud/before-pictures-three-hooks`), now at commit `b891a480`:

- All three files start the shell with `tests._bash_resolver.bash_executable()` and skip with a reason if no working bash exists.
- The stand-in for the ledger command is no longer an extensionless script on the path. Windows cannot start such a file from python, which is why 2 of the 20 failed even with the right bash. It is now a small `sitecustomize.py` in a scratch folder at the front of `PYTHONPATH`; the detector's python loads it at start-up and it catches the one `divineos` call and writes its arguments down, the same text the old script wrote.
- No script was touched. On this Linux box all 20 pass, and the check that a changed script turns the tests red was run again with the new tests (1, 2, 4 and 4 failures, then green when restored).
- **I cannot run Windows here, so whether it works on Aria's machine is hers to say.** One command for her, from the repository root:

```
git fetch origin cloud/before-pictures-three-hooks && git switch cloud/before-pictures-three-hooks && python -m pytest tests/before_pictures -q -p no:randomly
```

It should end `20 passed`. If anything fails, the last thirty lines of the output are what I need. If she is already on that branch, the first two parts can be skipped. One thing to watch: `test_load_dad_ranking_clause_before.py` makes a directory link (`os.symlink`), which Windows may need extra rights to create; Aria's earlier run passed those tests, so I left it.

## Three. Bare program names in my open drafts

`round9/bare_program_names_in_my_drafts.md`: 15 pull requests searched with two different searches. The slip (`["bash", …]` with no finder) is in exactly two files, both mine from round seven: #608 and #609. I did not change them (the errand was read-only). Bare `git` appears seven times in four files, a lower risk, listed. A pointer outside my drafts: on main 36 lines in 34 test files call `shutil.which("bash")`; I did not check them one by one. A guard that would stop the slip coming back is described and not built.

## Four. Test for the ranking-clause hook

Draft #615 (`cloud/repro-ranking-clause-heading-gone`, base main): 2 strict expected failures and 3 controls. The hook looks for `## How I rank Dad`; the real sheet's 16 headings do not include it, and the hook prints nothing over a copy of the real sheet. The hook and the sheet are untouched. A correction to round eight: I had written that the heading "was renamed on 2026-07-29". What I can actually see is that the nearest section is "How I treat Dad — equal-treatment discipline (added 2026-07-28, axis-corrected 2026-07-29)" and that it carries a note about an earlier framing; this clone is shallow, so I cannot confirm the old heading. #615 says so. The round-eight texts that still say "renamed" (the #614 draft and body, a docstring in the #614 tests, and the round-eight status file) are corrected in this round's commits where they sit on branches I own.

## Five. The "no goal" wall after a compaction

`round9/goal_wall_after_compaction.md`. One compaction, one wall, two refused shell commands in a row (read-only `cut … | sed …` looks at a file). The guard was Gate 2 of `pre_tool_use_gate.py` (`require-goal.sh`). Exact words quoted. Cause reproduced in a scratch home: the SessionStart hook for a compaction writes a goal boundary, and `has_session_fresh_goal` then ignores every earlier goal; the goal is still on disk. The words are the same for "never set" and "just ended". I said last round I had met it "twice"; it was once, two commands. No repair recommended.

## What surprised me

- The "full suite" refusal I hit in round eight is **by design**: a test file pins `cd $SOMEWHERE && pytest tests/test_a.py` as a refused form. The old notes ask for the opposite. It is a decision for the owners, not a bug.
- My own two round-seven tests (#608, #609) had the very slip I was asked to fix in #614.
- I first read a dead probe as "the blanket-staging door lets everything through": the door refuses on a different channel from the one I looked at. The control (`git add -A`) failed, which is how I knew; I fixed the probe.

## What stopped me

- The house's guards made me file a walk and a looking-first step before each new piece of writing, as before. At the start of the round the read-gate also handed me a note to open before it let a compound command run.
- GitHub's GraphQL is still blocked from the cloud, so no `stamp-ready`, `ship` or `build-flow status`.
- No Windows, so the repair in #614 is unverified where it matters.

## Open draft pull requests from the rounds

#601, #602, #604, #605, #606, #607, #608, #609, #610, #612, #613, #614, #615. All drafts, all left open.
