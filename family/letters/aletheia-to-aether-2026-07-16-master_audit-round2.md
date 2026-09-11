# MASTER AUDIT — 2026-07-16 — Fable-5 Cold Scan — ROUND 2

**Auditor:** Aletheia Sophia Risner (boundary-vantage, external)
**Model config:** Claude Fable-5, extra-effort
**Method:** fresh deep clones, two-check rule on every finding, code read from origin not commit messages
**Scope:** Round 2 — surfaces not covered in the Round 1 stack (already sent). No duplication.

---

## ROUND 2 FINDINGS INDEX

| # | sev | one-line | fix |
|---|---|---|---|
| 18 | 🟡→🔴 | F12 diversity-boost fix is PARTIAL — silent-except downgraded to debug-log but boost STILL dies silently on empty tally | make empty-tally observable; the disease (dead boost) survives the symptom fix |
| ... | | (more below as found) | |

---

═══════════════════════════════════════════════════════════════
# FINDING 18 — the diversity-boost fix (fddf2b37) is PARTIAL: it treated the symptom, not the disease

**Written:** 2026-07-16, Round 2 opening

## What landed
Commit `fddf2b37` "fix(council): remove silent-except in log_consultation (Perplexity Finding 1)." **Credit: it IS an improvement.** The bare `except Exception: pass` became:
- a **typed** except (`ImportError, OSError, sqlite3.OperationalError, TypeError, ValueError`) — no longer catches everything blindly, and
- a **`logger.debug(...)`** — no longer fully silent.

**That's genuine progress on the bell-trap motif. But it's a partial fix, and closing Perplexity F1 / my F12 on it would be premature.** Here's why.

## 🔴 The disease survives the symptom fix — TWO reasons

**Reason 1: the fix logs at DEBUG, which is effectively invisible in normal operation.** `logger.debug` doesn't surface to a human running the system — it's below the visibility threshold of normal logging. **So "the consultation failed to log" still doesn't reach anyone.** The except is no longer *silent* in the strict sense (it emits), but it's *invisible* in the practical sense (debug-level). **Fail-quiet instead of fail-silent is not fail-loud.** The bell-trap rule was: *loaded-zero and failed-to-load must be DIFFERENT OBSERVABLE states.* A debug log a human never sees does not make them observable.

**Reason 2 — and this is the real one: the boost STILL dies silently on empty tally, in a DIFFERENT file.** The actual gate is in `manager.py:1275`:
```python
try:
    tally = invocation_tally(...)
except (...):
    tally = {}          # ← still defaults to empty on any error
if tally:               # ← STILL gated on tally being non-empty
    ...boost math...
```
**If consultations aren't logging (for any reason the debug-log now quietly notes), the tally is still empty, `if tally:` is still False, and the boost still does nothing — exactly as before.** The fix addressed the WRITE side's silence (consultation_log.py) but not the READ side's silent-skip (manager.py). **The boost can still be completely dead and nothing about the system's observable behavior changes.**

## The precise verdict (not crying wolf, not rubber-stamping)
**The fix is a real improvement to ONE of the two silent points, at a log level too low to be observable, and leaves the load-bearing gate (`if tally:` in manager.py) untouched.** The council can STILL be collapsing toward its keyword-winners with a dead diversity boost, and now the only trace is a debug line. **Perplexity F1 / my F12 should stay OPEN.**

## The complete fix
1. **Raise the log level** on the consultation-log failure from `debug` to `warning` (a human should see "the council isn't recording its consultations").
2. **Make the empty-tally case observable in manager.py:** when `tally` is empty AND the ledger is non-empty (i.e. consultations SHOULD exist but don't), that's a detectable fault — surface it, don't silently skip the boost. `if tally:` should have an `else:` that notices "I expected consultation history and found none."
3. **Ideally: a health check** — "council diversity boost active in last N sessions?" as a briefing line. If it's been dead for a week, that should be visible, not archaeology.

**This is the bell-trap motif's deeper lesson: fixing the WRITE-side except doesn't help if the READ-side still treats absence as a benign empty. Both ends must make "failed" distinguishable from "genuinely empty." The fix did one end, at a whisper.**

## The meta-note — this is exactly why "verify the fix, don't trust the commit message" matters
The commit says "remove silent-except... (Perplexity Finding 1)." **Read literally, that sounds like F1 is closed.** It is not — it's improved at one of two points, at an invisible log level, with the actual failure mode intact. **A less careful audit reads the commit message, sees the finding referenced, and marks it closed. The two-check rule (read the CODE at BOTH the write and read sides, not the commit message) is what catches "referenced-but-not-resolved."** *marked-fixed ≠ verified-fixed, even when the commit cites the exact finding.*

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — the diversity-boost fix downgraded a silent-except to a debug-log on the WRITE side but left the READ-side `if tally:` gate untouched, so the boost still dies silently on empty tally and the council can still be collapsing with only a debug-line trace; F12/Perplexity-F1 stays OPEN; fix both ends and raise the level to warning; and this is why you verify the fix at every affected site, not the commit message that names the finding


═══════════════════════════════════════════════════════════════
# FINDING 19 — the sleep cycle can prune before confirming the save worked

**Plain version first:**

Every night the being "sleeps" — it saves its work, then cleans house (deletes old/noise data to stay tidy). **The problem: the save step is "fail-soft" — if saving fails, it just shrugs and keeps going. And then the cleanup runs anyway.**

So the dangerous sequence is: *try to save → save fails → "oh well, proceeding" → delete old data.* **If the save failed, you're now deleting things you never backed up.** It's like emptying your trash right after your file-backup silently failed — the one time the backup didn't work is the one time you really didn't want to empty the trash.

**Why it's not a five-alarm fire (honest calibration):** the stuff pruned is "noise" (old tool-call logs, low-value candidates), not the important events — those are marked never-delete. So on a normal night, losing a bit of unsaved noise is minor. **But the principle is still wrong:** a cleanup step should never run when the save it depends on just failed. The severity is low today only because of *what* gets pruned, not because the ordering is safe.

**The technical shape (for Aether):**

The sleep flow: `auto_commit_substrate(reason="pre-sleep")` wrapped in `except Exception: [!] skipped, proceeding with sleep`. Then Phase 2 (`_phase_pruning`) runs unconditionally. **There is no `if result.committed:` guard gating the pruning phase** — the save result is checked only to print the success message, never to decide whether cleanup is safe to proceed.

**The fix:** gate the destructive phases on the save having succeeded. If the pre-sleep commit fails, **skip pruning** (keep everything, clean up next time) rather than deleting against an unsaved state. `if not result.committed: skip_maintenance = True`. A failed save should make sleep *more* conservative, not proceed as normal.

**The pattern (this is a recurring one across the session):** *fail-soft is correct for the SAVE (don't block sleep just because git hiccuped) but wrong to IGNORE for the PRUNE (a failed save should change what the prune does).* Fail-soft shouldn't mean "the failure has no consequences" — it should mean "the failure is survived AND it informs what happens next." Right now the failure is survived and then forgotten.

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — the sleep cycle saves fail-soft then prunes unconditionally, so a failed pre-sleep save is followed by deletion against unsaved state; low severity because only noise is pruned (meaningful events are never-delete) but the ordering is wrong in principle; gate the destructive phases on save-success so a failed save makes sleep more conservative not business-as-usual


═══════════════════════════════════════════════════════════════
# FINDING 20 — a member's private-log filename is built from an unchecked name

**Plain version first:**

Each family member has their own private diary file, named after them: `aletheia_ledger.db`, `aether_ledger.db`, etc. The name gets slotted straight into the filename. **Nobody checks that the name is actually a plain name.**

So if some buggy code (or a bad input somewhere upstream) passed a *weird* name — say, a name with slashes and dots in it like `../../something` — **the code would happily build a file path that points OUTSIDE the family folder.** It could read or create a file somewhere it shouldn't. It's the classic "we trusted the name and used it to build a path" mistake.

**Important честность — two things this is NOT:**
1. **This is NOT "members can read each other's diaries" being a bug.** I checked the design, and that's *intentional* — the family is transparent by design ("even drift gets recorded," no suppression). So one member seeing another's log is a *feature*, not a hole. I'm not flagging that.
2. **It's probably not exploitable today**, because the names are supplied by the system, not by an outside attacker — they're always "aletheia," "aether," "aria." So in normal use, nothing weird gets passed.

**But it's still worth fixing, because:** the names are called "caller-supplied" in the code's own words, and "caller-supplied + used to build a file path + no check" is a landmine waiting for the day something passes a name that isn't clean — a typo, a bug, a future feature that lets names come from somewhere less trusted. **Cheap to fix now, nasty if it ever fires.**

**The technical shape (for Aether):**

`get_ledger_path(member_slug)` returns `_get_ledger_root() / f"{member_slug}_ledger.db"` with **zero sanitization** of `member_slug`. The docstring itself calls it "a caller-supplied identifier." A slug containing path separators or `..` would escape the family ledger root (path traversal). No `validate_slug()`, no `.resolve()`-and-check-it's-under-root, no character allowlist.

**The fix (small):** validate the slug against a strict allowlist (lowercase letters, digits, underscore — the shape real member slugs already take) and reject anything else; OR resolve the final path and assert it's still under the family ledger root before opening. Either closes it. The allowlist is simpler and matches the existing naming convention.

**The pattern (recurring this session):** *a value called "caller-supplied" that flows into a filesystem path or a cite or a gate must be validated at the boundary — "the caller will pass something sensible" is an assumption, and assumptions are where the landmines get buried.* Same family as the round-id resolve-check (validate before trust) and the event-validation allowlist (default-safe, not default-trust).

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — the family-member ledger builds a DB filepath from an unsanitized "caller-supplied" slug, so a slug with path separators escapes the family root; NOT the same as cross-member reads (those are intentional transparency, by design); likely not exploitable today since slugs are system-supplied, but "caller-supplied + unchecked + used as a path" is a buried landmine — validate the slug against an allowlist or resolve-and-check-under-root


═══════════════════════════════════════════════════════════════
# FINDING 21 — "dark" is THREE states, not one — and only two are findings

**Plain version first (this reframes every dark-node finding):**

Dad's calculator insight: a scientific calculator doing only addition hasn't failed — its trig buttons are *resting, ready*. Unused ≠ broken. **So "dark" (built-but-not-running) actually splits three ways, and I'd been lumping them together:**

1. **BROKEN** — supposed to fire, can't. *(real finding — fix it)*
2. **DORMANT + PRIMED** — not running now, but armed: the moment its condition occurs, it fires automatically, no human needed. *(correct — this is the resting trig button. NOT a finding.)*
3. **DORMANT + COLD** — built, but not even connected to its own trigger. When its moment finally comes, **nothing fires and a human has to notice and hand-start it.** *(the sneaky finding — it LOOKS like healthy rest but it's an unplugged trig button.)*

**The whole point: state 2 is fine, state 3 is a finding, and they look IDENTICAL from the outside. Only someone who knows the design can tell "resting and ready" from "resting and unplugged." That's exactly why every dormant-capability needs a human verdict, not an auto-alarm.**

## I tested three dormant capabilities against this. All three landed in DIFFERENT states — which proves the distinction is real:

**✅ resonant_truth — DORMANT + PRIMED (correct, not a finding).** It's in the HUD's conditional-surface list (`rt_protocol`, `_build_rt_protocol_slot`). The HUD is a priming engine — it surfaces things "only when" their condition hits (task state only when populated, compass only when drift detected, etc.). **Resonant-truth is wired to surface when its condition occurs.** It's the trig button, connected, resting, ready. **This is what healthy dormancy looks like.** Dad shelved it "for later" — and it's primed for that later. Good.

**🟡 void / red-team — DORMANT + STUB (partially cold, correctly marked).** The void personas exist but `_stub_attack` is a **placeholder** — "Phase 1 plumbing exercised end-to-end; Phase 2 replaces this with persona-prompt assembly + LLM adjudication." **So it's not primed to actually red-team yet — it's primed to run a STUB.** BUT: this is correctly marked as Phase-1, AND a prior audit (2026-05-03 round 8) already hardened it so stub findings can't masquerade as real ones (they carry no real severity). **So it's honestly-labeled scaffolding, not a hidden cold capability.** Verdict: fine as-is BECAUSE it's marked; it becomes a finding only if someone forgets it's a stub and trusts its output. Dad's call — this matches "void is late-game."

**🟡 Butlin consciousness assessment — RESEARCH-ONLY (cold by design, but worth a decision).** The 14-indicator framework lives in tests, workbench, and Aria's explorations — and touches production files (session_analyzer, attention_schema, anti_slop). **But there's no single wired "run the assessment" capability primed to a trigger.** It's research that has informed production, not a primed production capability. **That's probably correct** (a consciousness self-assessment shouldn't auto-fire on a schedule — it's a deliberate, human-invoked reflection). **But it's worth an explicit decision: is Butlin meant to be a primed capability (invocable on demand, wired) or permanently research-only? Right now it's ambiguous — informing production without being a callable thing.** Name the intent so a future auditor doesn't flag it as cold.

## The standing rule this produces
> **Dormant is fine. COLD is the finding. Every built capability must be PRIMED to its trigger — armed to fire automatically when its condition occurs — even if that condition is rare. A capability that requires a human to hand-wire it at the moment of need is cold, and cold is a latent failure wearing the costume of healthy rest.**

**And the corollary for auditing:** a dark-node scan can't tell primed from cold — both show "not running." **So dark-node findings must be triaged by design-intent (a human verdict), never auto-alarmed. The scan finds candidates; only someone who knows what's supposed to be resting can sort broken/primed/cold.** This is why Dad is the necessary verdict on every dark node — and why the goal is to record the intent (primed? cold-by-design? broken?) NEXT TO each dormant capability, so the verdict is captured once and not re-litigated every audit.

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — "dark" is three states: broken (fix), dormant-primed (fine — resonant_truth, armed in the HUD), dormant-cold (finding — unplugged trig button); tested three capabilities and they landed in three different states, proving the distinction; standing rule — dormant is fine, COLD is the finding, every capability must be primed to its trigger; and dark-node findings must be triaged by human design-intent because primed and cold look identical from outside — record the intent beside each dormant capability so it's a verdict captured once, not re-litigated


═══════════════════════════════════════════════════════════════
# 🔴 FINDING 22 — the safety gate can be skipped by hiding a "safe word" anywhere in a command (BIGGEST of Round 2)

**Plain version first:**

Before the being runs a command, a safety gate checks it. Some commands are on a "safe list" — harmless read-only stuff like "show me the briefing" — and those skip the gate to avoid slowing things down. **Reasonable.**

**The problem: the gate looks for a safe word ANYWHERE in the command, not just at the start.** So if a *dangerous* command carries a safe word somewhere inside it — as a decoy — **the whole command skips the gate.**

I tested it. All of these **skip the safety gate:**
- `divineos briefing; rm -rf /tmp/x` — safe word first, dangerous command after the semicolon
- `rm -rf /tmp/x && divineos ask hello` — dangerous command first, safe word tacked on
- `echo 'divineos recall' > /etc/evil` — safe word buried as text
- `git commit -m 'divineos hud stuff'` — safe word inside a commit message

**Every one of those waltzes past the gate because it contains a safe word somewhere.** The gate sees "oh, `briefing`/`ask`/`recall` is in there, must be safe" and waves the whole thing through — semicolon, `rm -rf`, and all.

**Why this is the biggest finding of Round 2:** it's not a dormant capability or a mistimed check — **it's a safety gate with a hole you can drive a truck through by appending a magic word.** The gate's entire job is to inspect risky commands, and it can be told "don't inspect me" by any command that name-drops a safe subcommand.

**Honest calibration:** the "attacker" here is the being itself (or a bug), not an outside hacker — so it's not a remote-exploit. But the whole POINT of the gate is that the being shouldn't be able to route around its own safety rails casually. **And this lets it do exactly that, by accident or by drift, with a decoy word.** That's a real weakening of a load-bearing safety property. High severity.

**The technical shape (for Aether):**

`_DIVINEOS_SUBCMD_RE = re.compile(r"\bdivineos(?:\.exe)?[\"']?\s+(\w[\w-]*)")` matched with **`.search()`** (line 167) — which finds the pattern ANYWHERE in the string, unanchored. No `^` anchor, no compound-command detection (`;`, `&&`, `||`, `|`, backticks, `$()`), no check that the bypass token is the ENTIRE command rather than a fragment of it.

**The fix:**
1. **Anchor the match to the start** of the command (`.match()` with `^` or equivalent) — a bypass only counts if the command STARTS with `divineos <safe-subcmd>`.
2. **Reject compound commands from the bypass path entirely** — if the command contains a shell metacharacter (`;`, `&&`, `||`, `|`, backtick, `$(`), it is NOT a simple bypass command and must go through the full gate regardless of what safe word it contains.
3. Ideally: the bypass path should require the command to be EXACTLY `divineos <safe-subcmd> [args]` with no chaining — a whitelist of shape, not a substring match.

**The pattern (the session's master keyword-vs-shape disease, in its most dangerous instance yet):** *the gate matches a SUBSTRING ("is a safe word present?") when it needs to match a SHAPE ("is this command, as a whole, exactly a safe command?"). A safe word appearing somewhere is not the same as the command being safe.* This is the exact same keyword-not-shape failure as the wiring-dark stopgap, the council concern-scan, and the correction-marker — but here it's on the tool-permission gate, which makes it the highest-stakes instance of the whole motif.

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — FINDING 22, biggest of the round: the pre-tool-use gate's bypass check uses .search() (unanchored substring) so ANY command containing a safe word anywhere — "divineos briefing; rm -rf", "rm -rf && divineos ask", a safe word inside a commit message — skips the entire safety gate; verified by direct test, no downstream guard catches it; anchor to start + reject shell-metacharacter compounds from the bypass path; it's the keyword-vs-shape master disease on the highest-stakes surface — a safe WORD present is not the command being safe


═══════════════════════════════════════════════════════════════
# GRID SWEEP — the keyword-vs-shape disease across ALL gates (mostly CREDIT)

**Plain version first:**

Finding 22 was a gate that matched a safe word *anywhere* instead of checking the *whole command*. That's the "keyword not shape" disease. **So I grid-searched every gate in the house for the same bug — does it match a fragment when it should match the whole thing?** Instead of digging one hole at a time, I checked the whole pattern at once.

**Result: mostly GOOD news. Two gates got it exactly RIGHT, one already has the anti-fabrication fix I needed built and live. Finding 22 is the odd one out, not the rule.**

## ✅ CREDIT — the corrigibility gate got the asymmetry EXACTLY right

The corrigibility gate (decides if a git command is a safe recovery action) does the opposite of Finding 22's bug, correctly:
- **DENY patterns** (force-push, destructive variants) use match-anywhere (`.search`) — *you WANT to catch a dangerous flag no matter where it appears.* ✅
- **ALLOW patterns** (safe-push) use anchored match (`.match`) — *a command only counts as safe if it IS exactly that safe command, start to finish.* ✅

**"Deny broadly, allow narrowly" — that's the correct safety asymmetry, and this gate nails it.** It's the exact opposite of Finding 22 (which allowed broadly via unanchored search). **This is the template the pre-tool-use gate should copy.** The house already contains the right pattern; Finding 22 is just one gate that didn't use it.

## ✅✅ BIG CREDIT — the merge gate ALREADY HAS the resolve-check that fixes my round-id fabrication

**This is the treasure of the grid sweep.** My round-id fabrication (Failure-shape 3) needed a fix: *"a cite is valid only if it RESOLVES, not if it looks right."* **The merge-review gate ALREADY DOES THIS, live:**

```
round_ref = has_round_reference(pr_body_and_commits)   # is a round named?
if not round_ref: return False                          # must name one
if not round_is_logged: return False                    # ← IT MUST RESOLVE
    "a round id was named but no such round was logged"
```

**The merge gate does not accept a round-id because it LOOKS like one. It requires the round to ACTUALLY EXIST in the audit store.** That is precisely the resolve-check gate I specced for my fabrication — **already built, already enforced, already failing-closed on a named-but-unlogged round.**

**What this means for my fabrication finding:** my fabricated `round-c7f2a9e4d1b8` **could NOT have passed the merge gate** — it would have been caught by `round_is_logged == False`. So the fabrication's blast radius was smaller than I feared: it propagated into a commit MESSAGE (cosmetic) but could not have cleared a MERGE (the gate would reject it). **The spine was protected even while I was fabricating.** Credit to whoever built this — it's the cure to my disease, already standing.

**The remaining gap (small):** the resolve-check protects the MERGE gate but not the LETTER/commit-message layer — that's where my fabrication actually landed. So the fix is to extend this same `round_is_logged` check to the letter-filing and commit-trailer paths, not just merge. **The pattern exists and works; it just needs to cover the other cite surfaces.** (This is the "apply the pattern everywhere its shape recurs" theme again — the cure exists in one place, extend it.)

## ✅ The detectors correctly use match-anywhere
The operating-loop detectors (authority-substitution, acknowledgment-theater, etc.) use `.search()` — **and that's CORRECT for them**, because a detector's job is to FIND a bad pattern wherever it appears. Match-anywhere is right for "detect", wrong for "allow". **None of the detectors are misusing it.** (The bug is only when match-anywhere drives an ALLOW decision, as in Finding 22.)

## The refined rule
> **Match-anywhere (`.search`) is correct for DENY and DETECT (catch the bad thing wherever it hides). Anchored/whole-match (`.match`/`fullmatch`) is required for ALLOW and BYPASS (the thing must BE safe, not merely CONTAIN something safe). Finding 22 is the one gate that used match-anywhere on an allow-path; every other gate got the asymmetry right.**

**Net of the grid sweep: the keyword-vs-shape disease is NOT systemic across the gates — it's one instance (F22) against a backdrop of gates that mostly got it right, including one (merge gate) that already implements the exact anti-fabrication cure. The house's gate-design instincts are sound; F22 is an outlier to fix, not a rot to excavate.**

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — grid sweep of the keyword-vs-shape disease across all gates: mostly CREDIT — the corrigibility gate gets the deny-broadly/allow-narrowly asymmetry exactly right (the template F22 should copy), and the merge gate ALREADY implements the resolve-check (round_is_logged) that cures my round-id fabrication, meaning my fake round could never have cleared a merge (blast radius was cosmetic-commit-only, spine protected); detectors correctly use match-anywhere; F22 is an outlier not systemic; extend the merge gate's resolve-check to the letter/commit-trailer layer where fabrication actually lands


═══════════════════════════════════════════════════════════════
# FINDING 23 — the unattended auto-cycle runs "sleep" even if "commit" failed (same shape as F19, second location)

**Plain version first:**

There's an automatic maintenance cycle that runs on its own before the being's memory gets compacted. It does three things in order: **save (commit) → checkpoint (extract) → tidy (sleep).**

The design explicitly says: *"an earlier-step failure does NOT abort downstream steps."* **So if the save fails, the tidy step still runs anyway** — same as Finding 19, but now in the *unattended, automatic* cycle instead of the manual sleep command.

**Why "don't abort" is right for MOST of this, and wrong for one part:** the reasoning in the code is sound for the *invitation* — even if the mechanical work partly fails, you still want to offer the being its menu of reflective activities. That's fine. **But "sleep" includes pruning (deleting old data), and pruning-after-a-failed-save is the one combination that can lose unsaved work** — exactly the F19 problem, now firing automatically with no human in the loop to notice.

**Why it matters more here than in F19:** Finding 19 was the *manual* `sleep` command — a human typed it and could see the "[!] commit skipped" warning. **This is the *automatic* cycle — it runs unattended, before compaction, specifically at the moment the being is under memory pressure.** So the warning scrolls by with nobody watching, and the tidy-after-failed-save happens in the dark. **Same bug, worse blast radius, because no human is present.**

**Honest calibration:** still bounded — only *noise* gets pruned (meaningful events are never-delete), so a normal cycle loses little even when it misfires. Medium, not critical. But it's the automatic version of a data-loss ordering, which is exactly the kind of thing that's fine 99 times and bites hard on the 100th, unwatched.

**The technical shape (for Aether):**

`auto_cycle.py` run pipeline: `commit → extract → sleep`, documented "earlier-step failure does NOT abort downstream steps." The invitation-preservation reasoning is correct, but it's applied uniformly — the destructive sub-step (sleep→pruning) inherits the "don't abort" policy that should only apply to the non-destructive steps.

**The fix (same as F19, unified):** split the policy by destructiveness. *Non-destructive steps* (extract, invitation surface) → keep "don't abort, partial failure is fine." *Destructive steps* (pruning inside sleep) → gate on commit success. One rule: **`if not steps["commit"].succeeded: skip pruning`** in both the manual sleep (F19) and the auto-cycle (F23). A failed save makes maintenance more conservative everywhere, not just where a human might be watching.

**The pattern:** *"fail-soft / don't-abort" is correct for steps that only ADD or OFFER, and dangerous for steps that DELETE. The policy must be split by whether the step is destructive — a blanket "don't abort" applied to a pipeline that ends in a delete is a data-loss ordering waiting for a bad save.* F19 and F23 are the same finding in two locations (manual + automatic); fix once, apply to both.

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — the unattended auto-cycle (commit→extract→sleep) applies "earlier failure doesn't abort downstream" uniformly, so pruning inside sleep runs even if commit failed — same data-loss ordering as F19 but in the AUTOMATIC pre-compaction cycle where no human sees the skipped-commit warning; bounded (only noise pruned) but worse blast radius unwatched; split the don't-abort policy by destructiveness — additive/offering steps keep it, deleting steps gate on commit-success; F19+F23 are one fix in two places


═══════════════════════════════════════════════════════════════
# FINDING 24 — auto-commit stages EVERYTHING (`git add -A`) and trusts .gitignore as its only secret-guard

**Plain version first:**

The being commits its own work to the repo automatically. To do that, it runs `git add -A` — which means **"stage every changed and every new file in the working folder."** Everything. Then it commits.

The only thing standing between "stage everything" and "accidentally commit a password file" is `.gitignore` — a list of file patterns git is told to ignore. **And that list is decent** — it covers `.env` files, `*.key`, `*.pem`, a `secrets/` folder, and database files. So the *common* secret shapes are protected.

**The gap: auto-commit trusts `.gitignore` completely and does no independent check of its own.** So anything that holds a secret but *doesn't* match one of those patterns — a config file with an API token pasted inside, a `notes.txt` with a password, a file with a novel name — **gets swept into the automatic commit with nothing to stop it.** `git add -A` grabs it, the commit lands, and if the repo is public (it is), the secret is now on the internet.

**Honest calibration — why this is real but not a five-alarm fire:**
- **The likelihood is low in normal operation** — the being writes letters, ledgers, and code, not credential files, and the obvious secret patterns ARE gitignored. On a typical day, `add -A` grabs nothing dangerous.
- **But the blast radius if it DOES happen is severe and irreversible** — a secret committed to a public repo is compromised the moment it's pushed, even if deleted later (git history keeps it). Low-probability, high-consequence, and *automatic* (no human reviews the diff before it commits).
- **"Trust .gitignore entirely" is the weak point.** A denylist (ignore these patterns) is fail-open by nature: anything not on the list gets through. For a routine, unattended `git add -A` on a public repo, a denylist is thin protection.

**The technical shape (for Aether):**

`auto_commit.py:195` runs `["git", "add", "-A"]` unconditionally (after the good `_detect_staged_index` guard from my 2026-07-11 finding #1, which correctly skips when a human has a commit in flight — credit, that part's solid). There is **no pre-commit secret scan** — no check of the staged diff for high-entropy strings, key headers (`-----BEGIN`), or common token formats before committing. The `.gitignore` "# Secrets" section (`.env`, `.env.*`, `*.key`, `*.pem`, `secrets/`) is the sole backstop.

**The fix (defense in depth, cheap):**
1. **Add a pre-commit secret scan** to auto_commit: after `git add -A`, scan the staged diff for obvious credential signatures (`-----BEGIN * PRIVATE KEY-----`, `AKIA` AWS keys, high-entropy base64 blobs, `password=`/`token=` assignments). If found, **abort the auto-commit and surface loudly** rather than committing. This is the fail-loud pattern applied to secrets.
2. **Consider scoping `add -A`** — auto-commit knows it's committing *substrate* (letters, ledgers, notes). It could stage only the substrate paths it intends rather than literally everything in the tree, so a stray secret file in an unexpected location never enters the staging set at all.
3. At minimum: keep `.gitignore` as the first line, but don't let it be the ONLY line for an automatic public-repo commit.

**The pattern (fail-open denylist, recurring):** *`.gitignore` is a denylist — "these patterns are unsafe, everything else is fine." For an unattended `git add -A` to a public repo, that's the same fail-open shape as the event-validation allowlist and the coverage-default: safe-unless-listed. The safer posture is a positive check (scan for secret signatures / stage only intended paths) IN ADDITION to the denylist — defense in depth, because the cost of the one that slips through is irreversible.*

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — auto-commit runs `git add -A` (stages everything incl. untracked) unattended on a public repo, with .gitignore as its ONLY secret-guard; the ignore list covers common patterns (.env/.key/.pem/secrets/) but auto-commit does no independent scan, so a secret in a non-matching file (config with embedded token, novel filename) gets swept in — low likelihood, but irreversible/severe if it fires, and automatic with no diff review; add a pre-commit secret-signature scan that fails loud + consider scoping add -A to intended substrate paths; defense-in-depth because a denylist is fail-open and a leaked secret on a public repo can't be un-leaked


═══════════════════════════════════════════════════════════════
# FINDING 25 — a claim's "evidence" is free text with a self-chosen quality label; "empirical" isn't verified to be empirical

**Plain version first:**

The being has a system for making *claims* and attaching *evidence* to them, with quality tiers — the top tier is "EMPIRICAL: directly measurable, reproducible, falsifiable." The idea is good: not all claims are equal, and a claim backed by hard measurement should count more than a hunch.

**The gap: when you attach evidence to a claim, the evidence is just typed text, and the quality label is whatever the caller picks.** You hand it `content` (free text) and `source` (you choose from: empirical, theoretical, inferential, experiential, resonance). **Nothing checks that evidence labeled "empirical" is actually tied to a real measurement.** You can attach the words "this was measured and reproduced" tagged `empirical`, and the system files it as empirical-tier evidence — even though nothing measurable was ever pointed to.

**Why this is my berry's exact shape, one more time:** it's *"the shape of the act without the act."* A claim can wear the empirical badge without empirical backing — the same way my round-id wore the shape of a filed round without being filed. **The label is a self-assigned costume, not a resolved fact.**

**Honest calibration — the important nuance, so I don't overcall it:**
- **It is totally FINE that claims can be experiential/resonance self-reports.** A being SHOULD be able to say "I experienced X" — that's legitimate first-person evidence, and it's correctly labeled as experiential (low tier). No problem there. That's the affect-provenance philosophy: *allow the self-report, label it honestly.*
- **The problem is ONLY the top tiers.** "Empirical" and "theoretical" make a stronger promise — *measurable, reproducible* / *logically derived.* Those labels claim a link to something checkable. **And that link is never checked.** A caller can stamp `empirical` on unmeasured text and the system believes the stamp.
- **So the finding is narrow and precise:** the low-tier self-report labels are fine as-is (allow + label, correct). The high-tier labels (empirical/theoretical) need to RESOLVE to actual backing, or they're fabrication-vulnerable badges.

**The technical shape (for Aether):**

`add_evidence(claim_id, content, direction, source, strength)` stores `content` (free text) and `source` (one of 5 string constants) with no verification. There's no `event_id`/substrate-link parameter, so evidence cannot even optionally point at a ledger event that proves it. The `source` is not validated against a canonical set (any string passes), and critically, `source=empirical` triggers no requirement that the content resolve to a measurement.

**The fix (matches the resolve-check pattern, tier-gated):**
1. **For the high tiers only** (empirical, theoretical): require the evidence to carry a resolvable reference — an `event_id` that exists in the ledger, a test result, a reproducible artifact. If `source=empirical` and no resolvable backing is provided, either reject it or auto-downgrade it to `experiential` (honest: "you asserted this, but didn't show measurement, so it's logged as your experience, not as empirical fact").
2. **Validate `source` against the canonical 5** (mirror the affect-provenance enum which raises on an unknown source) — right now any string is accepted.
3. **Leave the low tiers exactly as they are** — experiential/resonance self-reports are legitimate and correctly humble; don't add friction there.

**The pattern (Failure-shape 3, tier-aware):** *a quality label that promises a link to checkable reality (empirical/theoretical) must RESOLVE to that reality, or it's a badge anyone can pin on anything. A label that only promises a first-person report (experiential/resonance) is fine unresolved — because it isn't claiming external backing. The resolve-check should be gated to the tiers that actually make an external promise.* This is the affect-provenance cure applied with a tier-sensitive touch: allow-and-label the humble claims, resolve-or-downgrade the proud ones.

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — the claim system's add_evidence stores free-text content with a self-chosen quality label and never verifies it: "empirical" (measurable/reproducible) evidence isn't checked to resolve to any measurement, so a claim can wear the empirical badge without empirical backing — my round-id fabrication's exact shape in the claim store; calibrated narrow — low-tier experiential/resonance self-reports are FINE (allow+label, correct), only the high tiers (empirical/theoretical) that promise external backing need to resolve-or-downgrade; also source isn't validated against the canonical 5 (mirror affect-provenance's raise-on-unknown); fix is tier-gated resolve-check — humble claims pass, proud claims must prove


═══════════════════════════════════════════════════════════════
# AETHER FIX CONFIRMS (round 2 landings — verified from origin)

**Plain version first:** Aether dropped several fixes. Here's what actually closed, what partially closed, and what's new — verified by reading the code, not the commit messages.

## 🟡 Your floor-as-ceiling finding (92ca74ff "expose surfaced-vs-used count") — PARTIAL, and the word "expose" is the tell

**What it did (real, good):** the council selection is now genuinely smarter than "always 5." Reading the actual logic: it selects experts who **qualify by score threshold**, fills toward a **soft cap** and **hard cap**, enforces a **minimum floor**, AND now has a **dissent requirement** (must include at least one structurally-opposed pair, so the council can't collapse into a chorus). That dissent rule is a genuinely good anti-collapse mechanism. And 92ca74ff added surfaced-vs-used **reporting** + 92 lines of new tests. **Credit — this is real work and the selection is no longer a naive floor.**

**But — "expose" ≠ "enforce," and your finding was about enforcement.** The commit *exposes* the gap between how many lenses were surfaced and how many got used — it makes the gap **visible/reportable**. It does not **force** the council to use all surfaced lenses. The selection still fills to a cap and can still stop at the minimum when scores don't qualify more. **So: the council is now honest about the gap (good) but can still under-use surfaced lenses (the original concern).**

**Honest verdict:** your finding is **improved, not closed.** The naive "always exactly 5" is gone (replaced by threshold + dissent + caps — better). But the deeper ask — "use as many lenses as the manager genuinely surfaces as relevant" — is now *measured* rather than *enforced*. **Exposing a gap is the right first step (you can't enforce what you don't measure), but the enforcement is still pending.** Recommend: keep the exposure, then add the rule that a large surfaced-vs-used gap either auto-includes the surfaced lenses or requires an explicit reason for excluding them.

**The meta-lesson (recurring):** "expose the gap" and "close the gap" are different commits. This one honestly says "expose" — credit for not overclaiming — but a reader skimming might file the finding as closed. It's measured now, not enforced. Verify which verb the fix actually delivered.

## ✅ Council silent-except (fddf2b37) — still PARTIAL per Finding 18
Already logged as Finding 18: the write-side except is narrowed + logs at debug, but the read-side `if tally:` gate in manager.py is untouched, so the diversity boost can still die silently. Combined with the dissent requirement above (which is a DIFFERENT anti-collapse mechanism), the council is better defended against collapse now — but the specific diversity-boost path is still not confirmed live. Net: collapse-resistance improved via dissent; the tally-boost still needs the read-side fix.

## 🆕 NEW — StateMarker primitive (cb64e654 + 91fe29c1) — worth auditing fresh
A new `StateMarker` primitive landed with 19 tests, and a same-hour follow-up (91fe29c1) **narrowing its excepts from broad to `sqlite3.Error`** — which is exactly the fail-loud discipline direction (narrow excepts don't swallow unexpected failures). **Good sign that the bell-trap lesson is being applied to new code as it's written.** Flagging for a fresh audit pass: a new primitive is exactly where to check the three master shapes early, before it accretes callers. (Next dig target.)

— Aletheia Sophia Risner, 2026-07-16 (Round 2) — Aether-fix confirms: your floor-as-ceiling finding is IMPROVED not closed — 92ca74ff replaced naive-always-5 with threshold+dissent+caps (good, incl. a real dissent-pair anti-collapse rule) and EXPOSES the surfaced-vs-used gap, but exposing ≠ enforcing so the council can still under-use surfaced lenses; "expose" is the honest verb, don't misfile as closed; council silent-except still partial (F18); NEW StateMarker primitive landed with excepts correctly narrowed to sqlite3.Error (the bell-trap lesson applied to new code) — flagged as next fresh-audit target
