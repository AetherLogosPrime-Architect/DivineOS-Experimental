# Pre-registration: Windows Job Object subprocess wrapper (src/divineos/core/subprocess_jobs.py) prevents orphan child process accumulation on parent-death across all Windows shutdown paths (SIGKILL, crash, harness timeout, user close). Uses CreateJobObject + SetInformationJobObject with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE and both BREAKAWAY_OK flags OFF. CREATE_SUSPENDED + AssignProcessToJobObject + ResumeThread eliminates the startup race. Integrates into precommit.sh (mypy invocation) and check_push_readiness.sh (pytest invocations, all three code paths). Aria design-reviewed 2026-07-13, both refinements integrated.

- **ID**: `prereg-dae52c6ca269`
- **Filed by**: agent
- **Filed at**: 2026-07-12 23:28 UTC
- **Review at**: 2026-08-11 23:28 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Wrapping heavy subprocess spawns in Windows Job Object eliminates orphan-child-process accumulation that nearly crashed Andrew's machine 2026-07-13. When the parent (bash, Claude Code, Python wrapper) dies for any reason, the OS itself kills every process in the job. No trap logic dependency, no signal propagation dependency, no PID tracking. Kernel guarantee.

## Success criterion

Test harness spawns wrapped pytest under wrapper, kills the wrapper parent forcibly (Stop-Process -Force), asserts no residual pytest processes remain 5s after parent death. Repeated across 20 iterations with zero orphans. Same test on mypy. In production over 30 days, Windows Task Manager python.exe process count stays flat during normal precommit+push cycles (no baseline drift).

## Falsifier

Killing the wrapper parent leaves child pytest or mypy processes running after 5s — proves Job Object breakaway is happening (child detached) or the Windows Job semantics diverge from MS docs in this environment. OR: 30-day baseline shows Python process count creeping up across sessions despite the wrapper being live — proves some spawn path is bypassing the wrapper. Either falsifier fires: file follow-up Class 2 without shame and iterate the design.
