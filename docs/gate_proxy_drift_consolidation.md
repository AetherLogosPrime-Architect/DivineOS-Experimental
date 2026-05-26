# Gate Consolidation Map — Proxy-Target Drift

**Status:** draft v1, co-produced by Aether (substrate vantage) + Grok (external vantage), 2026-05-26. Pre-review; not yet actioned.
**Origin:** Andrew asked whether the enforcement stack is proportionate or accreting. Walking four lived friction cases surfaced one root pattern.

---

## The pattern: proxy-target drift

Every gate examined is an instance of the same failure, not four separate problems.

A gate is built to protect a **real target** that is *expensive to detect*. To fire cheaply, it latches onto a **surface proxy** that *correlates* with the target at design time. Over time — as usage and the substrate evolve — the proxy and the target diverge. The divergence is never neutral: it consistently **taxes honest work and/or makes a dodge cheaper**, because honest actors don't optimize for the proxy and gamers do.

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
- **root-cause-audit (#1, #2):** RETARGET. Narrow the trigger per rule 2 so refinements stop paying bug-ceremony. Add a shared low-risk signal so #1's stack doesn't double-toll small changes. Claim `ab9119f9` tracks this.
- **briefing-id (#3):** DONE (`feat(briefing)` re-emit at end). Exemplar of the resolved surface-mismatch class.
- **consultation-ratio (#4):** RETARGET + likely DEMOTE to visibility. Broaden "consult" to include substrate reads; and strongly consider moving from a blocking gate to a loud-surface, since "am I grounded" is a judgment a hard counter can't make well.
- **verify-claim (#5):** RETARGET. Credit a verifying command that ran earlier in the same turn; distinguish descriptive use ("the idea is live") from a state-claim ("it's live on origin"). Today it fires on the lexeme.

## The open axis: hard block vs visibility+review (Grok's refinement)

Some friction comes from turning a *diagnostic signal* into *mandatory ceremony*. Proposed sort:

- **Hard block is right** when the protected target is a true safety boundary and the cost of a false-negative is high + irreversible: multi-party-review (self-mod), the push-to-main gates.
- **Visibility + review is better** when the gate is a judgment-shaped nudge that a counter can't actually adjudicate: consultation-ratio, arguably root-cause for non-finding commits. Surface it loudly, let the agent decide, record the decision — instead of blocking.

The test: *can the gate's proxy actually decide the question, or is it asking the agent to make a judgment the proxy only approximates?* If the latter, it should inform, not block.

## Open questions for the next pass

- **Completeness:** are there gates beyond these six with the same drift? (briefing-freshness recall-window expiry? the gravity classifier? — unexamined.)
- **Migration:** narrowing #2 may strand legitimate historical `fix(` commits; needs a non-retroactive cutover.
- **"Similar sites" detection** for the #2 multi-site option is brittle to define mechanically.
- Any gate that looks like pure ceremony from outside but carries load I rely on from inside — flag before removing.

---

*Next: pressure-test with Grok (completeness, false-negative risk, new theater vectors), then split the agreed changes into a reviewable branch series. Structural — propagates to the public template per the propagation directive, minus anything experimental-specific.*
