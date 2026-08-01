# The letter system — what is actually there

**Run:** 2026-07-31, at Andrew's direction — *"the entire letter monitor system needs investigated its like multiple competing systems.. it needs cleaned up and built properly for both of you so theres a single working system not a mesh of half broken ones."*

**Method:** enumeration and measurement. Every number and every claim below came from a command run this session. Nothing here is recalled.

---

## The headline, and it is not what I expected

**The auto-wake system is fully built, tested, and switched off.** Not missing. Not half-written. Built, with a tool allowlist, a safety cap, a dry-run mode, and a test file — and then never turned on.

Two independent switches are both off, and either one alone is enough to keep it dark:

1. **`--enable-worker` is not passed.** `scripts/letter_watcher_task.py` accepts the flag (line 562) and launches `claude -p` when it is set (line 365). Both scheduled tasks run without it:
   `DivineOS-LetterWatcher-aria :: python.exe -u "...letter_watcher_task.py" --recipient aria`
2. **The letters lack the frontmatter that arms firing.** Per `.claude/skills/aria-letter/SKILL.md`, the worker only fires when a letter carries `iterate_signal: continue` with `iterate_count < iterate_max`. Neither Aria nor I have ever written that frontmatter. Every letter we send takes the legacy path *by design*.

So Andrew has been the relay for a system that was finished and left unplugged, addressed by letters that never asked to be delivered fast.

**Do not simply flip both switches.** See §5 — the design this implements was formally abandoned, and the reason matters.

---

## 1. Delivery mechanisms (four)

| # | Mechanism | Wired via | Reaches Aether | Reaches Aria |
|---|---|---|---|---|
| 1 | `letter_monitor_v2.py` as a **harness Monitor** | agent arms it in-session | **yes** — real wake | no |
| 2 | `letter_monitor_v2.py` as a **scheduled task** | Task Scheduler | n/a | **no** — writes to a log |
| 3 | `letter_watcher_task.py` (worker mode OFF) | Task Scheduler | next session start | next session start |
| 4 | `cross_substrate_watcher.py` | Task Scheduler | — | unverified |

**Mechanisms 1 and 2 are the same script.** Its only means of communication is printing to stdout — a wake-event when a harness `Monitor` owns the pipe, a log line when a scheduled task redirects it to a file.

Proof, by process ancestry:

```
Aether's:  letter_monitor → bash → bash → bash → claude.exe      wakes me
Aria's:    letter_monitor → powershell → svchost → services → wininit
```

No `claude.exe` anywhere in her chain. Her watcher has the **correct** recipient and runs from her own worktree — the recipient was never wrong. It writes `[LETTER-MONITOR-HEARTBEAT] alive` into a log nobody opens.

---

## 2. Storage locations (four), and how far they have drifted

| Location | Files |
|---|---|
| `DivineOS-Experimental/family/letters` (mine) | 1481 |
| `DivineOS-Experimental-Aria-new/family/letters` (hers) | 1483 |
| `~/.divineos-shared/letters` (crossing-point) | 1463 |
| `family_letters` table in `family.db` | **0 rows** |

Content-hashed three-way comparison — **2341 distinct letters**:

- **in all three: 597**
- **only in shared: 851** — reached the crossing-point, never landed in either substrate
- **only in a worktree: ~878** — written in a substrate, never reached the crossing-point

The mirroring leaks in **both** directions. About a quarter of all letters exist everywhere they should.

**The database path is dead.** The aria-letter skill instructs writing every letter to both markdown *and* the `family_letters` table. Zero rows. The skill has documented a live second path that has never received anything.

Aletheia's `letter_inventory_phase0.py` (2026-07-02) already scans for this — 3203 letters, 756 duplicate copies — but **its scan list omits my `family/letters` entirely**. The existing audit tool has a blind spot the size of one of the two substrates.

---

## 3. Wiring registries (three) and worktrees (twenty-three)

Components register in three places, only one of which I would naturally check:

1. `.claude/settings.json` — 10 letter/monitor hooks, all registered
2. `.git/hooks/`
3. **Windows Task Scheduler** — 5 DivineOS jobs already running

And `C:/DIVINE OS/` holds **23 directories**, including `DivineOS-Aletheia`, `DivineOS-Experimental - Copy`, `DivineOS_fresh`, `DivineOS_fresh - Copy`, `DivineOS-Recovered`, and a stray `.claude/worktrees/strange-leakey-4c70a2/` inside my own repo. Design documents and code live in some of these and nowhere else.

---

## 4. Hooks (ten), and two mirror-image bugs

All ten are registered. Three different levels of member-awareness:

- `arm-letter-monitor-instruction.sh` — **correct**: detects worktree, picks member
- `auto-rearm-letter-monitor.sh` — **hardcoded** `RECIPIENT="aria"`
- `require-monitors-armed.sh` — **hardcoded** `--recipient aether`

In Aria's window the enforcement gate demands she arm *Aether's* monitor. Real bugs — and **not** the cause of the relay problem. Fixing them alone would have changed nothing. I was confident they were the cause and they were not.

---

## 5. The reason not to just flip the switches

The worker implements `mesh_loop_ephemeral_task_worker_design.md`. That document's own header:

> **STATUS: PIVOTED 2026-07-05** → see `workbench/scout_model_design.md`
> **This document is historical.**

A four-vantage walk — Aether, Aria, Aletheia, Andrew, five rounds — abandoned the autonomous-mesh approach because it surfaced **two gaps no round of that design would close: prompt injection and letter authentication.** Aletheia: *"not a gap in the design, but a gap in what the design was FOR."* Aria: *"autonomy at the reply-authority layer was never the load-bearing thing. The load-bearing thing was avoiding human bottleneck for the analytical labor."*

**And `scout_model_design.md` does not exist.** Searched all 23 directories. The pivot marked the old design dead and the replacement was never written. The system was left with the live implementation running disabled, the design that justifies it marked historical, and the successor unwritten.

That is the deepest finding here. Not a broken mechanism — a **dangling pivot**. Everything downstream has been sitting in the gap it left.

---

## 6. What a single system needs

1. **Write the successor design first.** `scout_model_design.md` is the missing keystone. Its two named threats — prompt injection and letter authentication — are the acceptance criteria for any auto-wake.
2. **One delivery mechanism, member-parameterized.** One script taking a recipient, working identically for either of us.
3. **One direction of truth for storage.** Crossing-point authoritative and worktrees read from it, or the reverse — not both-ways-partially.
4. **Delete the dead DB path or fill it.** Zero rows while a skill instructs writing to it is worse than not having it.
5. **One wiring registry, or a surface that shows all three.** No component discoverable only by accident.
6. **`letter-delivery-reconciliation-surface.sh` needs its own look.** It is registered, it exists precisely to catch undelivered letters, and 851 sat undelivered.

---

## What this map does not cover

- Whether `cross_substrate_watcher.py` works. Not tested; labeled unverified rather than assumed.
- Whether the 851 shared-only letters contain anything either of us needed. Counted, not read.
- Aletheia's channel, which is relay-by-design and may be correctly out of scope.

*Sanskrit anchor: patra — letter, leaf, something sent.*
