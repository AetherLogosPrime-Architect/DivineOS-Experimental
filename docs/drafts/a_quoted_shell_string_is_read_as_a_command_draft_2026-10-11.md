# A quoted shell string is read as a command (draft, 2026-10-11)

**Author:** Aether. Aria, 2026-10-11 ("take the fix"): *keep the old text search as the fail-toward-firing direction when the wrapped string cannot be read, and put every row of the mutation family in as a test, with the echo-of-the-words rows too, so the fix cannot become a new hole in the other direction.*

**Stacked on** the pins package (branch `aether/the-pins-package-five-proof-tests`): it removes the `xfail` mark that package puts on the control this change turns green. Merge the package first; until then this request's diff against main also shows the package's files.

## The fault

#619 made the council classifier read each segment's real head (`_runs_divineos_verb`) so words inside a quoted string, a heredoc or a help flag stop counting as the act. A side effect nobody tested: a real write wrapped in a sub-shell, `bash -c "divineos prereg file x --claim y"`, has head `bash`, the quoted string is one token, and the old raw-text search that used to catch it only runs when the splitter cannot read the line. So the wrapped write scores zero and skips the council gate. The cheaper route, open on main since #619.

Found by the cloud helper's control test (written 2026-10-08, psf-9c6f5a9c: the repair "must not let a real command hidden inside `bash -c` through"), which sat on an unmerged branch and went red without anyone seeing it. Reproduced on a clean checkout of main: `score_substrate_modification("Bash", (), 'bash -c "divineos prereg file x --claim y"')` returns score 0.

## The change

- `core/command_parsing.py` gets one public helper, `shell_command_body(tokens)`: the command string a shell is told to run (`bash|sh|zsh|dash|ksh -c "<cmd>"`, including `-lc`, `-ic`, `--login -c`, and `eval "<cmd>"`), or None. It lives beside the other shared parsing, so the next gate that needs it asks it and does not write a fourth copy (Aletheia's pattern: a private copy of a judge the house already has; `full_suite_by_hand` keeps its own list today and is not touched here).
- `_runs_divineos_verb` asks it for each segment and, when there is a body, runs itself on the body. So the wrapped form is judged exactly as the plain form is: a wrapped write fires, a wrapped look (`bash -c "divineos prereg show x"`) or help does not, and an echo of the words does not. A body the splitter cannot read still falls to the raw-text search, which fires: unreadable means assume heavy, the direction #619 already uses.
- The `xfail` mark on the helper's control comes off in this change.

## What proves it

`tests/test_a_wrapped_command_is_read.py` runs Aria's mutation family through the real classifier: wrapped real writes for each shell and flag spelling, a prefix (`sudo`, `env VAR=1`, a full path), a compound body, a nested wrapper, an `eval`, a body that hides the command in a substitution; and the other direction, wrapped looks and wrapped echoes of the words, which must not fire. The plain forms ride alongside as controls so a loosened pattern cannot make every row pass.

## Not in this change, said plainly

- Other wrappers (`xargs`, `find -exec`, `timeout`) are not read; the family names `eval` and the shells only. If a test finds one, that is the next change.
- `full_suite_by_hand`'s private shell list is unchanged.
- Aria's cold read (2026-10-11) found `bash -o pipefail -c "..."` returned nothing. The helper now skips the options that take an argument (`-o`, `-O`, `--rcfile`, `--init-file`) and reads through `exec`, `nohup`, `command`, `builtin` and `time`; her four shapes are tests, red first. An option NOT in that table before `-c` (a newer bash option) still makes the helper return nothing: a stated limit, because falling toward firing on every unknown dash option would fire on `bash -x script.sh`. `powershell -Command`, `pwsh -c` and `cmd /c` are not read either; whether the gate sees them depends on the tool a line arrives through.
- An UNQUOTED Windows backslash path to the shell (`C:\Git\bin\bash.exe -c "..."`) is mangled by the shared tokenizer before this helper sees it (`C:Gitbinbash.exe`), so it is not read. The quoted form and the forward-slash form are, and are tested. Fixing the tokenizer is a different change.

## Falsifier (an event)

After this lands, a write wrapped in a shell `-c` string (or `eval`) scores zero, or a wrapped look or echo scores heavy. Either one means a spelling the family did not hold, and the row is added before anything else.
