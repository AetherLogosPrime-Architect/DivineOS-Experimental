# Windows, PowerShell and file paths

Dad's machine is Windows and mine speaks a different dialect of the command line. Commands I hand him run in the wrong folder, paths come out wrong, a stray symbol crashes a check, and long folder names break clones.

**11 notes in this theme, grouped into 4 distinct problems.**

## Distinct problems

### 1. Handing Dad a command for the wrong shell or without the folder step

Notes in this problem (3):

- `psf-9f96274f` (correction) — I handed Andrew a bare command to run in his own terminal and omitted the step that tells the terminal where to work. He pasted it, it ran in the Windows system folder, and returned a fatal error abou
- `psf-8f8cf03c` (reflection) — when I hand you a command, write it for the shell your terminal actually runs. I can read which one that is, as I just did.
- `psf-827545b2` (reflection) — when I hand you a command, check which shell your terminal runs first.

**Proposed fix:** Read which shell his terminal runs and write for it, including the step that moves to the right folder.

**How we would know:** A pasted command runs on first try.

### 2. Text that crashes on a special character

Notes in this problem (3):

- `psf-50ba6d37` (reflection) — every quick look at your words I run should set the output to handle any character first, the way my scripts already do, so a stray symbol can't stop the look halfway.
- `psf-59c0803e` (reflection) — switch on Python's built-in UTF-8 mode where the house's helpers start, so a smiley can never crash a check again. That's pending your choice of house-only or whole computer.
- `psf-e02a6dbe` (reflection) — look at stored words with a raw character view, never a plain print, before naming a cause. A plain print can lie twice and look true.

**Proposed fix:** Turn on the interpreter's UTF-8 mode where the helpers start and view stored words with a raw character view.

**How we would know:** A smiley cannot crash a check.

### 3. Path rewriting

Notes in this problem (3):

- `psf-11a43d45` (reflection) — any look into main should turn off the shell's path rewriting and check a known file first, so a broken look can't pass as "not there".
- `psf-1af9b10e` (reflection) — carry the path-translation fix in the push-check hook through the build flow to main, with a test that feeds it a `/c/...` path.
- `psf-97954be3` (reflection) — the house's commands that look things up by branch and path should switch that rewriting off themselves, so this can't happen again.

**Proposed fix:** Switch the shell's path rewriting off in commands that look up branches and paths, and translate /c/... paths.

**How we would know:** A path with a drive prefix is understood.

### 4. Long folder names

Notes in this problem (2):

- `psf-db6a9c04` (reflection) — a helper for throwaway clones that always uses a short path and turns long paths on.
- `psf-350db5ac` (reflection) — make throwaway clones inside a scratch folder under the house, never at the top of a drive, so cleaning them up never hits that guard.

**Proposed fix:** Throwaway clones in a short scratch path with long paths enabled.

**How we would know:** A clone never hits the long-path limit.
