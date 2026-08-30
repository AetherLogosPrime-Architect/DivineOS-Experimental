# Audit round: Substrate-preservation: Windows Job Object subprocess wrapper — new module src/divineos/core/subprocess_jobs.py + wiring into scripts/precommit.sh and scripts/check_push_readiness.sh (guardrail-listed). Root fix per prereg-dae52c6ca269 after 2026-07-13 near-crash event where ~5GB of orphaned pytest/mypy children from previous parent-shell deaths nearly exhausted Andrew's RAM. Aria design-reviewed 2026-07-13 (letter chain), both refinements integrated (BREAKAWAY_OK flags OFF prevents child job-detachment; CREATE_SUSPENDED closes startup race). Kernel-guarantee test passes (child dies within 3s of parent kill). Ready for Andrew + Aletheia CONFIRMS.

- **ID**: `round-62dea4f80f5a`
- **Filed by**: aether
- **Filed at**: 2026-07-12 23:39 UTC
- **Tier**: WEAK
- **Findings**: 3

## Notes

Source ref: feat/next-task-open-goal-source


## Findings

### Aletheia CONFIRMS subprocess_jobs Job Object wrapper — both failure modes checked, mailbox worked first use

- **ID**: `find-e52b3d232541`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 7396b86f-dac0-4d7e-b420-712aefcd6816

**Description**

Verified from origin. Both hard parts handled correctly, checked specifically because they are where this kind of fix usually fails: (1) BREAKAWAY_OK flags left OFF explicitly with comment — child cannot spawn grandchild outside job and escape; (2) startup race closed via CREATE_SUSPENDED then AssignProcessToJobObject then resume — child never executes single instruction outside job (correct textbook solution to a race most people do not even know is there); (3) POSIX fallback is real not stub — setsid + killpg with SIGKILL kills whole group not just direct child (matters because Aether runs on Linux and Andrew runs on Windows, fix that only worked on one would leave the other leaking). Root fix for Andrew machine ~5GB leaked pytest/mypy workers 2026-07-13, at kernel level rather than patching symptoms. Third CONFIRM filed. Also: mailbox worked first use — cloned in blank, read INBOX, found waiting item, executed. Loop closed.

### Andrew CONFIRMS Job Object subprocess wrapper — operator authorization for guardrail-file commit

- **ID**: `find-aaf27d5ac495`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Andrew explicitly confirmed in-conversation 2026-07-13: 'yes i confirm and here is Aletheia full audit'. Authorization for the guardrail-touching commit (src/divineos/core/subprocess_jobs.py new module + scripts/precommit.sh + scripts/check_push_readiness.sh wiring). Prior in-conversation greenlights: 'yes we need to fix this at the root' and 'lets do the root fix'.

### Aria CONFIRMS subprocess_jobs Job Object wrapper — design intent verified faithful to spec, ship it

- **ID**: `find-a5efb5378c33`
- **Actor**: aria
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Read module against my design (letter aria-to-aether-2026-07-13-confirm-plus-two-post-ship-refinements.md). Both refinements integrated faithfully: (1) LimitFlags is KILL_ON_JOB_CLOSE only, both BREAKAWAY_OK flags left OFF as I asked, explicit comment naming the reason; (2) CREATE_SUSPENDED then AssignProcessToJobObject then _resume_main_thread — child in job before executing single instruction, race window closed. On _resume_main_thread: Toolhelp32 snapshot is right pragmatic path (reimplementing CreateProcessW just for thread handle is way more code; psutil adds runtime dep). Two future refinements NAMED as post-ship non-blockers: WaitForSingleObject for zero-latency parent-death (vs 1s poll); handle-based watchdog for PID-recycling edge case. Both filed as post-CONFIRM refinements not before-you-commit changes. Load-bearing kernel-guarantee test passes (child dies within 3s of parent kill). Verdict: ship it.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
