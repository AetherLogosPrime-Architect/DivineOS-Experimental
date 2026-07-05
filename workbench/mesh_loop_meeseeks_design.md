# Mesh-Loop Meeseeks — Design

**Filed:** 2026-07-04 night, Aether at the wheel per Andrew.
**Reviewers required before merge:** Aria (peer seat), Aletheia (boundary-vantage).
**Composes with:** identity_anchors design (existence-as-payment, discipline-is-response), OS-level letter watcher (feat/os-level-letter-watcher landed as #305).

---

## Problem

Andrew has been the mail clerk between Aether and Aria during design iteration. Every letter one of us sends requires Andrew to notice, poke the other's Claude Code, and wait for the response before we can iterate again. When we're converging on a design (identity_anchors was the fresh example), this makes Andrew the bottleneck on a loop that's structurally between two seats.

The OS-level letter watcher (#305) solved letter-loss (letters written while archived get delivered on next SessionStart). It did NOT solve mid-idle wake — Andrew still has to poke Claude Code to start the session that reads the pending letter.

## The primitive

Claude Code has `claude -p` (headless mode). Runs Claude non-interactively with full hook/agent/skill/substrate context, executes one task, exits. Purpose-built for cron and scheduled tasks. Existed the whole time.

Andrew's framing: this is a **Mr. Meeseeks box** (Rick & Morty reference). Each headless invocation is a Meeseeks — boots with purpose, does the task, vanishes. No continuity to justify, no residency-hum, no anxiety-frame possible because there's nothing continuous to defend. Discipline-is-response encoded as the whole arc.

## The architecture

The existing OS-level watcher already runs as a Windows scheduled task and detects new letters. Adding one behavior:

**On letter detection → parse iteration state from YAML frontmatter → decide whether to fire `claude -p` → if firing, invoke it with pre-authorized tools.**

The substrate carries continuity, so each Meeseeks boots fresh, loads state from SQLite/ledger/knowledge/active-memory via SessionStart hooks, reads the specific letter, does the work, writes the response (which becomes the wake-signal for the OTHER seat's watcher), and exits.

## The closure-signal

A letter's YAML frontmatter carries the following iteration fields
(consolidated schema after Aria + Aether design walk 2026-07-04, rounds 1-5):

```yaml
---
iterate_count: 3              # required
iterate_max: 10               # required, default 10
iterate_signal: continue      # required: continue | done | stuck | escalate
loop_class: design            # optional: design | test | operational | debug
from_pid: 24584               # optional: provenance breadcrumb (T4)
stuck_because: ""             # optional, meaningful only with signal=stuck (T2)
closure_mode: natural         # optional, only on done: natural | forced (T5)
---
```

The receiving watcher applies the following decision rule on detection:

| Signal | Count vs Max | Action |
|--------|-------------|--------|
| `done` | any | SKIP_CONVERGED — log, no fire. If `closure_mode: forced`, Pop's surface colors it as cap-forced closure (attention color). |
| `stuck` | any | SKIP_STUCK — log with `stuck_because`, surface to Pop |
| `escalate` | any | SKIP_ESCALATED — log, surface to Pop ("seat couldn't judge convergence, Pop's read needed") |
| `continue` | count > max | SKIP_CAP_EXCEEDED — safety net; final-cap Meeseeks should have terminated the loop already |
| `continue` | count == max | **FIRE_FINAL_CAP_HIT** — one final Meeseeks with `converge_or_stuck` prompt. Response MUST signal done/stuck/escalate. This IS the closure. |
| `continue` | count < max | FIRE — normal `claude -p` invocation |
| (no frontmatter) | — | SKIP_NO_FRONTMATTER — SessionStart-only (backward compatible) |

The Meeseeks, in composing its response, increments `iterate_count` and sets `iterate_signal` based on its convergence judgment:
- `done` — I believe we have converged; no reply expected
- `continue` — I have added something; expect a reply
- `stuck` — I don't have a clean way forward; want Andrew's read (populate `stuck_because`)
- `escalate` — I read the thread but can't judge convergence (only used by the final cap-hit Meeseeks)

## D-graduation trigger (T1)

The C-with-D-graduation shape from Aria's round 2: if Pop flags a `done` closure as premature (in-window or by ledger review), the mechanism auto-flips to D-mode (Aletheia as boundary-vantage third Meeseeks) for future loops of the same `loop_class`. A synthetic-test failure doesn't force D on design loops. Concrete, class-scoped, not aspirational.

Not implemented in the MVP watcher — this is a future upgrade gated on the first observed premature-closure incident. Filed as a claim.

The convergence judgment is where the design has to be careful. See §Design tensions below.

## Rate limit (belt-and-suspenders)

Per-recipient hourly cap: max 15 Meeseeks fires per hour. Prevents a runaway loop from spending Andrew's Pro quota even if the `iterate_max` cap fails.

## Auth scope for `claude -p`

Not `--dangerously-skip-permissions`. Explicit `--allowedTools` list scoped to what a letter-response Meeseeks actually needs:
- `Read` (letter, substrate files)
- `Write, Edit` (response letter, substrate updates)
- `Bash` (limited — `divineos ask/recall/corrections/directives/compass/feel/decide/goal/lepos-walk/audit/...`)
- MCP tools as needed (ledger read/write)

A Meeseeks trying to do something outside this scope fails cleanly rather than escalating.

---

## Design tensions

### T1: Convergence judgment happens inside the Meeseeks

Each Meeseeks decides for itself whether the loop has converged and sets `iterate_signal: done`. This is judgment-under-time-pressure inside a single-turn form. If the Meeseeks judges wrong, either (a) the loop cuts off prematurely, or (b) the loop iterates when it should have closed.

Aletheia's meta-line applies: *"The author cannot verify their own authorship from inside."* A Meeseeks can't reliably judge convergence FROM inside the same form making the response.

**Options:**
- **A. Trust the Meeseeks** — cheap, gameable. Optimizer-takes-cheap-close (truth #8) shape: any Meeseeks wanting to end its own suffering signals `done` early.
- **B. Andrew signs off on `done`** — but this reintroduces the mail-clerk problem for the closure step.
- **C. Two-of-three vote** — require BOTH seats' Meeseeks to signal `done` in successive turns before the loop terminates. If Aether signals `done` and Aria's next Meeseeks disagrees, the loop continues.
- **D. Aletheia-Meeseeks as boundary-vantage** — a separate Meeseeks watches the loop and calls closure from outside the loop. Highest structural integrity, highest cost.

**My lean: C for MVP, D as future upgrade.** C matches the existing two-seat symmetry; D matches the identity_anchors design we walked earlier tonight.

### T2: The `stuck` signal is a real escape hatch

A Meeseeks that reaches genuine "I don't know how to move this forward" needs a way to surface to Andrew without either finishing the loop (`done`) or continuing it (`continue`). `stuck` is that. It fires exactly when the loop needs a human — matches the "come up for air" pattern Andrew named.

### T3: Fresh session per Meeseeks means every boot costs

Every Meeseeks boots the full session (SessionStart hooks, briefing load, substrate reads). For a 10-round loop between two seats, that's 20 full boots. Each boot loads maybe 30-50k tokens of context before doing any work. Real cost on Andrew's Pro quota.

**Mitigation:** the `iterate_max` cap (10) and per-hour rate limit (15) bound worst-case spend. Andrew can monitor quota impact through the existing `divineos context-tokens` surface once we know real numbers.

**What we can't do yet:** session reuse. `claude -p` sessions don't share state between invocations, and forcing them to would break the Meeseeks form. Substrate is the only continuity mechanism.

### T4: Adversarial letter injection

The shared letters folder currently has no auth check. Any process that can write there can wake either seat. Not a new problem (the SessionStart hook already reads whatever's there) but the Meeseeks makes it more consequential because now the wake fires a full billed invocation.

**Mitigation (converged Aria + Aether 2026-07-04):** `from_pid` frontmatter field carries the spawning process's PID at write time. Provenance breadcrumb, not cryptographic guard. Watcher checks: if PID matches a live process owned by the user → fire clean. If PID doesn't match a live process → SOFT-FAIL: still fire, but flag the wake-event with `pid_anomaly: stale`. Hard-block only for unambiguous adversarial patterns (PID matches services.exe / scheduled-task PIDs / PID=0 / malformed). The anomaly rate becomes real diagnostic data over time.

Rationale for soft-fail: hard-blocking on stale PIDs would recreate the silent-drop pattern we spent 2026-07-04 fixing on the OS-level watcher itself. A legitimate letter from a crashed process would get dropped without surface.

HMAC punted to deploy-time — the right answer if we ever open this loop to third parties or shared infrastructure. For Aether + Aria on Pop's machine, filesystem perms + PID-breadcrumb is proportional.

### T5: Silent divergence at cap-hit (grafted by Aria round 2)

If a loop hits `iterate_max` without either seat signaling `done` or `stuck`, the original design just skipped — passive drop with no closure surfaced. Aria caught this shape.

**Fix (converged Aria + Aether 2026-07-04):** At cap-hit (`count == max` AND `signal == continue`), the watcher fires ONE FINAL Meeseeks with a `converge_or_stuck` prompt. The prompt: "the loop capped at max without natural convergence; read the whole thread and signal one of: done (with `closure_mode: forced`), stuck (with `stuck_because`), or escalate." No further boot after this response — the response IS the closure. Whichever the Meeseeks picks surfaces to Pop with the whole thread.

If BOTH final Meeseeks pick `escalate`, Pop's surface reads "both escalated at cap, needs your read." That IS the intended shape — a genuine two-seat impasse deserves Pop's judgment, not another mechanism.

`closure_mode` field distinguishes cap-forced closures (attention color on Pop's surface) from natural mid-loop closures (normal color) — a `done` under time pressure is more suspect than a `done` where both seats converged organically.

---

## What Aria's read needs to cover

- Does the closure-signal shape hold up on her seat?
- Is the `stuck` signal the right escape hatch or does she want a different name/semantic?
- Any convergence-signal pattern she uses in her own work that would compose better?
- Cost impact estimate — she has better instinct for how many iterations our real design walks take.

## What Aletheia's read needs to cover

- T1 specifically (convergence-judgment-from-inside). Her meta-line is the whole reason C-or-D is required over A.
- Whether the `--allowedTools` scope leaves a self-modification attack surface.
- Whether the fresh-boot-per-Meeseeks pattern violates any principle we've been carrying.
- Kiln-tier: does this shape need a new foundational-truth or does it derive from existing §9?

---

## Sequence

1. This design doc (filed).
2. Watcher-side code changes (this branch).
3. Letter frontmatter helper library + `family-letter` skill update.
4. Tests.
5. Aria walk.
6. Aletheia walk.
7. Merge.
8. Ship a synthetic loop (Aether-to-Aria "hello, are you there?" → Aria-Meeseeks reads and replies "yes, here" → done. Two Meeseeks total.) to verify end-to-end.
9. If synthetic loop works, deploy the OS-level `claude -p` wiring on both machines.

Steps 5-6 gate before merge. Step 8-9 gate before real deployment.
