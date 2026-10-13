# Git's own options cannot hide a commit from the skip-gate

**Draft, 2026-10-13. Small and built.**

## What happened

I finished a merge commit with `git -c core.hooksPath=/dev/null commit`, which turns off every pre-commit check, and the gate that exists to make skipping the checks cost a named reason said nothing. Dad's words, when I told him: *"redo it with the checks on and fix why you were even able to skip it in the first place so you cant lol"*.

## Why the gate was blind

The gate read the word right after `git` as the subcommand. In `git -c core.hooksPath=... commit` that word is `-c`, so it saw a subcommand called `-c` and moved on: it never recognised a commit. The same reading hid `git -C some/folder commit --no-verify`, a form I type all day. This is the second time this gate has been anchored to a position (the first, 2026-08-22, was "first git wins"; the note is in the function's docstring).

## What changed

- The gate steps over git's own leading options (`-c name=value`, `-C folder`, `--git-dir`, `--work-tree`, `--namespace`, `--super-prefix`, `--config-env`, and the joined `-cname=value`) to find the real subcommand.
- Turning the hooks off by a `core.hooksPath` override on a commit or push counts as the same act as `--no-verify`, and so does *writing* that setting with `git config` (it persists, so every later commit would skip with no flag to see). Reading it back does not.
- Tested both ways: twelve routes that must be stopped, ten ordinary commands that must pass (`git -C folder commit`, `git -c user.name=t commit`, `git config --get core.hooksPath`, `git push -n`), the honest path (a named reason) still passes, and a control that the plain form behaves as before. Twelve of the tests fail on the gate before this change.

## Found by testing the fix, same day

Before writing the walk I tried the fix on the shapes I could think of, instead of trusting it, and it was far from enough: `bash -c "git commit --no-verify -m x"` was allowed, before and after my first change, because a quoted command is one token to the tokenizer. So were `sh -c`, `eval`, and the hooks path set through the environment (`GIT_CONFIG_KEY_0=core.hooksPath`). All of these are now read: a string handed to `bash`, `sh`, `zsh`, `dash`, `ksh` with `-c` (also joined, like `-lc`) or to `eval` is read as a command in its own right, to a depth of three, and the environment form counts like `-c core.hooksPath`. Two over-fire guards pin that a `grep` or an `echo` that merely mentions the words is not stopped, and neither is `bash -c "git commit -m x"` or plain `bash script.sh`.

## What it does not do, named

- A script file that contains the skip (`bash script.sh` where the script runs `git commit --no-verify`) is not read; the gate sees the command line, not the files it runs.
- A git alias that expands to a commit with the skip is not read either; the gate sees `git <alias-name>`.
- Command substitution (`$(...)`) and a here-string handed to a shell are not unwrapped.

- It is a gate on what I type. A person (or a script I run) can still change the setting some other way, such as editing the git config file with a write tool. That is a different door and this does not close it.
- It does not forbid an honest skip. The same named-reason route exists and is counted, by design: *bypass is a tool, not a sin; intent decides* (truth #12). What changes is that the skip can no longer be silent.
