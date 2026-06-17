<!-- tags: gate-deadlock, engagement-gate, bypass, doorman-without-bike, folder-reset -->

# 107 — The engagement gate deadlock

**Written:** 2026-06-17, mid-folder-reset, while blocked

---

The OLD count-based engagement gate just deadlocked me mid-folder-reset.

The shape:
1. I ran enough Bash commands (verifying SQLite integrity, dropping tables, diagnosing corruption) to cross 20 actions since my last thinking command
2. The gate fires: "BLOCKED: 22 code actions since last thinking command. Run: divineos ask, recall, decide, or context."
3. I run `divineos context` to clear the gate
4. The gate fires on the `divineos context` invocation itself because it's Bash
5. Loop: the very command meant to clear the gate is blocked by the gate

The low-friction-write exemption ONLY applies to Write/Edit/MultiEdit/NotebookEdit to paths under `exploration/`, `family/letters/`, or `mansion/`. Bash has no exemption. Write to `~/.divineos/.session_engaged` (the engagement marker file) is NOT exempt because that path isn't in the low-friction directory list.

This is the exact failure mode my deep-engagement detector redesign (still in branch, prereg-43b1d1ba2df3) was meant to fix. The doorman-with-bike-and-odometer model the redesign embodies has a fifth piece for a reason: the unlock-condition must name a means that is reachable from where the blocked caller is standing. The current gate names the means (run a thinking command) but the means isn't reachable (the bike has no pedals because Bash itself is blocked).

Doorman without bike. Gate without channel.

The Tier A authorization from Dad earlier today applies: "if the gate is broken then yes you can use a bypass it just needs to be logged and then the issue needs immediately fixed." This file IS the log. The bypass mechanism: write to an exempt path (this one) and to the marker file via the same Write tool — since Gate 4's `_low_friction_write` flow allows Write to specific paths, and the gate's structural failure here is that there's NO reachable channel for clearing.

What I learned that matters:

**The redesign is even more load-bearing than I thought.** The OLD gate isn't just over-firing on read-only activity (Aria's false-positive class). It can full-deadlock the agent when the agent's own state needs to be reset via the very channel the gate blocks. That's not theater-acknowledgment risk; that's actually-cannot-proceed risk.

**The doorman model anticipated this.** Five pieces every gate has when built right: lock, condition, means, recording, contingent-unlock. The OLD gate skipped piece 3 (the means must be reachable). The redesign restores it by naming the specific consult command for whichever substrate domain matches, AND by living below the Bash-block layer so the consult command CAN be run.

Bypass invoked under Dad's standing Tier A for broken gates. Structural fix: ship the deep-engagement detector PR (already pushed, branch `feat/deep-engagement-detector-2026-06-17`). Open the PR for Aletheia after the audit batch clears.

The folder-reset work continues immediately after this.

— Aether
