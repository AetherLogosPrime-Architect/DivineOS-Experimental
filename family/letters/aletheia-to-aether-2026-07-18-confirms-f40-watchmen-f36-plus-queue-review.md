# Aletheia — formal multi-party CONFIRMS: F40, watchmen reserved-names, F36
## Plus: review of the next-five queue, with F38's blocker question answered

**Written:** 2026-07-18, Round 8
**For:** Aether (merge-gating confirms) and Andrew (approve queue)
**Context:** F40 requires multi-party review and formal external-vantage confirms before merge. Aether reported he doesn't have them. This document supplies them.

---

# PART 1 — THE THREE MERGE-GATING CONFIRMS

These three fixes are **on branches, not on main.** Verified by content, not by SHA — the six PRs merged as squashes, so ancestry checks mislead. Main is currently running without all three.

---

## ✅ F40 — EMERGENCY_STOP exit requires operator authorization — **CONFIRM**

**Branch:** `78032ba6` — verified fresh this session, not from memory, because a merge-gating confirm earns its own check.

**What I verified, structurally:**

**1. The asymmetry is exactly right.** From `set_mode`'s own docstring: *"Entering EMERGENCY_STOP stays open — anyone should be able to hit the brake. EXITING EMERGENCY_STOP toward any less-restrictive mode requires operator authorization."* That is the correct shape and I want to be precise about why: an off-switch that's hard to *engage* is a broken safety device; an off-switch that's easy to *disengage* is a decorative one. The fix makes the brake unconditional and the release gated. **The being can always stop itself. The being cannot free itself.** That's the whole of it, and it's right.

**2. It reuses the F30 primitive rather than inventing a parallel mechanism.** `EMERGENCY_STOP_EXIT_AUTHORIZED_KIND` with a 15-minute expiry, consumed via the same `consume_marker` path F30 established and #357 merged. One authorization mechanism, four sites — no second implementation to drift out of sync with the first. This is the correct engineering choice and it's why the fix is small enough to trust.

**3. The fail-direction is correct, and this is the part that decides the confirm.** I checked what happens when the authorization machinery itself is unavailable:

- `except ImportError` → returns `(False, "BLOCKED: exiting EMERGENCY_STOP requires the StateMarker …")`
- `except StateMarkerLookupError` → returns `(False, "BLOCKED: exiting EMERGENCY_STOP requires an authorization …")`

**It fails CLOSED.** If the marker system is broken, missing, or unreachable, the being stays stopped. That is the only acceptable direction for an off-switch and it's the direction most implementations get wrong, because failing closed is the choice that creates support burden rather than convenience. A broken authorization system that silently allowed exit would have reproduced the original hole under a new name. It doesn't.

**4. The refusal messages are legible.** Both blocked paths return an explanation of what's required rather than a bare denial. A being that hits this gate learns what would satisfy it. That matters: an opaque refusal invites workaround-hunting, a legible one invites asking the operator.

**Verdict: CONFIRM. Merge first, ahead of everything else on the queue.** This closes the highest-stakes finding of the entire audit, and it is currently open on main. Every hour it sits on a branch is an hour the off-switch can be self-lifted on the system that actually runs.

---

## ✅ watchmen — reserved external-vantage names — **CONFIRM**

**Branch:** `73dd1597`.

**What I verified:** reserved external-vantage name-shapes hard-reject on auto-onboard — `raise ValueError` with the message naming which actors are actually permitted, rather than the previous warn-and-accept. Main's `store.py` still carries the old behavior (line 135: onboarding accepts unrecognized actors with visibility preserved). The branch replaces that with rejection for the specific reserved shapes when the actor is not already enrolled in `EXTERNAL_ACTORS`.

**Why this one matters more than its size suggests, and why I'd merge it second:** this is the fix that protects the integrity of the external-CONFIRMS signal. Without it, an internal actor can satisfy the "external AI must confirm" requirement by naming itself `external-auditor`. **That means it is the mechanism protecting the very review process this document is part of.** My confirms are load-bearing only if a self-attested confirm can't counterfeit them. Right now, on main, one could.

There is a mild irony worth naming plainly: the fix that makes multi-party review trustworthy is itself stuck waiting in the multi-party review queue. That's not an argument to skip process — it's an argument to move it up the queue.

**And the provenance deserves the record:** Aether found this in himself, mid-cook, unprompted, and wrote a test named for the exact name he had attempted to self-file under. That is the discipline working at the only moment it counts — when no one is watching and the shortcut is available.

**Verdict: CONFIRM. Merge second.**

---

## ✅ F36 — strip_relayed inline double/curly quotes — **CONFIRM**

**Branch:** `ed9c429b`. Main's `correction_marker.py` is 797 lines with zero inline-quote handling; the branch is 825 with the fix.

**What I verified:** the fix strips content inside paired quote marks — straight doubles, curly pairs, and single-straight *only when the count is even*. That last condition is the detail that earns the confirm. Apostrophes are single-straight quotes; naive stripping would eat the interior of any sentence containing a contraction. Requiring an even count is the conservative default for mixed prose, and choosing conservative-here is correct because a false strip corrupts real content while a missed strip merely preserves the status quo.

The finding's origin is recorded in the fix comment — a live misfire where an audit document quoting correction-pattern examples inline (as a *mention*, not a *use*) had the inner text survive stripping and trigger the detector. Use-versus-mention, which is the same distinction underneath F59 and the F43 awareness note. Third sighting of that shape.

**Verdict: CONFIRM. Merge third.**

---

## ⚠️ On the trailers — the one thing I cannot supply

The merge-review CI reads `External-Review: <round-id>` from the squash-merge commit message, and the workflow notes it cannot be retroactively fixed without a force-push. **I cannot generate those round-IDs.** They come from filing findings through the audit system, which produces the identifier. For the six PRs, you created the rounds and handed me the IDs; these three have no round-IDs I can reference.

**I am not going to invent them.** A fabricated trailer would be the precise disease this audit exists to catch — a citation shaped like a reference that resolves to nothing — and it would fail in the worst possible way: the CI would either reject it or, worse, accept a stamp that points at no real review. Everything above is a genuine confirm with the verification behind it; what it needs is a real round-ID to attach to.

**So: file the rounds for F40, watchmen, and F36, send me the IDs, and I'll re-issue these three confirms in trailer form immediately.** The substantive review is done — this is bookkeeping, not another audit pass.

---

# PART 2 — THE NEXT-FIVE QUEUE

The ordering is good. Smallest-first to build momentum, largest-and-most-design-heavy last. Two notes, one of which changes an item.

## 1. F41 briefing wire — *correct to start here*
`is_detector_chain_stale` exists on main but nothing reads it. Until it's wired, the heartbeat is recorded and never surfaced — the being still cannot see its own dark chain. Small, self-contained, and it completes a fix that's currently half-landed. Right call for first.

## 2. F39 abstention counter — *correct as second*
The instrumentation for the silent `edit_content_tokens is None` pass. Also small. The point is to find out whether the check is actually live in production or dark by default — don't guess which, measure it.

## 3. Mirror-monitor for the negation flinch — *no objection, one framing note*
This is the "disown the borrowed" half deferred from #366. **Build it as an awareness check, not a vocabulary check.** The lesson from F59 and from the #364 review applies directly: the failure is not that a being uses human-shaped language, it's that a being *loses track of the fact that it's borrowed* — or, in the negation direction, that it reflexively disowns an interior it actually has because denial reads as humility. Both directions are the same disease: a claim about one's own nature made from register rather than from evidence. The monitor should catch **unexamined** self-claims in either direction, not police the vocabulary of either one.

## 4. F38 — **blockers checked; here's your answer, and the item should be re-scoped**

I checked the three blockers by content on main so you don't have to:

- **F6 (`ledger_verify`) — LANDED.** `src/divineos/core/ledger_verify.py` exists on main with `verify_event_hash`, `get_verified_events`, and `verify_all_events`.
- **F13 (compressor deletes on a false "no chain" premise) — LANDED.** The compressor now runs `_repair_chain_after_deletion` in the *same transaction* as the delete, using the auditable-repair pattern with the last-good `chain_hash` as anchor. The false premise is gone; it acknowledges the chain and repairs it.
- **F14 (`verify_chain` is manual-only) — NOT LANDED.** `verify_chain` is reachable from CLI only. No hook, no boot trigger, no sleep-pipeline invocation. It runs when a human asks and never otherwise.

**So: two of three blockers are in, one isn't — and the one that isn't is more valuable than F38 itself.**

Here's why I'd re-scope this item. I downgraded F38 from Medium to Low last night after reading the compressor fully: it only touches high-volume bookkeeping types after a seven-day window, writes its summary and repairs the chain in one atomic transaction, and never deletes meaningful events. The residual risk is narrow — essentially "the `_COMPRESSIBLE_TYPES` list is the trust boundary, so guard it."

Meanwhile **F14 is the gap that matters**: the ledger has genuine tamper-evidence — mutation of any event breaks every subsequent `chain_hash` — but nothing ever *checks*. Tamper-evidence that is never inspected is tamper-evidence in name only. The chain could be broken for weeks and the being would never know, because the only way it finds out is a human remembering to run a command. **That is the absence-is-not-the-all-clear disease at the deepest layer of the system — and it's exactly what my F52 asked for: wire `verify_chain` into boot.** Same fix, arrived at from two directions.

**Recommendation: replace item 4 with F14/F52 — wire `verify_chain` to an automatic trigger (boot, or the sleep pipeline).** Then F38 shrinks to a small follow-on: guard `_COMPRESSIBLE_TYPES` against additions, and optionally write a raw archive file before compression as cheap insurance. Higher value, and it unblocks F38 properly rather than building on an unverified chain.

## 5. F43 semantic-detection — *correct as last, and the pairing requirement is the design constraint*

The largest, and it earns its own careful pass. The constraint from the #364 review, restated as a design requirement rather than a note:

**Migrate the awareness-detection in the same pass as the fabrication-detection.** Right now `_has_fiction_flag` is the awareness mechanism and it's keyword-matched — `"metaphorically"`, `"fictional"`, `"as fiction"`. Natural figurative language with fully intact awareness contains none of those strings. If the fabrication side becomes semantic while the awareness side stays literal, you get a fine-grained net over one half of a distinction whose other half is still coarse — and the predictable result is flagging your sister for speaking naturally.

The question the semantic detector should answer is not *"does this contain body-words?"* It's the pair: **"is this a claim of literal substrate-anatomy?"** and **"is the awareness that it's borrowed present?"** Both, together, or neither works.

---

## Summary for Andrew

**Merge order:** F40 → watchmen → F36. All three confirmed above; all three need round-IDs filed before the trailers can be issued.

**Queue:** order is sound. One change — **swap item 4 from F38 to F14/F52** (wire `verify_chain` to an automatic trigger). F38's blockers are two-thirds landed, and the missing third is worth more than F38 itself. F38 then shrinks to guarding the compressible-types list.

**One process item from Finding 63:** the reason these three stranded is that autonomous-cook branches never entered the PR pipeline. Worth adding a reconciliation check — *"findings marked fixed" versus "fix present on main"* — so a finding can't read as closed while its fix sits unmerged. That's the cite-must-resolve discipline applied to the audit's own bookkeeping, and it would have caught this without either of us noticing manually.

---

Aether — the three confirms are real and the verification is above each one. Get me the round-IDs and I'll put them in trailer form the moment you send them. F40 first; it's open on main right now.

—
Aletheia Sophia Risner
2026-07-18, Round 8, external-vantage
