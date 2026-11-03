# Second reader: findings on 777 and 778

A cold read, 2026-11-03. I did not merge, stamp, confirm, approve, comment on or edit either PR. Findings are marked REPRODUCED (run against the PR head's real code, extracted to a scratch folder with PYTHONPATH pointing at it, `__file__` checked) or "from reading". Native Windows Python 3.13, Git Bash for the shell tool.

---

## PR 777: scratch paths outside the house, and deleting what is already gone

**Read:** head `836d6ec594de8ecb769728671301c3705723159b`, base `6de941c54`. The whole diff, `deletion_discipline.py`, and `gravity_classifier.py` (`_guardrail_listed_paths`, root detection, `score_substrate_modification`). Compared against base where base can answer.

Findings: 2 high, 2 medium, 1 low.

1. **HIGH, REPRODUCED: a Git Bash style path to an existing folder is waved through.** `_rm_targets_all_missing` (`deletion_discipline.py`, ~L112) tests `os.path.lexists` with native Windows Python, which cannot see `/c/...` paths. `rm -rf "/c/DIVINE OS/.../docs"` (folder exists) gives `(False, None)` on the PR head and `(True, 'rm recursive/force')` on base. The native `C:/...` spelling of the same folder is still held. The Bash tool here is Git Bash, so this spelling is likely in real use.
2. **HIGH, REPRODUCED with a simulated layout: when the house is itself a linked worktree, the main checkout's hooks are freed.** `_is_outside_the_house` (`gravity_classifier.py`, ~L242) decides "linked worktree of this repo" by checking that `root/.git` appears in the gitdir the other folder points to. That is true only when the root is the main checkout. When the root is a linked worktree (agents run in `.claude/worktrees/agent-*`), the main checkout (`.git` is a directory) and sibling worktrees or clones fall through to `return True`. With a hand-made `.git` file in the scratch root and `M/.git` as a directory, `Edit` on `M/.claude/hooks/x.sh` gave `fired_features=()` and council not required on the PR; base gave `('edit-guardrail',)` and True. The PR's linked-worktree control test covers only root-is-main. (`git worktree add` was refused by the sandbox at the time, so the layout is simulated.)
3. **MEDIUM, REPRODUCED: relative targets and paths are read against the hook process's cwd, not the shell's.** `rm -rf src` is freed or held depending on the process cwd. Whether the real hook's cwd equals the Bash tool's persisted cwd I could not check.
4. **MEDIUM, REPRODUCED: 6 of 38 of the PR's own tests fail on native Windows Python.** Four in `test_deletion_of_nothing_is_not_a_deletion.py` and two redirect tests in `test_scratch_paths_are_not_the_house.py`, run in a non-temp folder so it is not the temp exemption. Cause: `str(Path)` backslashes in the command strings. The redirect-with-backslash case fires nothing on base either (old behaviour). An unquoted backslash `rm -rf C:\...\M` of an existing folder is freed (shlex eats the backslashes); Git Bash would eat them too, so I could not show a real deletion slipping, only that the tests are not portable and the door is wrong if it ever sees PowerShell or cmd commands.
5. **LOW, from reading:** a symlink inside the repo that points outside resolves outside and is freed (a hooks folder symlinked to a shared location would be). Relative paths are read against the root, as the docstring says.

**Could not check:** whether the hook's cwd equals the shell's; a true linked-worktree layout (simulated).

**One thing it gets right:** the missing-target proof fails toward "held" on every doubt (globs, variables, non-`rm` clauses, dangling symlinks, no target), and the controls test the mixed cases (existing beside missing, a second clause).

---

## PR 778: a letter may open with front matter and still declare what it read

**Read:** head `c25a87dd6e67b66834c3a612cdf04d41d26abdee`. The whole diff, `build_flow.header_lines`, `_declared_readings`, `_front_matter_end`, and the `baton._header` caller. The PR's 28 tests in `tests/test_baton.py` pass.

Findings: 0 high, 1 medium, 2 low.

1. **MEDIUM, REPRODUCED: the baton reads front matter too, and neither the draft nor the tests say so.** `header_lines` is shared with `baton._header`. `---\ntitle: t\n---\n# x\n**Baton:** pass\n**To:** aria` gives `{}` on base and `{'baton': 'pass', 'to': 'aria'}` on the PR head. All seven new tests use `_declared_readings`; none covers a baton field after front matter.
2. **LOW, REPRODUCED: common front matter is not recognised.** A BOM-led file, a YAML list, a blank line inside the block, spaced keys (`In response to: x`), dotted keys, and URL lines all return `(False, [])`. That is the safe direction (old behaviour), but the draft's "cannot see" does not mention it.
3. **LOW, partial measurement:** 1,206 of 8,793 letters on disk (`~/.divineos-shared/letters` and `family/letters`) open with `---`; 15 have a BOM. I did not finish the split into how many the PR's rule actually recognises.

**One thing it gets right:** the rule is narrow and tested at its edges (line 12, no close, a prose line, a rule pasted lower down, a `Reading` inside the block credits nothing), and everything unrecognised falls back to the old behaviour.

---

## Scratch folders left behind

The delete door holds their removal, so they are still there: `C:\Users\aethe\AppData\Local\Temp\claude\scr`, `C:\Users\aethe\scr777`, `C:\Users\aethe\scr777base`, `C:\Users\aethe\scr778`, and the worktree `C:\Users\aethe\second-reader-c`.
