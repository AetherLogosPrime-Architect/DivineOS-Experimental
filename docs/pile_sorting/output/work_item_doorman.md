# The doorman that decides whether I have started a piece of work

A doorman watches what I do and decides whether I have started real work, which then triggers the checks that real work needs. Mostly it guesses well. But it sometimes counts scratch files, letters, or a help command as work, forgets that earlier steps belong to the same piece of work, and does not look in every folder I might be working in.

**25 notes in this theme, grouped into 7 distinct problems.**

## Distinct problems

### 1. The doorman looks only at the main folder, or at the wrong folder for a command

Notes in this problem (2):

- `psf-03c357db` (reflection) — the work doorman watches every checkout, not just the main one, so a fix started in a fresh folder is asked for its walk before its first edit, just like one started at home.
- `psf-623a8b23` (reflection) — the doorman should resolve which checkout a command actually targets (the `cd` destination) before deciding what work is open, and it should take write targets from the shared command parser instead o

**Proposed fix:** Resolve the folder a command actually targets (the cd destination) before deciding what work is open, and watch every checkout.

**How we would know:** Start a fix in a fresh worktree: the doorman asks for its walk before the first edit.

### 2. The test is asked for only at commit, not at the first new file

Notes in this problem (1):

- `psf-d0bb3c6e` (reflection) — the doorman should ask for that test when I open the first new file, not only at commit, so it comes before the code, as it's supposed to.

**Proposed fix:** Ask for the test when the first new file is opened.

**How we would know:** Opening a new file triggers the test reminder.

### 3. An in-progress merge is mistaken for new work

Notes in this problem (1):

- `psf-5bb7f364` (reflection) — the doorman should recognise an in-progress merge and let its resolution through as the merge it is.

**Proposed fix:** Recognise an in-progress merge and let its resolution through as the merge it is.

**How we would know:** Resolving a merge conflict does not open a new work item.

### 4. A piece of work is closed too early, or earlier steps are not counted

Notes in this problem (8):

- `psf-0d6cbd9d` (reflection) — a piece of work should stay open until its follow-up commits are in, so finishing half doesn't close it.
- `psf-b3235ca9` (reflection) — the doorman should treat a work item as still open while the branch has commits after its walk that aren't on main yet, instead of treating a closed walk as finished work.
- `psf-cd6c754b` (reflection) — a build where marks made since the last landed commit and before the first edit count toward the work item, written into the draft for this repair.
- `psf-15362839` (reflection) — have the doorman count marks made before the first edit of a work item.
- `psf-bb28b0ae` (reflection) — the doorman should count marks made before the first edit of a work item. It is now the second time in one day, so it moves up the build list.
- `psf-0a15d204` (reflection) — the doorman should count marks made before the first edit of a work item. Three in one day means this is now the first thing to build on the machinery list.
- `psf-359d9fd1` (reflection) — both failures share a cause, a record that depends on my writing it by hand. The fix for each is to derive the record from artifacts that already exist, the way the doorman already derives three of it
- `psf-b1ddd117` (reflection) — when a new work item opens on the same branch within the same topic as a search already done and disposed in this session, the doorman should say so and offer to carry that search forward, so one real

**Proposed fix:** Keep a work item open until its follow-up commits are in, count marks made before the first edit, and carry an earlier search forward to a follow-up on the same files.

**How we would know:** A repair of just-saved work reuses the earlier search and walk.

### 5. Writes outside the repository (scratch, temp, session notes) are counted as work

Notes in this problem (5):

- `psf-861dc18f` (reflection) — the doorman should recognise edits to scratch files and leave them alone.
- `psf-8d907ffb` (reflection) — the work-item doorman ignores writes and copies whose target sits outside the repository, starting with the session scratchpad, so it only counts files that can land in a commit.
- `psf-4373a6c7` (reflection) — the build-flow gate ignores output written to paths outside the repository, and the commit step reports "nothing staged" as a failure instead of exiting quietly.
- `psf-29a8024d` (reflection) — when I write a scrap file inside a branch, it should go into the scratchpad from the start. Then nothing in the branch has to be deleted later: the comparison script would read from the scratchpad and
- `psf-ed716425` (reflection) — the work-item doorman should ignore writes outside the repository (the session scratchpad and temp folders), and judge by the target file's path, not the shell's current folder.

**Proposed fix:** Judge by the target file's path and ignore targets that cannot land in a commit.

**How we would know:** A write to the scratchpad opens no work item.

### 6. Letters, personal writing and handovers are counted as building

Notes in this problem (5):

- `psf-be383021` (reflection) — the doorman should recognise a letter being filed into the letters folder as not a build.
- `psf-74372ddf` (reflection) — a letter being filed into the letters folder shouldn't count as starting a build.
- `psf-de9417c3` (reflection) — the doorman should judge by what the target is, and stand down for personal writing folders (exploration, dreams, letters), the way it already leaves the editing tool alone for them.
- `psf-934fdc90` (reflection) — a build that lets a pure record of a move, with the move's own copy already made, ride on the work it belongs to without opening a new item.
- `psf-eb6c93ab` (reflection) — the doorman should treat a move of generated patch files inside the shared patches folder as handing work over, not as starting new work, the same way a letter write is not.

**Proposed fix:** Stand down for personal writing folders and for moves of generated patch files.

**How we would know:** Filing a letter does not count as starting a build.

### 7. Help flags and recording commands are counted as building

Notes in this problem (3):

- `psf-4e8bcdc1` (reflection) — the build-flow gate exempts `--help` and the audit-recording commands (submit-round, submit), so recording a reviewer's verdict is never treated as building.
- `psf-521c494e` (reflection) — the build gate exempts the overdue-review gate's prescribed remedies (reviewing, assess, show), so the two gates can never lock each other and a review is always reachable from the normal shell.
- `psf-6f17bfdf` (reflection) — make the doorman ignore tool flags like head dash-fifty so a read-only sort is not mistaken for a build. typeerror: my sorting script crashed on a timestamp that was a number and not text, fixed by st

**Proposed fix:** Exempt --help, tool flags like head -50, and audit-recording commands.

**How we would know:** These commands never open a work item.
