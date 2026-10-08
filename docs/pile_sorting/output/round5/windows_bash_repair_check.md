# The Windows shell repair: what was not tested, and one command to prove it

*Round five, errand five. 2026-10-08, cloud helper. Nothing was changed.*

**A picture.** I cut a new key at a workbench in the cloud and checked that it turns the lock on the bench. The door it was cut for is in Aria's house on Windows, and I have never stood at that door. This note lists what only that door can tell us, and gives one thing Aria can do there to find out.

## What the repair was

Commit `0cd6cf73` on `cloud/repro-pipe-and-command-shape-guards` (pull request #602). The test helper that runs the pipe-guard hook used to start `bash` by its bare name. On Windows the bare name finds the WSL relay stub, which exits 1 having done nothing, so three controls failed there. The helper now asks the house's finder, `tests._bash_resolver.bash_executable()`, which tries Git Bash first and checks that the shell it picks really prints `ok`, and it still skips when none is found.

## What I did test (Linux, this machine)

- Before and after, the file gives the same result: `4 passed, 9 xfailed`.
- With the expected failures forced to run (`--runxfail`), all nine fail, each with the message it should (for example `'… only prints help but was refused'`).

## What I could not test, exactly

1. **Anything on Windows.** The resolver's Git Bash directories (`C:\Program Files\Git\bin`, `…\usr\bin`) do not exist here, so on this machine the resolver returns plain `bash` and the repair is a no-op. The fix is *proven to leave Linux unchanged*, not proven to cure Windows.
2. **Whether the hook itself runs under Git Bash.** The hook sources `_lib.sh`, resolves a Python with `find_divineos_python`, and runs inline Python. I have not seen any of that run under Git Bash on Windows.
3. **Whether the test's isolated home holds on Windows.** The test sets `HOME`. The hook's shell half uses `${HOME}` but its Python half writes the liveness log through `pathlib.Path.home()` (`.claude/hooks/pipeline-exit-ambiguity.sh:218`), which on Windows reads `USERPROFILE`, not `HOME`. So a Windows run may write to the real profile's `.divineos/hook-liveness.log` instead of the temporary one. That is harmless to the result but would add real lines to a log the house reads. I did not change this.
4. **A thing the old result hid.** Seven of the nine expected failures run the hook through bash; two (the quoted-word ones) do not. Before the repair on Windows, those seven would have shown as "xfailed" even though the hook never ran, because "the hook did not run" is also a failed assertion. So an old Windows `9 xfailed` could not distinguish "fails for the stated reason" from "could not start". After the repair that distinction matters, and only a Windows run can show it.
5. **The path form.** The test hands the shell a Windows-style path as one argument. Other tests in the house do the same and work, but I did not run this one there.

## The one command for Aria

In PowerShell, in the repository root, on the branch (`git fetch origin cloud/repro-pipe-and-command-shape-guards; git switch cloud/repro-pipe-and-command-shape-guards`):

```powershell
python -m pytest tests/pile_repro/test_pipe_and_command_shape_guards_repro.py -p no:cacheprovider -q -rs --runxfail --tb=line 2>&1 | Select-String "passed|failed|skipped|SKIPPED|returncode|WSL|execvpe|Relay|but was refused|only warned|is False"
```

**How to read it, either way:**

| What she sees | What it proves |
|---|---|
| `9 failed, 4 passed`; no `SKIPPED`, `returncode`, `WSL`, `execvpe` or `Relay` text; and the failure lines read like the Linux ones (`… only prints help but was refused`, `… only reads but was refused`, `… was only warned about`, and `assert True is False` for the two quoted-word ones) | **The repair works on Windows:** the bash found really runs the hook, the three controls pass, and the hook-based failures are for their stated reasons. |
| `13 skipped` or `4 skipped` style output | The resolver found no working bash. The repair did its honest thing (skip) but nothing was proved; install Git for Windows or fix the PATH and rerun. |
| Controls fail with `returncode`, `WSL` or `execvpe` text | Bash was found but the hook (or the stub) did not run; the repair did not cure it, and the text says where. |
| The hook-based failures mention `returncode` and the controls also fail | The hook is not starting under Git Bash on Windows (items 2 or 3 above); the problem is deeper than the bash name. |

To see the **old** state on the same machine for comparison, run `git checkout 454ef2a3 -- tests/pile_repro/test_pipe_and_command_shape_guards_repro.py` before the command and `git checkout HEAD -- tests/pile_repro/test_pipe_and_command_shape_guards_repro.py` after it. The three controls should fail there, and the seven hook-based expected failures will appear to "fail" for the wrong reason.

## What this note could not do

- It cannot say what the command prints on Windows; the table is what I expect from reading the code, not an observation.
- It does not say whether item 3 (`HOME` versus `USERPROFILE`) should be fixed; that is a design choice for the test's author.
