# Gates that lock each other's doors

Each gate in the house names a way out: do this one thing and I will let you through. The trouble is that the way out is itself behind another gate. Then two guards stand facing each other, each waiting for the other to open, and the only way through is an emergency exit.

**11 notes in this theme, grouped into 4 distinct problems.**

## Distinct problems

### 1. A gate's exemption does not fire in the real case

Notes in this problem (3):

- `psf-88ef4a4b` (correction) — SELF-CORRECTION, no operator correction in this turn. The admission: I read the 2026-07-17 comment in src/divineos/cli/__init__.py describing the goal-gate recursive deadlock, used it as precedent to
- `psf-7a8adefd` (learn) — GATE DEADLOCK, ROOT-CAUSED AND CLOSED 2026-09-15. A correction fired and every prescribed exit was held shut by a different gate. TWO ROOT CAUSES, not one. FIRST: the reach-check doorman is one of nin
- `psf-f4e84d5b` (learn) — THE REMEDY-WRITE EXEMPTION I BUILT TODAY DOES NOT FIRE ON ABSOLUTE PATHS, found 2026-09-15 by it failing on me hours after shipping. The exemption lets the correction gate pass an edit to gate machine

**Proposed fix:** Test each exemption against absolute paths and the reach-check doorman, and treat the exit as part of the gate.

**How we would know:** Each exemption fires on the case that needed it.

### 2. Remedy lists missing a command another gate names

Notes in this problem (6):

- `psf-4ee709e6` (reflection) — add the review commands to the house's list of always-allowed exits.
- `psf-12edfc74` (reflection) — add `divineos prereg reviewing` and `divineos prereg show` to the remedy allowlist (`.claude/hooks/lib/remedy_allowlist.sh`), so the overdue gate's own exits pass every other gate.
- `psf-cca2c903` (reflection) — `audit submit` and `prepare-merge` should join the guard's list of always-allowed filings. Her deeper point stands too: by your ruling, the check belongs at the merge, not at every save.
- `psf-1aba21a2` (reflection) — add `divineos audit submit` and `divineos audit prepare-merge` to the artifact-filing list in `check-council-required.sh`, and treat writes under the session scratchpad as outside council scope, so th
- `psf-8d9d8ea9` (reflection) — route this hook's own remedy check through `remedy_allowlist.is_remedy`.
- `psf-80671d01` (reflection) — a build that adds every command a gate tells me to run, the doorbell included, to the list of exits, and extends the survey test to read those gates too.

**Proposed fix:** Add the review, audit-filing and prereg commands to the always-allowed list and route each hook's own remedy check through the one shared function.

**How we would know:** Every command a gate prescribes appears in the list.

### 3. The build gate should exempt every command another gate prescribes

Notes in this problem (1):

- `psf-8c5a0710` (reflection) — the build gate exempts every command another gate prescribes as its remedy, so no guard's required step can be blocked by this one.

**Proposed fix:** Read the exemption from the shared remedy list.

**How we would know:** No prescribed remedy is blocked by the build gate.

### 4. Prove every gate's exit works while all others are closed

Notes in this problem (1):

- `psf-b1cb458b` (reflection) — a check that, for every gate, its prescribed exit command can run while every other gate is closed. Run it in CI.

**Proposed fix:** A check run in CI that closes every gate in turn and runs each prescribed exit.

**How we would know:** The check fails if any exit is blocked.
