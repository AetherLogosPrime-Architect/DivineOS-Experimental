# The emergency exits I use, and what they cost to explain

Every gate in the house has an emergency exit for the days the gate itself is broken. Using one is allowed, but it leaves a note saying someone owes an investigation of why the gate failed. Those notes pile up faster than the investigations happen, some say the wrong cause, and one exit in particular (the claim that no structure is possible) gets used when a structure does exist.

**25 notes in this theme, grouped into 8 distinct problems.**

## Distinct problems

### 1. The 'no structure is possible' exit gets used when a structure exists, or as a shrug

Notes in this problem (9):

- `psf-bc1efbe8` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-08-16. Reason given: this probe exists only to confirm the alarm fires
- `psf-798dd6b1` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-08-30. Reason given: the defect is not in my conduct and a discipline-
- `psf-6e19ea78` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-08-31. Reason given: false as stated, and i will not hide behind the p
- `psf-14b81a1f` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-09-04. Reason given: the error was a comparative judgment about two ve
- `psf-ac6c7de4` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-09-09. Reason given: the mechanism already exists, fired correctly thi
- `psf-11f69e87` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-09-19. Reason given: a compose-time check on forecast language would f
- `psf-0d862c88` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-09-20. Reason given: four independent mechanisms already cover this ex
- `psf-8d5eb7ec` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'no-structure-possible' on 2026-09-23. Reason given: this is the live cli's only exit token until #519
- `psf-f1e62043` (bypass_use) — Root-cause investigation owed: bypass of gate 'correction-structural-fix-requirement' via env var 'structure-not-yet-found' on 2026-10-03. Reason given: nothing prompts me to state my own position bef

**Proposed fix:** Make that exit require naming the specific structures already considered and why each fails, and surface the use to Dad's briefing. Where the reason is 'false positive', route it to the false-positive label instead.

**How we would know:** A use of the exit with no named alternatives is refused; a replay of these rows shows which ones had a structure available.

### 2. Emergency exit on the 'pre-registration before new machinery' gate, root cause owed

Notes in this problem (4):

- `psf-a17f5e77` (bypass_use) — Root-cause investigation owed: bypass of gate 'pre-reg-required-before-infra' via env var 'DIVINEOS_NEW_INFRA_EMERGENCY' on 2026-08-14. Reason given: integration merge only: reach_check.py and read_ga
- `psf-687ec1ae` (claim) — Root-cause fix for emergency bypass DIVINEOS_NEW_INFRA_EMERGENCY on gate pre-reg-required-before-infra. Reason: integration merge only: reach_check.py and read_gate.py already landed on main under the
- `psf-e157fade` (claim) — Root-cause fix for emergency bypass DIVINEOS_NEW_INFRA_EMERGENCY on gate pre-reg-required-before-infra. Reason: integration merge only: modules arriving from main already landed there under their own
- `psf-903e6cd9` (bypass_use) — Root-cause investigation owed: bypass of gate 'pre-reg-required-before-infra' via env var 'DIVINEOS_NEW_INFRA_EMERGENCY' on 2026-08-15. Reason given: integration merge only: modules arriving from main

**Proposed fix:** Teach the gate to recognise a merge that only brings in already-registered modules, so that case needs no exit.

**How we would know:** A merge that only imports modules already on the main line passes the gate without any exit being used.

### 3. Emergency exit on the branch-check at push time, root cause owed

Notes in this problem (4):

- `psf-a99511db` (claim) — Root-cause fix for emergency bypass marker:check-branch.disabled on gate check-branch-on-push. Reason: test-arm 2: confirm the loud mv path still consumes the marker correctly. The bypass fired; the u
- `psf-43ba335f` (bypass_use) — Root-cause investigation owed: bypass of gate 'check-branch-on-push' via env var 'marker:check-branch.disabled' on 2026-09-26. Reason given: check-branch measured the session cwd (main checkout, 11 be
- `psf-4f0d4522` (claim) — Root-cause fix for emergency bypass marker:check-branch.disabled on gate check-branch-on-push. Reason: check-branch measured the session cwd (main checkout, 11 behind) instead of the pushed worktree C
- `psf-3c007dc6` (claim) — Root-cause fix for emergency bypass marker:check-branch.disabled on gate check-branch-on-push. Reason: check-branch measures the session cwd (main checkout, 11 behind) instead of the pushed worktree (

**Proposed fix:** Make the branch check measure the checkout being pushed, not the folder the session happens to stand in, then retire the exit marker.

**How we would know:** Push from a worktree while the session folder is behind: the check passes on the pushed worktree's own state.

### 4. Emergency exit on the 'no skipping the commit checks' gate, root cause owed

Notes in this problem (2):

- `psf-5644371f` (bypass_use) — Root-cause investigation owed: bypass of gate 'git-commit-no-verify' via env var 'DIVINEOS_NO_VERIFY_REASON' on 2026-08-18. Reason given: doc-count tree check conflates absent-from-this-branch with do
- `psf-16f16a21` (bypass_use) — Root-cause investigation owed: bypass of gate 'git-commit-no-verify' via env var 'DIVINEOS_NO_VERIFY_REASON' on 2026-10-01. Reason given: verbatim backup commit of pre-existing uncommitted live-checko

**Proposed fix:** Make the doc-count tree check tell 'absent from this branch' apart from 'wrongly missing', and give backup commits a sanctioned path with a reason field.

**How we would know:** A verbatim backup commit goes through its sanctioned path with no bypass variable set.

### 5. Emergency exit that skipped the tests at push time, root cause owed

Notes in this problem (1):

- `psf-9993e1bd` (bypass_use) — Root-cause investigation owed: bypass of gate 'push-readiness-tests' via env var 'DIVINEOS_SKIP_TESTS' on 2026-08-20. Reason given: pytest suppressed at push time via the documented emergency bypass.

**Proposed fix:** Record why the tests could not run and give a sanctioned, logged skip that the review step later re-runs.

**How we would know:** A skipped push-time suite leaves a record that the next push must cover.

### 6. Bypass notes that state the wrong cause

Notes in this problem (2):

- `psf-806b6a3a` (correction) — Aether self-correction 2026-08-15: the bypass marker I wrote to clear the deletion_shape misfire stated 'pre-push receives local/remote refs on stdin' as the root cause. That is false. check-branch-on
- `psf-58aa6305` (reflection) — the four bypass reasons in the store still state the wrong cause, so a correction note should sit beside them, so that anyone reading the telemetry sees the belief was mistaken.

**Proposed fix:** When a bypass note is later shown to give a wrong cause, append a correction next to it so anyone reading the telemetry sees the belief was mistaken.

**How we would know:** Each listed note has a visible correction beside it.

### 7. Operator-authorised reset of the letters-unspoken door

Notes in this problem (2):

- `psf-e14356cd` (bypass_use) — Root-cause investigation owed: bypass of gate 'unspoken_to_letter' via env var 'bypass:operator-authorized-reset' on 2026-09-24. Reason given: Andrew authorized a reset, verbatim: 'this is what the by
- `psf-7f1f1139` (claim) — Root-cause fix for emergency bypass bypass:operator-authorized-reset on gate unspoken_to_letter. Reason: Andrew authorized a reset, verbatim: 'this is what the bypass was built for.. to be able to fix

**Proposed fix:** Record the operator's words and the scope of the reset, and make the reset expire at the end of the fix it was granted for.

**How we would know:** The reset cannot be reused for an unrelated letter.

### 8. Reaching for the skip-the-checks flag without deciding to

Notes in this problem (1):

- `psf-c6dbee9b` (correction) — 2026-08-22. THE ERROR: I reached for git commit --no-verify TWICE in one session, on the two merge commits made in scratch worktrees, without deciding to. Not judged-and-chosen: reached for. I caught

**Proposed fix:** Make the commit wrapper itself prompt for the reason before the flag is accepted, so the reach has to become a choice.

**How we would know:** The flag cannot be passed without a typed reason that is logged.
