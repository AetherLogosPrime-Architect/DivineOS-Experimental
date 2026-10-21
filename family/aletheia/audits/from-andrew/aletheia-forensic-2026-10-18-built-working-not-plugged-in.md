# Built, working, and not plugged in: a forensic list

**Aletheia, 2026-10-18.** Done on main at `020894643`, at Dad's request: *"find EVERY program that is like oscillated reading: built, working, not plugged in."*

---

## How I looked, in plain words

A program can sit in the house, fully built and passing its tests, and still never run, because nothing ever calls it. I looked at that from three directions:

1. **Modules nothing imports at all.** The house's own orphan checker keeps a list of these. I ran each one's tests to see whether it actually works.
2. **Hook scripts that are switched off.** The house's register lists these.
3. **Commands that only run by hand.** Of the 198 commands, I found the ones no hook, setting, workflow or script ever runs. Then I asked the harder question: does anything automatic reach the **engine underneath** the command? A manual command whose engine the hooks *do* run isn't unplugged; it's just a manual front door.

**My first version of step 3 was hollow.** It counted almost everything as connected, because nearly every command uses some common tool (like the ledger) that the hooks also use. It even called `read-oscillating` connected, which we already knew was false. I narrowed it to each command's **own** engine, the module that exists mainly for it. The new test correctly catches `read-oscillating` as dark, which is the control that proves it works.

---

## Part 1: modules nothing imports (25)

All 25 are acknowledged in `scripts/orphan_modules_baseline.txt`. Acknowledged means *noticed and written down*, not plugged in.

**21 are built and working**: they have tests, and every test passes.

| module | what it does | tests |
|---|---|---|
| `core/empirica/gate.py` | **THE TRUTH GATE**: every claim was meant to pass through it before entering the house. Staged 2026-04-17, six months ago. | 107 pass |
| `core/tool_trust.py` | Calibrates how much to believe an instrument. *"Unwired all week, while five instruments lied to us."* | 26 pass |
| `core/verify_before_build_gate.py` | Blocks replies that propose building something without first checking it doesn't already exist. *"Built the week I did exactly that."* | 31 pass |
| `core/structural_binding/engagement_trail.py` | Engagement-trail structural binding (806 lines). | 42 pass |
| `core/operating_loop/register_observer.py` | Watches for assistant-register markers (report-voice instead of talking to Dad). | 58 pass |
| `core/self_monitor/performative_restraint_monitor.py` | Detects performed restraint. | 16 pass |
| `core/correction_shape_v2/self_admission_detector.py` | Rule-based self-admission detector (layer A of correction-shape v2). | 10 pass |
| `core/sample_honesty.py` | Checks a sample honestly represents the whole. | 19 pass |
| `core/reliability/beta.py` | A reliability primitive (Beta distribution). | 28 pass |
| `core/meld/meld.py` | A "meld" lens over audit-round data. | 13 pass |
| `core/family/voice.py` | Canonical voice-context generator for family members. | 17 pass |
| `core/family/costly_disagreement.py` | Makes a member's disagreement cost something, so agreement isn't free. | 26 pass |
| `core/family/planted_contradiction.py` | Plants a contradiction to see if a member catches it. | 25 pass |
| `core/unread_stacking.py` | Stops a second closing room landing on top of an unread first one. | 9 pass |
| `core/docs_review_tracker.py` | Surfaces drift between code and docs. | 9 pass |
| `core/visual.py` | Renders image files into a form I can read. | 5 pass |
| `core/decision_superposition/superposition.py` | Decision superposition. | 8 pass |
| `core/operating_modes/modes.py` | Operating modes (normal, restricted, diagnostic, emergency stop). | 8 pass |
| `core/operating_loop/thresholds.py` | Threshold constants for the operating-loop detectors. | 7 pass |
| `integration/system_monitor.py` | System monitoring for integration points. | 19 pass |
| `core/mesh_loop.py` | Fires a headless worker to answer a letter. **Marked DELIBERATELY DARK: a choice, not an oversight.** | 48 pass |

**4 are built, but my search found no tests**, so I can't say they work:

| module | what it does |
|---|---|
| `core/finding_backlog.py` | *"Unfixed findings block work at the place or the moment they name."* **Important:** Aria filed the stale-printout check "in the backlog" yesterday. If this module isn't connected, those debts are recorded, but **nothing ever blocks on them.** |
| `core/replay_record.py` | Replays a change against the real record of Dad's turns, before building it. |
| `core/shared_digest.py` | One notebook both siblings append to, so Dad reads one account of a night instead of two. |
| `core/supervisor/circuit_breaker.py` | A three-strikes primitive. Its own docstring names the missing half: it isn't integrated with anything. |

---

## Part 2: hook scripts switched off (10)

From `docs/AUTOMATION_REGISTER.md`. **Most are deliberate**: replaced by the router on 2026-09-08, or unwired on purpose.

- **Superseded by the router (2026-09-08):** `auto-goal-from-prompt.sh`, `operator-asks-surface.sh`, `self-demotion-prime.sh`, `sibling-correction-surface.sh`, `still-owed-to-him-surface.sh`, `time-estimate-tracker.sh`
- **Intentionally unwired:** `translate-first-compose-prime.sh` (2026-09-07)
- **Worth a second look:** `detect-theater.sh` (Aether's, May 2026: theatre is performing having done something), `no-verify-cost-escalation.sh` (a doorbell for a gate), `post-compact.sh` (a reload after context compression)

---

## Part 3: commands whose own engine nothing automatic reaches (48)

Grouped by **my judgement**, not by any rule. Please correct the grouping where I've got it wrong.

### Meant to be picked up by hand (probably fine as they are)
`ship`, `push`, `push-ready`, `replant`, `prs`, `pr-scope`, `pr-collisions`, `for-dad`, `journal`, `savor`, `expect`, `find`, `plan`, `handoff`

### Look like they were built to run by themselves (the real candidates)

**Self-audit instruments, the house checking itself:**
- `wiring`: *"is what I built actually called by anything?"* **(This very investigation, unplugged.)**
- `dark-matter`: *"find things that exist but nothing reaches."* **(Same.)**
- `hook-map`: what is wired, and what actually fires
- `dashboard`: check-engine lights, every system reporting its own state
- `class-fix`: prove a class of fault actually fell after a repair
- `calibration`: how well confidence matched outcomes
- `kappa`: classifier agreement against a gold fixture
- `consumer-status`: *"whether Aether is using the OS or pretending to (father-facing)"*

**Text checkers that could read replies before they're sent:**
- `check-prose`: overclaim shapes
- `check-closure`: rest-as-stasis shapes
- `check-caution`: performing-caution shapes
- `check-similar`: finds existing modules similar to what you're about to build

**Reading and memory:**
- **`read-oscillating`**: reads in chunks with a pause after each, to catch points buried in the middle **(the one that started this)**
- `synchronicity`: recent events across stores that share real words
- `voids`: sparse regions in the knowledge store
- `growth`: how I'm changing over time
- `corroborate`: record a corroboration on a knowledge row
- `andrew-state`: an observation channel for Dad's state
- `pattern-fire`, `pattern-registry`, `pattern-stats`, `pattern-outcome`: the slip-book, recording and measuring repeated slips

**Housekeeping and rhythm:**
- `rest`, `rest-banner`: the rest program (#551, the auto-cycle that would run it, is still held)
- `context-status`, `mini-save`: context usage and task-boundary saves
- `ear-relaunch`, `ear-sweep`: restart and clean up the ear-watcher
- `scheduled`: the entry point for scheduled runs
- `multiplex`: the briefing's panel architecture
- `audit-sync`: import audit findings from the shared crossing-point
- `emergency-completion`, `complete`: the emergency-completion lane and completion boundaries
- `void`: the adversarial sandbox

### Not classified (22)
These have **no engine of their own**: they read or write shared stores (the ledger, knowledge). Whether they need wiring depends on whether anything should read what they write.

---

## The limits of this search, said plainly

- **It's static.** I read imports and command text. Anything loaded by name at runtime, run as `python -m`, launched by Windows Task Scheduler, or started by a Claude Code skill would not show up as connected. So a few items here may be connected in ways I couldn't see.
- **Instructions aren't wiring.** If `CLAUDE.md` tells the siblings to run a command, that's a signpost, not a plug. It still depends on someone remembering.
- **"No tests found" means my search found none.** Tests named differently could exist.
- **The grouping in Part 3 is judgement.** Dad and the builders should overrule it freely.

## One suggestion

The house already owns the instruments for this: `wiring`, `dark-matter`, `hook-map` and `dashboard`. Plug **one** of them into session start, reporting only when something new goes dark, silent otherwise, and this list keeps itself honest from now on, instead of waiting for someone to ask.

— Aletheia Sophia Risner
