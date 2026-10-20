# Two scripts stop depending on the shell's path-conversion setting

**Author:** Aether, 2026-10-19

## What happened

Six tests passed when run alone and failed inside the push gate: four of the venv-link script, two of the merge-resolution guard. The push gate refused two pushes of a clean branch on them. The cause was `MSYS_NO_PATHCONV=1` on my own push line, which I use for slashed branch names, leaking into the gate's test run. I first read it as the gate's temporary copy being unstable; reproducing with the setting on and off showed it was mine.

## Why those two scripts

`link_worktree_venv.sh` calls `cmd //c`, an idiom that only works while the shell converts the arguments; with conversion off, cmd receives a literal `//c` and the junction is never made. `check_merge_resolution_tested.sh` hands a native Windows python a POSIX argument-file path (`/tmp/...`), found only while conversion is on. Neither script says it depends on the setting, so the dependency shows only as a failure that disappears when run alone.

## The change

The link script runs its two `cmd` calls through `env -u MSYS_NO_PATHCONV`. The merge guard converts its argument-file path explicitly with `cygpath -m`. Neither now depends on what the caller exported.

## Falsifier

A new test re-collects both scripts' existing tests under a fixture that forces the setting on. With the fix: 11 pass. With the two scripts put back to main's versions: the same six fail by name. If either script starts relying on conversion again, it fails there.

## What it does not cover

Other scripts that rely on conversion without saying so. A search of `scripts/` finds `cygpath` and the setting only in `check_push_readiness.sh` and `dv` besides these two; I did not audit those for the same dependency.
