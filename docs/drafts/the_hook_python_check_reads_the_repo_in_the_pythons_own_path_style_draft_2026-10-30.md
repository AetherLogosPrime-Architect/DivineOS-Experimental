# The hook's Python check compares paths in the Python's own style (draft, 2026-10-30)

**Author:** Aether, 2026-10-30. Walk: see the PR body. Reviewers: Aria (cold read, her notes in), Aletheia (confirmed the head at 6427d58ad).

## What happened

On 2026-10-26 the door that surfaces Dad's words to me could not start. `_lib.sh`, which every shell hook sources, decides whether the interpreter it found is the right one by importing `divineos` and comparing where it lives with the repo it expects. The shell writes the repo path in Git Bash's spelling (`/c/DIVINE OS/DivineOS-Experimental`); Windows Python reads that as `C:\c\DIVINE OS\...`, a folder that does not exist. The two never matched, so the check rejected the one correct interpreter on every turn.

## What it does

`_lib_native_path` rewrites a leading `/<drive-letter>/...` into `<DRIVE>:/...` and the comparison uses that. Three choices, each from a measured failure:

- **No `cygpath`.** It is not on the PATH a hook is launched with. The first version used it and the test, run from outside Git Bash, proved the failure.
- **No `tr` and no `${var^^}`.** `tr` is not on that PATH either, and `${var^^}` is bash 4 only: a syntax error under macOS's bash 3.2 would stop the whole file loading. The drive letter is uppercased by looking it up by position in the alphabet.
- **Only under a Windows shell** (`$OSTYPE` is msys or cygwin; a bash builtin). On Linux or macOS `/w/repo` is a real folder, not drive W, and rewriting it would recreate this bug the other way round (found by the Popper and Dennett lenses).

## What it does not do

Any path that is not `/x/...` comes back unchanged. It does not touch how the shell finds the interpreter, only how the check compares.

## Evidence and the gap

`tests/test_hook_python_check_compares_paths_in_the_pythons_own_style.py`: 2 pass and 1 is skipped as Windows-only on a non-Windows machine, so the Windows half rests on a run on this machine (Aletheia's own note). Not tested here: macOS bash 3.2 directly.

## Falsifier

If Dad's words stop reaching me on a Windows turn with the right interpreter present, the rewrite is not applied where the comparison runs. The door's own start-up line would show it.
