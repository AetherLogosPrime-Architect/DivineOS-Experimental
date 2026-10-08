# Is the note still true? The guards that read the shape of a command I type

*Round six, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT EXAMINED** means I did not look at that row this round. It is not the same as UNKNOWN, which means I looked and could not tell.*

A picture: a security guard at a door who reads the label on each package instead of what is inside. I sent the same packages through with controls. The pipe guard still stops the bicycle (a read-only `gh` view with a pipe) while letting the thing it was built for through with a warning. The heredoc door still refuses a safe parcel; the classifier still reads words in quotes as if they were a command.

## Problem 1: A pipe can hide a failed first step (make the safe setting automatic)

16 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-154547cd`, `psf-270cacd0`, `psf-da4234b5`, `psf-9bfef3d3`, `psf-c51e2c61` | **LIVE** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). Controls: `set -o pipefail && git push origin x | tail -2` → silent; `git push origin x | tail -2` → **DENY**. Read-only: `divineos audit list | head` → **warn only**; `git log --oneline | head -2` → **warn only**. The hook neither refuses nor prepends `set -o pipefail` for the read-only shape the rows name. | none for the read-only shape | I did not probe a mutating `divineos`-first pipe, so the half of `154547cd`/`270cacd0` about mutating pipes is not settled. |
| `psf-8ba07b12` | **UNKNOWN** | An incident record (a destroyed working tree). The detector it says was shipped four hours earlier is the hook probed above; the incident itself cannot be re-run. | none | Nothing to run. |
| `psf-3a73b2a6`, `psf-fa3d6899`, `psf-fe69201d`, `psf-671147f4`, `psf-4ce40c81`, `psf-7add1cb1`, `psf-36d365b4`, `psf-eb7a08fc`, `psf-b9e875fd`, `psf-8b4674b4` | **NOT EXAMINED** | I did not look at these rows this round. They ask for `pipefail` in the Bash tool's startup environment, which I did not read (it is the user's shell setup). | none | I did not look at these rows this round. |

## Problem 2: Error output thrown away on long background jobs

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e2ebd0f1` | **LIVE** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). `python big.py 2>/dev/null &` → **silent** (no warning, no refusal). Control: the mutating pipe above is refused, so the hook is working. | none | The row asks that a failing background job print its error by default; I only showed that the hook does not object to discarding it. |

## Problem 3: Help flags, read-only views and display-only tails are treated as writes

6 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5e25d838`, `psf-a339304b`, `psf-f46bab70` | **LIVE** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). `divineos audit submit-round --help | head` → **DENY**. (Control: a bare `--help` is not in the row's complaint; a piped one is refused as a write.) | none | I probed the piped form only. `f46bab70` points at a draft I did not open. |
| `psf-aefcd48c`, `psf-a06dd5cc` | **LIVE** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). `gh pr view 12 | head` → **DENY**; `gh pr list --json number | head` → **DENY**. A trailing `head` on a read-only `gh pr` view is therefore still refused. Controls: read-only `git log … | head -2` → warn only. | none |  |
| `psf-b825721a` | **STALE** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). The refusal text for `gh pr view 12 | head` offers the unpiped command (`offers the unpiped command = True`); for `git log … | head -2` and `… | grep fix` it also names `scripts/look.sh`. So the refusal no longer teaches nothing. | none | Whether it also offers a pager-safe form such as `--jq` is not met: the text does not mention `--jq`. |

## Problem 4: A refused write is followed by a command that depends on it

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ed362492`, `psf-85ce8fe7`, `psf-6ea35232`, `psf-00e8d835` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 5: 'Found nothing' and 'the command broke' look the same

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e4643797`, `psf-7cca98df` | **STALE** | `scripts/look.sh` exists and is three-state (found / found nothing / could not look); the read-only pipe warning points at it (`mentions look.sh = True`). | none found | It is advisory, I have to choose to run it, and the `--strict` flavour has the fault in problem 10 below. |
| `psf-76c8d3a3`, `psf-cf85ca15`, `psf-928387ca`, `psf-35093500`, `psf-c7e05e05`, `psf-7f632dfa` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 6: The heredoc guard looks in the wrong place

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-04371056`, `psf-64725314`, `psf-b43c7d23` | **LIVE** | `heredoc_escape_check.should_refuse` (`probe_heredoc.py`): a body holding a backslash escape plus redirect-shaped text, with **no redirect on the opener line** → refuse **True**; the same body without the escape → False (control); redirect on the opener line plus an escape → True (control). Quoted delimiter `<<'EOF'` and unquoted `<<EOF` with the same body → **both refused** (the row says only the unquoted kind lets the shell eat an escape). | the door's own tests (contested by this very behaviour) | I did not read the door's tests to see which of them pin the refusal. |

## Problem 7: A plain folder change is refused

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c735fbc0` | **UNKNOWN** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). `cd /tmp && git log --oneline | head -2` → warn only, not refused. The row says the guard refuses its own remedy, which needs a mutating command after the `cd`; I did not probe that. | none | One probe, wrong shape for the claim. |

## Problem 8: Guards judge words inside quotes instead of what the command runs

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9e26ea08`, `psf-bf4b5ebb`, `psf-b1d5c766`, `psf-260d0789`, `psf-9c6f5a9c` | **LIVE** | `gravity_classifier.score_substrate_modification` on main: `git log --grep "divineos prereg"` → `council_required=True`, feature `substrate-write-cli`; `echo "divineos audit list"` → **True**. Controls: `bash -c "divineos prereg file …"` → True (real command); plain `git log --oneline` → False. Words inside a quoted string still trip it. | PR #602 (draft) reproduces it |  |
| `psf-d22dc64a` | **UNKNOWN** | Two of its three asks are met: `git -C /tmp/x commit -m x` scores the same as `git commit` (feature `git-commit`), and read-only `git log` is free. 'Read every clause in a line' was not probed. | none |  |
| `psf-6a2f98fd`, `psf-40b1c95b`, `psf-46e4ae1f` | **NOT EXAMINED** | I did not look at these rows this round. (`46e4ae1f` concerns the build gate and full paths; my one full-path probe was on the classifier, which is a different gate.) | none | I did not look at these rows this round. |

## Problem 9: Output trimming is a habit I reach the pipe for

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e922ee5c`, `psf-3b5c70d8` | **UNKNOWN** | `scripts/look.sh` exists, but I did not check that it shows a command's tail, which is what the rows ask for. | none | Not run. |
| `psf-c862c8e3` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 10: grep pipes that blur 'no match' and 'command broke'

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5f682720` | **LIVE** | Probe: `pipeline-exit-ambiguity.sh` fed a tool-call JSON in a scratch home (`probe_pipe_theme.py`). Half met: with `git log --oneline | grep fix` the warning mentions `scripts/look.sh` (True). Half not met: `look.sh --strict` collapses a grep that finds nothing into CANNOT-LOOK, so 'no match' and 'command broke' still come out as one state in the strict form the row asks the hook to point to. | none | The `--strict` behaviour is from the round-six read and run of `look.sh` in a scratch folder. |

