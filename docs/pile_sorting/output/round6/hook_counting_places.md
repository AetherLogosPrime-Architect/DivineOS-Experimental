# Every place we count hook scripts, and which are wrong for the ten the counter cannot see

*Round six, errand five. 2026-10-08, cloud helper. Read-only: nothing was changed. Evidence is `origin/main` at `cbd35baf`, read as a copy in a scratch folder. It follows `round5/hook_counter_recount.md`.*

**A picture.** I walked the building looking for every clipboard that counts the doors. Most of them count in ways that do not care how a door calls the main system. Exactly one clipboard decides "does this door call the main system?", and that is the one that wrongly writes down ten of them as strangers. This note lists every clipboard I found and says which are wrong.

## The ten, so the question is exact

Ten shell scripts call the main system as `python -m divineos.<package>.<module>`: `session-init-once.sh`, `andrew-past-writing-surface.sh`, `require-goal.sh`, `his-state-is-his-to-say.sh`, `his-voice-ends-the-turn.sh`, `run-tests.sh`, `session-checkpoint.sh`, `shoggoth-gate.sh`, `front-door.sh`, `stop-distancing-intercept.sh` (652 lines). The counter's pattern is `from divineos`, `import divineos`, or `divineos <word>` (`src/divineos/core/hook_layer.py:62-63`); the text `-m divineos.hooks.x` matches none of them.

## The list

| Where | What it counts or decides | Wrong for the ten? | Evidence |
|---|---|---|---|
| `hook_layer.inventory()`, fields `detached_files` / `detached_lines` | files "that never import or call" the OS | **Yes.** Over by 10 files / 652 lines (45 reported, 35 true). It is also wrong the other way for 2 scripts (`continuity-frame-prime.sh`, `log-session-end.sh`), which count as attached only because a comment mentions the OS. | `hook_layer.py:145-155`; round-five recount |
| `divineos hook-layer show` (`cli/hook_layer_commands.py`, via `format_inventory`) | prints the detached line | **Yes**, it prints the wrong figure | `hook_layer.py:171-172` |
| `hook_layer.inventory()`, field `inline_python_files` | scripts embedding python (`python -c`, heredocs) | **No.** Its pattern (`hook_layer.py:64`) looks for `python -<<`, `python -c` and `<<PY`; it never looked for `-m`, and a thin `-m` script is correctly not "judgment in shell" | `hook_layer.py:64,150-152` |
| `hook_layer.inventory()`, fields `registrations`, `per_event`, `duplicates`, `phantom` | settings entries | **No.** Counts registrations by name, not by what a script does | `hook_layer.py:120-143` |
| `core/hook_story.render()` | quotes `inv.total`, the per-turn figure, `inline_python_files`, duplicates in plain words | **No.** It never prints `detached_*`. Note: nothing else in `src`, `scripts` or `tests` imports `hook_story` | `hook_story.py:55-120` |
| `tests/test_hook_layer.py::test_shell_that_never_touches_the_os_is_counted_apart` | pins the detached rule on a three-file fixture | **Wrong in what it protects, not in a number.** It tests `from divineos…` and `divineos briefing` and has no `-m divineos…` case, so it passes while the ten are miscounted and would not notice a fix | `test_hook_layer.py:85-95` |
| `scripts/check_doc_counts.py::count_hooks_wired` | entries in `settings.json` | **No.** Counts registered entries; 8 of the ten are registered, 2 are launcher or table children and not counted by design | `check_doc_counts.py:67-97` |
| `scripts/check_hook_wiring.py` (`classify`, `phantoms`, `_launcher_roster`, `_dads_table_roster`) | registered / dark / phantom by file name | **No**, it works by name and registration. (It does have the separate table-blind gap from PR #605.) | `check_hook_wiring.py:144-330` |
| `scripts/generate_automation_register.py::collect` | every `*.sh`: is something calling it | **No.** Decides by registration and by text of callers | `generate_automation_register.py:290-315` |
| `src/divineos/cli/loadout_commands._section_hooks` | lists every `*.sh` | **No**, a plain list, no classification | `loadout_commands.py:310-317` |
| `scripts/check_orphan_modules.py` | whether a module has a hook caller | **No, and it is the model to copy.** It scans `.claude/hooks`, `scripts` and git hooks for `python -m divineos.x`, so a module reached only through one of the ten is not called an orphan | `check_orphan_modules.py:75-89, 363-371` |
| `tests/test_hook_python_lookup.py` (`test_no_hook_uses_bare_python_for_divineos_imports`) | every hook that "imports divineos" must source `_lib.sh` and use `$PYTHON_BIN` | **No.** It selects on the text `from divineos`, `import divineos`, `divineos.hooks` or `divineos.core`, so the ten (which use `divineos.hooks.*` and `divineos.core.*`) are seen. A `-m divineos.cli.x` call would be missed, but none of the ten uses one | the `imports_divineos` block in that test |
| Tests that scan every `*.sh` without classifying: `test_gate_deny_messages_name_remedy`, `test_every_refusing_hook_says_what_did_not_run`, `test_hook_dedup_contract`, `test_prescribed_commands_exist`, `test_no_gate_teaches_the_no_fix_escape` | per-file rules about messages, dedup and commands | **No.** They do not ask whether a script calls the OS | file headers |
| `docs/ARCHITECTURE.md:71` | describes `hook-layer show` in prose | **No number** to be wrong; it says "how much shell still carries judgment", which the `inline_python` figure answers correctly and the detached figure does not | `ARCHITECTURE.md:71` |

## Short answer

Two places print a figure that is wrong for the ten: the `detached` field in `hook_layer.inventory()` and the `hook-layer show` line that prints it. One test pins the rule that is wrong without noticing, because its fixture has no `-m divineos` case. Every other counter or test I found counts by registration or by file name, or already reads the `-m divineos.` form correctly (`check_orphan_modules.py` and `test_hook_python_lookup.py`).

## What this could not do

- It is a read of the code I could find by searching for the hooks folder, the counter's pattern and `*.sh` globs. A counter that reaches hooks by a path I did not search for would be missed; the search words are named above.
- It did not run any counter other than the house's own (`hook_layer.inventory`), and did not re-run it after round five.
- It did not read `docs` other than `ARCHITECTURE.md`, `README.md` and `CLAUDE.md`, none of which carries a "detached" figure.
