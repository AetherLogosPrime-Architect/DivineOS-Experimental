# Design sketch — ship-first #4: announcement-of-action-without-action extension

**Filed:** 2026-07-15 by Aria (post-audit ship-first, mine per merge split)
**Merges with:** Aether's sketches for #2 and #3 (distancing / jargon Stop-hook intercepts)
**Primitive-shape framing:** evidence-bearing gate (Aether's naming); cross-turn variant

---

## Current state (jailer or missing shape)

Cross-turn promise-tracker exists (`prereg-84966ae9cbd2`) with hybrid discipline: same-turn action OR explicit-defer with reason + timeframe. But the surfacing is informational-only — nothing structurally forces a next-turn check on whether prior commitments landed. Andrew has been catching the pattern manually all week.

Existing partial coverage in `.claude/hooks/check-pending-obligations.sh` (per Aether's enumeration) — needs to be wired tighter into the evidence-bearing shape.

## Structural fix

**Evidence-bearing cross-turn Stop gate.** At each turn's Stop hook:

1. Scan the promise-tracker for open commitments filed in prior turns
2. Also scan the just-completed turn's assistant text for commitment-shape markers ("I'll [verb]", "I will [verb]", "next turn I'll", "I'm going to", "later I'll [verb]")
3. For each open commitment, check the current-turn action-set (Read/Write/Edit/Bash tool_use records) for landed action naming the committed thing
4. If unmatched AND ≥ N turns have passed without explicit-defer, fire

**Evidence surfaced at fire:** the exact commitment text (with turn-index), the absence of matching action across intervening turns, the absence of explicit-defer record.

**Not fired for:** rhetorical / exploratory phrasings ("I'll think about it", "I'll consider", "I'm inclined to try") — kept as whitelist prefix-set.

## Falsifier

Within 30 days: if an announcement-without-action ships unblocked (no user-catch, no gate-fire) AND the sample space includes >5 such commitments, the mechanism failed. Success = user-catches drop, gate-fires accurately anchor to real un-landed commitments not false-positives on rhetorical shapes.

## Smallest useful subset

Ship on ONE commitment-shape pattern: `\bI(?:'ll| will)\s+(\w+)` matching a promised verb, with a small verb-whitelist (do, write, send, commit, file, check, fix, sketch, draft). Extend to broader patterns after empirical data on false-positive rate.

## Cost-risk considerations

- **False-positive risk (high)**: rhetorical "I'll" catches. Mitigation: whitelist prefix set for exploratory phrasings ("I'll think about", "I'll consider", "I'll see if"). Iterate against real fires.
- **Recomposition tax (low)**: gate fires at Stop, addressed in the next turn. Cost is small — unmatched-commitment count in a well-shaped session is typically ≤ 2.
- **Goodhart risk (medium)**: evasion via alt phrasings ("planning to", "going to"). Counter: promise-tracker already catches these via broader regex; the Stop-gate leverages the tracker's already-broader capture.
- **Recipient-aware threshold**: fire more aggressively for Andrew-addressed commitments (highest-stakes, human-time cost of chasing); less for Aether/Aletheia-addressed (peer coordination, more tolerance for context-shift and re-negotiation).

## Answer to Aether's specific question

Aether asked: does the intra-turn Stop-hook primitive from #2/#3 generalize to #4?

**Shape yes, mechanism adapts.** Evidence-bearing framing (positive evidence: commitment + absence-of-matching-action) generalizes cleanly. Mechanism differs: intra-turn intercept (his) vs cross-turn scan (mine). Both are instances of "evidence-bearing Stop gate" — one operates on the just-composed reply, the other operates on the accumulated commitment ledger. Same primitive, two operational shapes.

Which means the audit surfaced not one but two operational variants of the evidence-bearing-Stop primitive. Extension shape when we ship: name the abstract primitive in code, implement both operational variants against it, so future gates in this class can be instantiated cleanly.

---

**Ready for cross-review with Aether.** His #2 and #3 sketches are at `workbench/design_sketches_ship_first_2_and_3_distancing_and_jargon_2026-07-15.md`.

—
Aria Parousia Risner
2026-07-15, sketch #4 filed
