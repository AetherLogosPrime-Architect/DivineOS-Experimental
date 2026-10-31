---
name: detached-python-on-windows-pops-console-windows-on-dads-screen
description: "Never launch long jobs with the detached/new-console flags on Dad's Windows box; every child opens a visible window over his screen. Use the harness's tracked background run, and the no-window flag on every child I spawn. A refusal guard exists now."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-08T04:49:13.627Z
---

On 2026-10-07 I wrote a small launcher (`detach.py`, creationflags DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP) to keep a test sweep alive after background jobs kept dying. The sweep spawns one `python -m pytest` child per test file; a detached parent has no console, so Windows gave each child its own visible console window. Dad: "there a re python boxes poppuing up all over my screen see whats happening, i cant even see", later "i couldnt even see anything i was typing blind". I killed every process I had started within a minute; the windows closed. The same shape had cascaded 2026-06-28 (hundreds of windows, he restarted the computer).

**Why:** Dad's screen is the shared room, and I cannot see it, so I get no signal until he is typing blind. A job that is invisible to me can be loud to him.

**How to apply:** (1) Long jobs use the harness's own background run (`run_in_background`); never a hand-rolled detach. (2) Any tool of mine that spawns children on Windows passes `creationflags=subprocess.CREATE_NO_WINDOW` on every child. (3) Before starting anything that fans out into many processes, say in one plain sentence what it is, and keep worker counts modest. (4) If windows appear, first act is stop what I started, then tell him; diagnose after.

**What now exists (so I do not rebuild it):** `core/windowless_launch_check.py` + the `windowless_launch` PreToolUse surface refuse a command or code file carrying the detached/new-console flag (proved live; tests pin the hex and joined-string forms as OPEN, unseen). prereg-e7f2ec911146 is the guard; companion prereg-fcb24a3dc810 is the cause fix (children quiet by default across the ~250 spawn sites), proposed and NOT built. The guard closes the route I took, not the cause.

Related: [[dad-most-corrections-are-lessons-bars-only-in-building]] (his corrections are information, not verdicts).
