# The first push of a new core module or hook

For whoever adds a file under `src/divineos/core/` or a hook under `.claude/hooks/`.
Each item below is a way the first push has failed. Each was checked against the
scripts and tests named here on 2026-11-03; if a name has moved, trust the file over this note.

## 1. The architecture tree does not list the new module

- **Symptom:** the doc-count check prints `UNDOCUMENTED: core/<name>.py (exists but not in README architecture tree)`.
- **Cause:** the check compares every module on disk with the tree. The tree now lives in
  `docs/ARCHITECTURE.md` under `## The tree`; the README is only a fallback if that is missing.
  (The message still says "README". It is the old wording, not the place to edit.)
- **Fix:** run `python scripts/check_doc_counts.py --fix`, which appends the line to `docs/ARCHITECTURE.md`, then fill in its description.
  It only adds missing files. A file listed but not on disk (a "ghost") is never removed for you.
- **Look at:** `scripts/check_doc_counts.py` (`check_architecture_tree`, `fix_architecture_tree`).

## 2. The PreToolUse hook count is now wrong

- **Symptom:** `test_a_new_pretooluse_hook_is_a_decision_not_a_drift` fails with
  "N PreToolUse hooks are wired, the list was written against M".
- **Cause:** the test counts the hook commands under `hooks.PreToolUse` in `.claude/settings.json`
  and compares with a hard-coded number (`_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN`). Adding a hook moves the count on purpose.
- **Fix:** decide whether the new gate asks the shared remedy list (`core/remedy_allowlist.py`) and whether its own way out is on it; then change the number and add a one-line comment saying what was decided (see the 34 to 33 comment above it for the style).
- **Look at:** `tests/test_every_exit_passes_every_gate.py`, near line 363.
- Only hooks wired into `settings.json` under PreToolUse count. A session-start check (item 5) does not.

## 3. A new core file has no prereg in the commit message

- **Symptom:** the commit-msg check `scripts/check_prereg_for_new_infra.py` exits 1 on a commit that adds a new file under `src/divineos/core/`.
- **Cause:** new core infrastructure must name a pre-registration, matched as `prereg-` plus 12 hex characters, anywhere in the message body.
  It only looks at new files in `src/divineos/core/`, not at edits and not at hooks.
  The script's docstring still names `DIVINEOS_NEW_INFRA_NO_PREREG=1`, but the code ignores that variable. The bypass that works
  is `DIVINEOS_NEW_INFRA_EMERGENCY=<reason>` (it needs a reason, and firing it is logged); do not reach for it without a real reason.
- **Fix:** file one first, then paste the id (`prereg-xxxxxxxxxxxx`) into the commit body:
  `divineos prereg file "<mechanism>" --claim ... --success ... --falsifier ... --embarrassing ... --review-after-uses N --uses-of <EVENT_TYPE>`.
- **Two corrections to older advice:** `--embarrassing` is also required now (the reading that would make you sorry you built it),
  and `--uses-of` must name a ledger event type that has already happened at least once, for example `SLEEP_CYCLE`. Reviews go by use count, not by date.
- **Look at:** `src/divineos/cli/prereg_commands.py` (the options) and `scripts/check_prereg_for_new_infra.py`.

## 4. A hook that never refuses is not declared as non-gating

- **Symptom:** `test_the_dark_set_can_shrink_but_never_grow` fails: "these hooks are neither declared non-gating nor detectably refusing".
- **Cause:** the test scans every file in `.claude/hooks/`. A hook with no denial pattern in its source and no entry in the non-gating list is "unexamined", and the unexamined set may not grow.
- **Fix:** add the file name to `_NON_GATING_HOOKS` with a comment giving the reason, in the same style as its neighbours: what it does, and that every path exits 0.
  Do not add it to `_UNCLASSIFIED_BASELINE`; that list may only shrink.
  If the hook does refuse, teach its shape to `_DENIAL_PATTERN` or `_EXIT_CODE_DENIAL` so the test then checks that its message names a way out.
- **Look at:** `tests/test_gate_deny_messages_name_remedy.py`.

## 5. A session-start check is not registered where it runs

- **Symptom:** the check never fires at session start, and nothing complains. Adding it to `settings.json` does not help.
- **Cause:** the session-start work is gathered in one launcher, `.claude/hooks/session-init-once.sh`. It is a UserPromptSubmit hook, not a
  SessionStart one (it was moved off the SessionStart path on purpose; read its header). It runs the scripts named in its `INIT_HOOKS`
  roster, once per session, on the first prompt. A script that is not on the roster is not run.
- **Fix:** add the file name on its own line in the `INIT_HOOKS="..."` block, with a comment saying why and when. Comment lines inside the block are allowed.
- **Look at:** `.claude/hooks/session-init-once.sh`, near line 129.
  A listed name that is missing from disk is skipped with `continue`, so a typo means the check does not run and the prompt still goes through cleanly.
  It is not wholly silent: the launcher appends a `listed_child_missing` row to `~/.divineos/hook-liveness.log`. Nothing shows in the session,
  so look in that log after adding a name, and check the spelling.

## 6. A script run from Python by a drive-letter path exits 127

- **Symptom:** `/bin/bash: C:/.../script.sh: No such file or directory`, exit code 127, when Python starts `bash` on a script by its `C:/` path.
- **Cause:** the `bash` that Python finds first on PATH can be `C:\Windows\System32\bash.exe`, the WSL launcher, not Git's bash
  (`where.exe bash` lists both here; check which comes first on yours). WSL's bash reads `C:/x` as a folder name in the current
  directory, not as a drive path, which is where the 127 comes from. Git's own bash accepts `C:/...` paths.
  Windows Python in turn does not read the `/c/...` form Git Bash writes, so those two styles do not meet.
  The earlier 2026-11-03 test that gave 127 ran through whichever `bash` was first on PATH (the WSL one); it was not re-run against Git's bash by full path.
- **Fix:** call Git's bash by its full path (`C:\Program Files\Git\usr\bin\bash.exe`), or feed the script on stdin, `bash -s` with the file's text as input (tested, works), or give a path relative to the working folder.
  The relative-path form I did not test here. For a hook that must hand a path to Python, `_lib_native_path` in `.claude/hooks/_lib.sh` converts `/c/...` to `C:/...`, the right direction for Python.
- **Look at:** `.claude/hooks/_lib.sh` (`_lib_native_path`).

## Before you push

Run `bash scripts/precommit.sh`; it formats and runs the gates. Commits do not need an `External-Review` trailer, but the squash-merge body does. See `CLAUDE.md`, hard rule 8.
