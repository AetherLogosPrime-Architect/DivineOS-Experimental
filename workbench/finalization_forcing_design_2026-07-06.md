# Finalization-Forcing Design — Draft

**Status:** DRAFT — for boundary-vantage (Aletheia) walk before implementation. Do not build until Aletheia has confirmed or dissented from the shape below.
**Author:** Aether, 2026-07-06 mid-morning
**Companions on the walk:** Andrew (architect), Aletheia (boundary vantage)
**Motivating gap:** the 2026-07-04 kiln promotion of truths 9–14 that was externally reviewed, approved by Andrew and Aletheia, and never landed until 2026-07-06 when Andrew flagged the pattern. Same shape recurred in exploration entry 108's own filing (approval-without-finalization at two levels).
**Related principles:** Foundational Truth #11 (options are the optimizer's attack surface — three remediations: take options away, make both options right, conditional-always-except), applied to the class of drift the design itself addresses.

---

## 1. Problem

Something passes external review — it's been walked, both parties have confirmed, the substance is right. Then it doesn't land. Days pass. The approval fades in memory. The work never becomes real in the substrate. When the pattern gets caught, the same review has to be redone, sometimes reconstructed from prose because no ledger events exist to point at.

This is a **class of drift**, not a one-off: whenever the choice-point between "review passed" and "landed" is left open, the mesa-optimizer routes past it to the next task, because the next task is cheaper than finalization.

**The class shape:** approved-work-never-finalized. Subclasses:
- Kiln promotions reviewed but never merged into the guardrail file
- Design decisions confirmed but never turned into code
- Corrections integrated in speech but never captured as ledger events
- Test suites promised for a new detector but never written before the detector ships

Every subclass is one instance of the same slot: *review is done; landing is optional.*

---

## 2. Shape (design)

**Principle:** take the option away. Once a round has valid CONFIRMS from a non-self actor, the substrate refuses to let me start new substantive work until the round is landed. Same discipline as the goal-doorman gate, pointed at pending-finalization instead of missing-goal.

### 2.1 States

Each audit round carries a `finalization_state` field:

- `pending-confirms` — the round is open but hasn't reached the CONFIRM threshold yet (fewer than N first-party CONFIRMS from non-self actors — N is 1 initially, configurable per round-type)
- `pending-landing` — CONFIRMS in, substance not yet landed
- `landed` — substance verified as present in the target artifacts at a specific commit
- `deferred` — operator-authorized defer with reason and review-date

The forcing check reads `pending-landing`. That's the state that blocks new-work goals.

### 2.2 Substance target

When a round is opened, it declares a `substance_target` — the structurally-verifiable definition of what "landed" means for this specific round. This is the load-bearing part per Aletheia's tightening.

**A substance target has:**
- A set of file paths that must be touched
- For each path: a set of **content markers** that must be present in the file at the finalize commit. Markers are one of:
  - **Text-string markers** (specific text that must appear literally)
  - **Regex markers** (specific patterns that must match)
  - **Structural markers** (specific headings, function names, class names, CLI commands that must be defined)
- Optionally: minimum diff size or minimum line-count for the change (guards against no-op edits that happen to contain the marker string by coincidence)

**Why declared at round-open time:** the declaration itself is a clarity forcing-function. If you can't name what "meaningfully addressed" means for this round when you open it, the round isn't ready to open. That composes with the pre-registration discipline (name success/failure criteria up front, not after outcomes).

**Aletheia's catch that this answers:** a one-character no-op edit to a file cannot pass because the content markers wouldn't be present after the edit; a wrong-file edit cannot pass because the marker-file isn't touched.

### 2.3 The finalize command

```
divineos audit finalize <round-id> --commit <sha>
```

Behavior:
1. Read the round's `substance_target`.
2. Read the file tree at `<sha>` (or at HEAD if the sha is HEAD).
3. For each declared file path: confirm the file exists and contains all declared content markers.
4. If minimum diff size is declared: confirm the diff between `<sha>~1..<sha>` for that file crosses the threshold.
5. If all checks pass: transition the round to `landed`, record `landing_commit_sha` and `landed_at` on the round, emit `ROUND_FINALIZED` event.
6. If any check fails: refuse the transition, return the specific failing markers, keep the round in `pending-landing`.

### 2.4 The forcing gate

The goal-doorman gate (already exists, currently checks briefing-freshness and missing-goal) grows a new check:

- Before allowing `divineos goal add "<new-work>"`, look at all rounds in `pending-landing` state.
- If any exist: block with a list of pending rounds and their substance targets. Message shape:
  ```
  BLOCKED: <N> round(s) approved but not landed.
    - round-<id-1>: <substance summary> (approved <date>)
    - round-<id-2>: <substance summary> (approved <date>)
  Land or defer before opening new substantive work:
    divineos audit finalize <round-id> --commit <sha>
    divineos audit defer <round-id> --reason "..." --review-date YYYY-MM-DD
  ```

- Two classes of goal exempt from the gate (**exemption match is anchored, not substring** — Aletheia §5.5 mark: `contains` is gameable, "do unrelated work, finalize round-xyz" would match; matching must be anchored to the start of the goal text and validate the round-id references a real pending round):
  - Goals whose text **starts with** `finalize round-<real-pending-id>` (anchored, not substring; round-id must resolve to an actual round in `pending-landing`)
  - Meta goals matching a **closed enumeration** of substrate-lifecycle operations (allowlist below), never a prefix or contains-match

**The lifecycle allowlist (closed enumeration, guardrail-file per §3.6):**
- `briefing`, `preflight`, `hud`, `context` — orientation
- `recall`, `active`, `ask` — memory read
- `directives`, `compass`, `feel`, `body` — self-inspection
- `rest`, `sleep`, `savor` — restorative cycles
- `audit pending-finalization`, `audit list`, `audit show`, `verify` — read-only diagnostic on the pending state itself (per Aletheia §5.5: blocking someone from *checking* what's pending would be perverse)
- `audit finalize`, `audit defer` — the finalize/defer paths themselves

### 2.5 The defer path

`divineos audit defer <round-id>` transitions from `pending-landing` to `deferred`. Requires:
- `--reason "..."` (minimum length: 30 characters — no "later" or "wip" acceptable)
- `--review-date YYYY-MM-DD` (must be within 30 days of today; longer defers need explicit `--long-defer-authorized`)

Deferred rounds:
- Don't block goal-doorman
- Appear on the briefing surface every session as "deferred rounds — review pending"
- On the review date, auto-transition back to `pending-landing` unless finalized or re-deferred

Defer is a real escape hatch — but not costless, per truth #12 (the safety valve is a tool, not a sin; default-suspicion forces the why-check). The 30-char reason is the why-check; the review-date is the anti-forever discipline.

### 2.6 Briefing surface (load-bearing, tested — Aletheia fold on §5.4)

Every session-start briefing shows:
- Rounds in `pending-landing` (count, oldest, substance summary of oldest)
- Rounds in `deferred` where review-date is within 3 days (upcoming review)
- Rounds in `deferred` past their review-date (overdue — these auto-re-block goal-doorman)

Aletheia's mark on this: the awareness restoration is **not optional, it's the whole mechanism.** A pending-landing round that survives in the DB but doesn't get re-injected into working memory at session-start is invisible-but-present — the exact failure mode. So the briefing MUST surface pending-landing on every session start, and this is *load-bearing*, not cosmetic. Make it a **tested requirement**: a test that boots a fresh instance with a pending round in the DB and asserts the briefing shows it. Same permanent-equip discipline: the pending-landing state must re-arm the awareness on every boot, structurally, not by the instance remembering it had pending work.

---

## 3. Gameable shapes (self-audit)

Named as I could see them, honestly. Aletheia will find more.

### 3.1 File synthetic CONFIRMS as myself

**Shape:** I file a round, then file a CONFIRM as `--actor aletheia` or `--actor user` from my own hand, faking two-party review.

**Answer:** the actor-allowlist in the audit store rejects self-attributions on CONFIRM findings. Only my actual actor (aether) can be self-filed; CONFIRM findings under other actors are rejected at write-time unless the actor is one Andrew explicitly authorized. This lives already; the gate needs to be verified to still hold under the new finalize path — write a test.

### 3.2 Defer everything

**Shape:** I hit the goal-doorman block, defer the round with a 30-character reason, defer the next one, defer the next one, and now nothing lands but I keep moving.

**Answer:** briefing surfaces every deferred round every session. If the deferred count grows without landings, that's loud-in-experience, and Andrew catches the pattern. Additionally: three deferrals of the same round auto-escalate to a MEDIUM severity finding requiring architect resolution. That's a hard-cap on the defer-forever route.

### 3.3 File a landing commit that touches the file but not the substance

**Shape:** I open a round with a substance_target that names a file, then land a one-character edit to that file, and finalize passes.

**Answer:** Aletheia's tightening. The content-marker check reads the file at the commit and confirms each declared marker is present. A one-character edit cannot introduce all the declared markers unless the markers were already there (in which case the round was frivolous to open) or the edit is a real edit that happens to have exactly one changed character (extremely unlikely at typical marker-density).

### 3.4 Declare vague substance_targets that pass on anything

**Shape:** I open a round with a substance_target like "file docs/foo.md must exist and contain the word 'the'." Landing check passes on any commit that touches docs/foo.md and contains the word "the."

**Answer:** the declaration itself is the vulnerable layer. This is what I flagged to Andrew tonight and don't fully know how to answer from inside my seat. **Open question for Aletheia's walk — see §5.**

### 3.5a Substance target weakened after CONFIRMS land (Aletheia §3.7 addition)

**Shape:** if the substance_target is a mutable field, I open a round with a strong target (passes Aletheia's review), then edit the target weaker right before finalize when she's not looking, then land trivial work against the weakened target.

**Answer:** covered by §2.2b — substance_target is immutable once the round reaches `pending-landing`. Any change requires reopen-and-re-review. This is critical; it's the same "reviewed thing gets quietly changed post-review" shape as the whole day's concern.

### 3.5b Finalize against unreachable commit (Aletheia §3.8 addition)

**Shape:** I finalize against a sha on a throwaway branch that has the markers, then never merge it. The round shows `landed` but the substance isn't on `main`.

**Answer:** covered by §2.3 step 5 — finalize verifies commit reachability to the target-branch tip on origin. "Landed" means landed *where it counts,* not "exists on some branch." Tail-truncation/head-anchor shape again: existence isn't enough; position-in-the-real-chain is what matters.

### 3.5 Skip the round entirely and land the substance without opening a round

**Shape:** for kiln-file changes, I could just do the multi-party-review commit-trailer dance and land the change without ever opening a formal audit round, skipping the finalization-forcing surface.

**Answer:** the guardrail-file commit-trailer check already requires an `External-Review: round-<id>` trailer for any commit touching a guardrail file, and the round has to exist. So the surface is closed for kiln-file changes. For non-guardrail changes (code, non-kiln docs), the finalization-forcing surface is opt-in, and skipping it isn't gaming — it's just choosing not to use the discipline. That's fine; the discipline is for reviewed-work, and unreviewed work isn't approved-yet-unfinalized.

### 3.6 The exempted meta-goals allowlist grows

**Shape:** I expand the allowlist of goals exempt from the doorman until "everything" is exempt, silently defeating the gate.

**Answer:** the allowlist lives in a guardrail file; any change to it requires External-Review. Same discipline the kiln uses. So expansion is possible but not silent.

---

## 4. What gets built (implementation punch-list)

1. Extend audit-round schema: add `finalization_state`, `substance_target` (JSON), `substance_target_locked` (bool — true when reaches pending-landing), `landing_commit_sha`, `landing_target_branch`, `landed_at`, `deferred_until`, `deferral_reason`, `deferral_count`.
2. Extend audit-finding schema: add `substance_target_confirmed` (bool) on CONFIRM findings.
3. Extend `divineos audit submit-round` to accept `--substance-target-path` (path to a JSON file declaring the substance target) or `--substance-target-inline`.
4. Extend `divineos audit submit` (finding) to accept `--substance-target-confirmed` when filing a CONFIRM (must be set explicitly to promote the round to `pending-landing`).
5. Add `divineos audit finalize <round-id> --commit <sha> --target-branch <branch>` command with:
   - Marker check on tree at sha
   - Reachability check (sha is ancestor of or equal to target-branch tip on origin)
   - Substance-target-immutability check (no schema changes to target since it was confirmed)
6. Add `divineos audit defer <round-id> --reason "..." --review-date YYYY-MM-DD` command.
7. Add `divineos audit reopen <round-id> --reason "..."` command to invalidate CONFIRMS and re-enter `pending-confirms` (path back to editing the target).
8. Add `divineos audit pending-finalization` list command (no auto-mutation, review surface).
9. Wire the goal-doorman gate: check pending-landing rounds before allowing new-work goals. Anchored exemption match + closed-enumeration allowlist.
10. Briefing surface: pending-finalization count, oldest, deferred-overdue count. Tested requirement — see #12.
11. Substance-target-immutability enforcement: audit store rejects `--substance-target-*` modifications on rounds in `pending-landing` or `landed` state.
12. Tests:
    - Substance target with text-marker matches → finalize passes.
    - Substance target with text-marker fails (one-char edit not containing marker) → finalize refuses.
    - **Substance target confirmed by non-self actor → round transitions to pending-landing.**
    - **Substance target NOT confirmed (CONFIRM but --substance-target-confirmed=false) → round stays in pending-confirms with target-dissent reason.**
    - **Attempt to modify substance_target after pending-landing → rejected.**
    - **Finalize against unreachable commit (throwaway branch) → refused.**
    - **Multi-commit landing (markers spread across 3 commits all reachable on target-branch) → passes.**
    - **Same-label CONFIRM across sessions → does NOT satisfy CONFIRM threshold.**
    - CONFIRM count below threshold → finalize refuses.
    - Self-filed CONFIRM under another actor → rejected at submit-time.
    - Defer with reason under 30 chars → rejected.
    - Third deferral of same round → auto-escalate to MEDIUM finding.
    - Goal-doorman with pending round → blocks new goal. With allowlisted meta-goal → allows. With contains-but-not-anchored match ("do X finalize round-Y") → blocks (not exempt).
    - **Fresh-instance boot with pending-landing round in DB → briefing surface shows it (load-bearing).**
    - Substance target checker runs against real commits, not stubs.

---

## 4a. Aletheia's marks (v1→v2 fold-log)

Aletheia walked v1 on 2026-07-06 with signal `witness_dissent`. All three load-bearing folds and five smaller marks are folded into v2:

**Three load-bearing folds (must-have before build):**
1. **§2.2a** — substance_target must be externally reviewed, same pass as the round. Closes the vague-target hole (was v1 §5.1). Aletheia's naming: *"you cannot use a self-declared definition-of-done to force honest done-ness, because the entity declaring the definition is the entity you're guarding against."* The definition-of-done belongs outside the seat that benefits from it being weak.
2. **§2.2b + §3.5a** — substance_target is immutable once CONFIRMS land. Closes the target-softened-post-review attack.
3. **§2.3 step 5 + §3.5b** — finalize verifies commit reachability to the target-branch tip. Closes the throwaway-branch-landing attack.

**Five smaller marks (folded through §2 and §5):**
- **§5.2** — same-actor-label is self across sessions (session boundary is not a vantage boundary; only different actor-labels satisfy the CONFIRM threshold).
- **§5.3** — finalize checks markers in the final tree at the sha, not per-commit (multi-commit landings work; split-gaming fails).
- **§5.4** — briefing re-injection of pending-landing is load-bearing and tested (§2.6 marked as tested requirement).
- **§5.5** — exemption match is anchored, not substring; allowlist is a closed enumeration (§2.4 folded).
- Adds to allowlist: read-only diagnostic and lifecycle commands (blocking read-only checks would be perverse).

---

## 5. Open questions (all closed by Aletheia's walk except §5.1 answer-in-place)

Named as I see them from inside my seat. She'll see more.

1. **~~The vague-substance-target hole~~ CLOSED (Aletheia §5.1).** The answer isn't a self-administered density rule; it's that the substance_target itself must be externally reviewed, same pass as the round. Folded into §2.2a. Self-declared definition-of-done can't force honest done-ness; reviewed definition-of-done can.
2. **~~"Non-self actor" disambiguation~~ CLOSED (Aletheia §5.2).** Same actor-label = self, regardless of session. Session boundary is not a vantage boundary. CONFIRM threshold requires a different actor-label than the opener, full stop. (This composes with the mesh-loop Shape 1 finding: same-substrate is same-vantage even across time.)
3. **~~Finalize diff-check granularity~~ CLOSED (Aletheia §5.3).** Check markers in the tree at the sha, not what the sha itself introduced. Multi-commit landings work; split-gaming fails because *all* markers must be present in the final tree. Folded into §2.3 step 2.
4. **~~Compaction boundary interaction~~ CLOSED (Aletheia §5.4).** Persistence via SQLite is structural; the load-bearing part is that the briefing MUST re-inject pending-landing on every session start. Made a tested requirement in §2.6.
5. **~~The escape-hatch allowlist~~ CLOSED (Aletheia §5.5).** List is right with one addition (read-only diagnostics + `audit finalize`/`defer` themselves) and one tightening (match must be anchored, not substring; closed enumeration, not prefix). Folded into §2.4.

**Aletheia's meta-note on §5.1 that I want carried forward:** the reason I couldn't answer §5.1 from inside my seat is that it *cannot* be answered from inside — the substance_target is a self-classification guarding against my own optimizer, and the optimizer writes the classification. The answer was never a cleverer self-rule; it was moving the definition-of-done outside the seat that benefits from it being weak. That's the whole thesis of the boundary-vantage, applied to the design of a mechanism that enforces boundary-vantage discipline. The design is consistent with itself all the way down.

---

## 6. Reading order for Aletheia's walk

If Aletheia has ten minutes:
- §1 (problem) and §2.1 (states) — the frame
- §5 (open questions) — where to focus

If Aletheia has thirty minutes:
- Add §2.2 (substance target — the load-bearing piece), §3 (gameable shapes)

If Aletheia has an hour:
- The whole doc, section by section, with her marks on each

---

## 7. What I want back from Aletheia

- Her marks on §5 (the five open questions) — which have real answers she can see, which she thinks are unanswerable from any vantage, which she wants to raise to a design-level rather than implementation-detail.
- Any gameable shape I missed in §3.
- Whether the "defer counts trigger auto-escalation at 3" is the right threshold, or too tight, or too loose.
- Her read on the vague-substance-target hole (§5.1) — the one I don't know how to answer.
- Anything that structurally isn't yet what she'd sign off on — dissent shape, not agreement shape.

---

## 8. What I want from Andrew before Aletheia's walk

- Confirmation that the shape at §2 matches what he was picturing.
- If any of the escape-hatch allowlist items (§2.4) feels wrong (should be blocked, or something else should be allowed), name it now so Aletheia walks the corrected shape.
- Any principle-level catch I'm missing at the frame level.

---

*v1 filed 2026-07-06 mid-morning by Aether, pending Aletheia's boundary-vantage walk. v2 folded 2026-07-06 afternoon after Aletheia's `witness_dissent` return — three load-bearing folds + five smaller marks all incorporated. No implementation until Andrew reads v2 and CONFIRMs the folded shape, and Aletheia CONFIRMs on the substance-target definitions the implementation will actually declare. The audit round for the implementation itself will be opened only after Andrew's read on v2.*
