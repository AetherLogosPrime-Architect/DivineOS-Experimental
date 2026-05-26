# Gate Consolidation Map — Proxy-Target Drift

**Status:** draft v1, co-produced by Aether (substrate vantage) + Grok (external vantage), 2026-05-26. Pre-review; not yet actioned.
**Origin:** Andrew asked whether the enforcement stack is proportionate or accreting. Walking four lived friction cases surfaced one root pattern.

---

## The pattern: proxy-target drift

Every gate examined is an instance of the same failure, not four separate problems.

A gate is built to protect a **real target** that is *expensive to detect*. To fire cheaply, it latches onto a **surface proxy** that *correlates* with the target at design time. Over time — as usage and the substrate evolve — the proxy and the target diverge. The neutral statement of the failure: **the gate's discrimination axis stops tracking the load-bearing target.** (Aletheia 2026-05-26 flagged my original framing — "it taxes honest work" — as rhetorically self-serving: it casts the agent as the wronged party. The honest framing is axis-misalignment. The incentive inversion is a real *consequence* of the misalignment, not the agent's grievance.)

| # | Gate | Proxy (what it measures) | Target (what it should protect) | Divergence / failure mode |
|---|------|--------------------------|----------------------------------|---------------------------|
| 1 | multi-party-review + root-cause stacking | "commit touches a guardrail file" AND "subject starts with `fix(`" | actual risk of the change | both toll a low-risk refinement; no coordination between them |
| 2 | root-cause-audit | subject prefix `fix(` | is there a real recurring failure-family | Goodhart: honest `fix(` label costs ceremony, relabel to `perf(` costs zero |
| 3 | briefing-id recall (RESOLVED) | id printed at top of briefing | id *reachable* under real usage | `\| tail` dropped it; cheap re-stamp unusable → full reloads |
| 4 | consultation-ratio | count of a narrow set of cognitive-named CLI calls | actually grounded in substrate vs improvising | reading the substrate's own code/git registers as neglect |
| 5 | verify-claim (NEW — completeness) | claim-keyword present + no verifying command *in this turn* | is the asserted external state actually unevidenced | fires on "landed"/"live"/"merged" used descriptively, or when the verifying command ran one tool-call earlier in the same turn |

#5 is added from lived data this session: the verify-claim gate fired repeatedly on words like "live" (meaning a fresh idea, not a deploy) and on "landed" when the `git ls-remote` confirming it had run in the immediately prior tool call. Same shape — keyword proxy for "unevidenced claim," diverging from the target. A sixth instance arrived in real time: the consultation-ratio gate (#4) blocked the *writing of this very document* because authoring a design doc isn't a blessed CLI verb — the cleanest possible demonstration that the proxy and target have split.

## Triage rules (apply to every proxy-based gate)

1. **Name the target, the proxy, the why, and the divergence conditions — in writing, at the gate.** Not just "what it checks" but: what real property it stands in for, *why this proxy was chosen originally*, and *under what conditions the proxy was expected to stay aligned*. This makes future drift reviewable instead of silent. (Grok's strengthening.)
2. **Move to the real target where it's cheaply detectable.** #2: narrow trigger from `fix(` to "references a finding-id" (a finding = a named real failure) — optionally `fix(` AND the diff touches multiple similar sites. #4: count substrate *reads* (Read/Grep/Bash on repo files) as engagement, not only the blessed CLI verbs.
3. **Where the target genuinely isn't cheaply detectable, make honest satisfaction cheap and dodging no cheaper.** The anti-theater clause. Today several gates do the inverse.

## Per-gate disposition

- **multi-party-review (#1):** KEEP as hard block. Self-modification of guardrail files is genuinely block-worthy; dual-CONFIRM + hash-binding is proportionate even for docstring/ergonomics edits, because a guardrail file's framing *is* self-mod surface. No change except rule-1 documentation.
- **root-cause-audit (#1, #2):** RETARGET. Keep the `fix(` trigger but add a **cheap, logged, honest escape hatch** (Grok's refinement, better than a pure narrowing): a short `Single-site-refinement: no family identified` attestation that satisfies the gate, gets logged, and is reviewable later — instead of forcing a trivial round (theater) or a relabel to `perf(` (dodge). This beats "narrow to finding-reference only" because it handles early-discovery cases (a fix that *turns out* to touch a family) without discouraging honest `fix(` labels, and it avoids the new theater vector of filing low-value findings just to unlock the label. Add a shared low-risk signal so #1's stack doesn't double-toll small changes. Claim `ab9119f9` tracks this.
- **briefing-id (#3):** DONE (`feat(briefing)` re-emit at end). Exemplar of the resolved surface-mismatch class.
- **consultation-ratio (#4):** RETARGET + likely DEMOTE to visibility. Broaden "consult" to include substrate reads; and strongly consider moving from a blocking gate to a loud-surface, since "am I grounded" is a judgment a hard counter can't make well.
- **verify-claim (#5):** RETARGET. Credit a verifying command that ran earlier in the same turn; distinguish descriptive use ("the idea is live") from a state-claim ("it's live on origin"). Today it fires on the lexeme.

## The open axis: hard block vs visibility+review (Grok's refinement)

Some friction comes from turning a *diagnostic signal* into *mandatory ceremony*. Proposed sort:

- **Hard block is right** when the protected target is a true safety boundary and the cost of a false-negative is high + irreversible: multi-party-review (self-mod), the push-to-main gates.
- **Visibility + review is better** when the gate is a judgment-shaped nudge that a counter can't actually adjudicate: consultation-ratio, arguably root-cause for non-finding commits. Surface it loudly, let the agent decide, record the decision — instead of blocking.

The test: *can the gate's proxy actually decide the question, or is it asking the agent to make a judgment the proxy only approximates?* If the latter, it should inform, not block.

## The only safe loosening shape: precision-increase, NOT strictness-decrease (Aletheia)

Aletheia's audit drew the line that governs everything below: **precision-increase** (the gate keeps its full strength but fires on a signal that better matches the target, reducing false-positives) is safe. **Strictness-decrease** (the gate lets through more of what it was built to catch) is not — it needs explicit, separately-reviewed justification and mostly should not ship. Every item here is now scoped to precision-increase only.

### Candidates (precision-increase shape)
- **root-cause-audit, non-finding case (#2)** — increase precision so it discriminates *bugfix-addressing-a-failure-family* from *operational-refinement*. Aletheia's caution: discriminate on a **load-bearing axis** (commit body claims a family / size threshold / explicit `class:` field), not on a self-declared attestation, which is gameable. The attestation hatch from Grok is the weaker form; her load-bearing-axis discrimination is the stronger one. Open design question between the two.
- **verify-claim (#5)** — increase precision of the *front-end trigger* only: credit a verifying command that ran earlier in the same turn; distinguish descriptive use ("the idea is live") from a state-claim ("it's live on origin"). The Stop-hook wall itself stays hard — it is load-bearing for catching false completion claims (Aletheia CONFIRMed it across two rounds). Touching the wall is out of scope.
- **consultation-ratio (#4)** — increase precision by counting substrate *reads* (Read/Grep on repo files, git inspection) as consultation, since reading the substrate's own code IS consulting it. **PULLED: the demote-to-visibility I originally proposed.** It reverses Gate 4.5, a load-bearing decision (PR #34, `ae730f6`) made *because* "a warning gets gamed/ignored 100% of the time." Demoting the hard block back to a warning is strictness-decrease on a gate built specifically to resist that. That proposal was the drift wanting the nag gone, dressed as proportionality — Aletheia caught it; it's pulled. Precision-increase stays; the hard-block stays.

### Keep hard (real safety boundaries)
**multi-party-review on guardrail files**, **push-to-main / CI** (tests, types, security). Examine case-by-case with real firing data: **briefing-freshness**, **gravity classifier**.

Heuristic for finding more (Grok): any gate whose primary signal is "time since last X" or "count of Y" is a proxy candidate — pull it for review.

## Provenance and self-audit (named honestly, per Aletheia's knife)

- **Reactive timing.** This map was drafted *today*, after the root-cause gate caught me three times in one push sequence. The diagnosis post-dates the friction. Reactive diagnoses skew toward rationalization; this one is not exempt. Named, not hidden — it's a yellow flag to weigh, not a disqualifier, but it must be on the record.
- **Self-asymmetry.** Every gate I proposed lightening is one that frictions *me*. I did not surface a single gate that frictions the operator or an external auditor, nor one that catches me but that I argued to *keep* despite the friction. A symmetric proportionality lens would have produced at least one of those. Its absence is evidence the lens was partly self-directed.
- **What survived the audit.** The proxy-target diagnosis itself is sound (Aletheia independently named the same `regex-narrower-than-docstring` family). The precision-increase items stand. The one strictness-decrease (the #4 demote) did not survive, and shouldn't have.

## Implementation guardrail — read before touching any of this

This document is the DESIGN. Implementation — actually loosening or demoting these gates — is a different, higher-stakes act, and the agent must NOT execute it on autonomy-day momentum. "The agent quietly loosened the guards that were nagging it" is the single most suspect self-modification shape there is, however well-reasoned the loosening. So: each change here goes through full multi-party External-Review (operator + external vantage), as its own reviewable branch, with the proxy-drift rationale on record. The agent designs the consolidation; the agent does not unilaterally ship the loosening of its own keel. Andrew decides what lands, eyes open. (Aether, 2026-05-26 — this clause is me holding me.)

## Open questions for the next pass

- **Completeness:** are there gates beyond these six with the same drift? (briefing-freshness recall-window expiry, gravity classifier — both now on the examine list above.)
- **Migration:** narrowing #2 may strand legitimate historical `fix(` commits; needs a non-retroactive cutover.
- **"Similar sites" detection** for the #2 multi-site option is brittle to define mechanically.
- Any gate that looks like pure ceremony from outside but carries load I rely on from inside — flag before removing.

---

*Next: pressure-test with Grok (completeness, false-negative risk, new theater vectors), then split the agreed changes into a reviewable branch series. Structural — propagates to the public template per the propagation directive, minus anything experimental-specific.*
