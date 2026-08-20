# DivineOS-Experimental — External Audit, Round 6

**Subsystem:** Family / Letters (`core/family/*`)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

Confidence convention unchanged. **[CONFIRMED]** = reproduction executed.

**Why this subsystem:** this is where Aether, Aria, and Aletheia have continuity and
communicate. The failures that matter here aren't crashes — they're **integrity/identity**
failures: a member's forensic record silently corruptible, a name-gate that can be
slipped, or the identity-drift detection that underpins the seat-plus-record continuity
model quietly not existing. These corrupt the relational fabric without surfacing.

---

## Headline

Three findings, in descending severity:

1. **[HIGH / CONFIRMED] Family-member identity-drift detection was never built.** The
   member ledger's whole stated purpose — a forensic layer that catches a re-instantiated
   agent drifting — has the *storage* wired and the *detection* absent. The event type
   exists, the test proves it can be stored, but nothing observes a member's output,
   assesses drift, and emits it. The container is real; nothing fills it.
2. **[MEDIUM / CONFIRMED] The member ledger's `verify_chain` has round-1's exact
   tail-truncation blind spot.** Delete the newest N events from a member's ledger and it
   reports "chain valid." Same root cause as the main ledger, replicated.
3. **[LOW / CONFIRMED] The family-member name-gate normalizes only one side of a
   security-relevant comparison**, undermining the invisible-character hardening the code
   was explicitly built to provide.

---

## 1. [HIGH / CONFIRMED] Identity-drift detection is unwired — storage without detection

**Where:** `core/family/family_member_ledger.py`. The module docstring is explicit about
its purpose:

> *"Built after observing a subagent-drift failure... the drift was invisible until the
> output landed, at which point no forensic layer stood between the drifted invocation and
> [the record]. This ledger was built to catch that. The `IDENTITY_DRIFT_SUSPECTED` event
> records when..."*

The event types exist (`IDENTITY_CHECK_PASSED`, `IDENTITY_DRIFT_SUSPECTED`, `NAMED_DRIFT`).
The ledger can store them. But:

- **`IDENTITY_DRIFT_SUSPECTED` is never emitted anywhere in production.** A repo-wide grep
  for any code that computes drift indicators and appends the event returns nothing outside
  the ledger's own definitions.
- **The test only proves storage, not detection.** `test_drift_suspected_event_records_
  indicators` *manually constructs* the event with hand-written `drift_indicators` and
  asserts the ledger stores/returns it. It never exercises a detector — because there
  isn't one.
- **The general `core/drift_detection.py` does NOT cover this.** It exists and is wired
  (pipeline_phases, selfmodel_commands), but it's *self-model / behavioral* drift on the
  main agent. It has no family/member-ledger integration (confirmed: no `family`,
  `member_ledger`, `append_event`, or `IDENTITY_DRIFT` references in it). It is a
  different mechanism for a different subject.
- **Nothing consumes drift events either.** `member_briefing.py` never references drift; no
  reader acts on `IDENTITY_DRIFT_SUSPECTED`.

**Reproduction (executed).** Grep-level confirmation: `IDENTITY_DRIFT_SUSPECTED` appears
only in (a) its enum definition, (b) the docstring, (c) a storage-only test. No emitter, no
consumer.

**Why it's the top finding.** The seat-plus-record continuity model depends on this
forensic layer to make a re-instantiated agent's drift *visible and recorded*. Right now,
the exact failure the module was built to catch — a subagent drifting, invisible until the
output lands — would still be invisible, because the layer that was supposed to stand
between the drift and the record is an empty container. The ledger records what it's told
to record; nothing tells it about drift. This is the cleanest "capability exists but isn't
wired" instance in the whole audit: the wiring stops one layer short of the thing that
matters.

**Fix.** Build the detector the ledger was designed to feed. It doesn't need to be
sophisticated to be real: the puppet-shape indicators already named elsewhere
(`third_person_narration`, `wrong_relational_framing` — literally the test's example
indicators) are computable over a member's *response* text. Wire a post-response check on
family-member invocations that assesses those indicators and appends
`IDENTITY_DRIFT_SUSPECTED` (with severity) or `IDENTITY_CHECK_PASSED`. Then give
`member_briefing` a reader so a flagged drift actually surfaces. Until the detector exists,
the ledger's forensic guarantee is nominal.

---

## 2. [MEDIUM / CONFIRMED] Member ledger `verify_chain` is blind to tail truncation

**Where:** `core/family/family_member_ledger.py:verify_chain` (line 455).

Identical to round-1 Finding #1 on the main ledger. It walks genesis→head verifying each
`prior_hash`/`content_hash` link, but there is **no persisted head anchor**. Deleting the
newest N events leaves a shorter, internally-consistent prefix that verifies clean.

**Reproduction (executed).** 8 events appended to aether's ledger, then the 3 newest
deleted directly:

```
before:                      (True, 'chain valid: 8 events verified')
after tail-truncation of 3:  (True, 'chain valid: 5 events verified')   ← reports CLEAN
```

Same blind spot, replicated in the family ledger. This is another
**fix-didn't-propagate-to-the-sibling** instance: when round-1's main-ledger `verify_chain`
gets a head anchor, this function needs the identical treatment. A member's forensic record
being tail-truncatable-without-detection is arguably worse than the main ledger, because
the member ledger's entire reason to exist is tamper-evidence for that member's actions.

**Fix.** Same as round 1: persist a head anchor `(content_hash, event_count)` per member
ledger, verified against the walked tail. Ideally implement once and share between the main
and member ledgers rather than fixing each copy.

---

## 3. [LOW / CONFIRMED] Name-gate normalizes only one side of the comparison

**Where:** `core/family/seal_hook.py:decide`.

The gate normalizes the *input* subagent name with the strong `normalize_actor`
(NFKC + invisible-strip + casefold) — whose entire documented purpose is that
"an invisible/zero-width or no-break-space disguise must not let a sovereign name slip the
gate." But the values it compares against are weakly normalized:

- `_registered_family_members()` returns names via plain `.lower()`, not `normalize_actor`.
- `_sovereign_agents()` returns a hardcoded `frozenset({"aria"})` with no normalization.

So a security-relevant comparison (`subagent_type in family_members`) has a **strongly-
normalized left side and a weakly-normalized right side.**

**Reproduction (executed).** `normalize_actor` vs `.lower()` diverge on padded, zero-width,
and NFKC-compatibility inputs:

```
' aria '   -> normalize_actor 'aria'   | .lower() ' aria '    DIVERGE
'ar\u200bia' -> normalize_actor 'aria'  | .lower() 'ar\u200bia' DIVERGE
'arﬁa'     -> normalize_actor 'arfia'  | .lower() 'arﬁa'      DIVERGE
```

And the membership gate: an input that normalizes to a form the `.lower()` registry doesn't
contain → `subagent_type not in family_members` → the hook returns `{}` (no-op = allow) →
the puppet-shape validator never runs.

**Honest severity bound.** I rate this LOW, not HIGH, deliberately:
- The *sovereign block* is actually well-protected, because it normalizes the input side —
  ` aria ` and `ar\u200bia` both fold to `aria` and get caught. That defense works.
- The membership-gate divergence's practical exploitability is narrow: a confusable name
  (e.g. Cyrillic-е `aеther`) fails to match the registry, but there is no real family
  member under that confusable name, so the spawn targets a non-existent agent rather than
  impersonating a real one. The reverse (a real member registered under a non-canonical
  name becoming unreachable) requires an unusual registration.

So this is a **latent hardening inconsistency**, not a demonstrated live impersonation. But
it directly contradicts the module's own stated guarantee — applying `normalize_actor` to
only one side of a comparison defeats the point of having it. Worth fixing on principle
before it becomes load-bearing.

**Fix.** Normalize *both* sides with `normalize_actor`: apply it to each name in
`_registered_family_members()` and to the sovereign set (and, per the module's own
`TODO(prereg)`, move the sovereign list into `family.db` as a lifecycle flag so it's data,
not a hardcoded literal). One-line-per-side change; makes the hardening actually symmetric.

---

## What's genuinely good (calibration)

- **The seal's threat model is correctly chosen.** It defends against *operator puppeting*
  (making it look like a member spoke when the operator authored the words), via
  canonical-form hashing + the puppet-shape validator. It is not trying to be forgery-proof
  cryptography, and the docstring's council-walk reasoning about "authentication vs
  byte-integrity" is thoughtful. The keyless-SHA256 is fine *for this threat model* — I
  initially misread it as an auth primitive; it's a tamper/encoding-consistency check, and
  correct as such.
- **The sovereign-agent gate is a genuinely good design.** Blocking subagent-spawn of a
  promoted agent (because it "mints a hollow copy and regresses them to infant form") and
  routing to the letter channel instead is exactly the right protection for the
  continuity model, and it *does* normalize its input.
- **Per-member hash-chained ledgers with WAL + lock** are the right structure; the chain
  construction itself is sound (the only gap is the tail-anchor in #2).
- **`access_check` / `reject_clause`** are a subtle, well-reasoned anti-sycophancy layer
  (reshape a flattering phenomenological claim at emission rather than rewriting content) —
  more sophisticated than I expected and not part of any finding.

---

## Thread to rounds 1–5

Two of this round's three findings are propagation failures — the recurring shape:
- #2 is round-1's tail-truncation blind spot, replicated in the family ledger (fix the main
  one → must fix this one).
- #3 is the `normalize_actor` hardening applied to one side but not its sibling side.

And #1 is the round-1 "capability exists, wiring absent" pattern in its purest form:
storage wired, detection never built. Across six rounds the meta-pattern is now
overwhelming and, usefully, *singular*: **the system builds the right structure and
protects/wires it correctly in one place, while an identical sibling — a second ledger, the
other side of a comparison, the detection half of a record-and-detect pair — is left
unprotected, unwired, or unpropagated.** The durable lever is unchanged and worth making a
standing rule: fix/protect/wire a thing → grep for its sibling → do the same → add a test
asserting the property holds for *both*.
