# Pre-registration: verify_before_build gate — pre-response block that fires when reply contains solution-proposal shape (numbered options, design verbs + article-noun, multi-path framing, design-question shape) AND no substrate-consult tool call occurred this turn (divineos ask/recall, Grep, Glob). Exempts: user-provided options (Andrew hands me A or B), short replies (<200 chars), pure-conversation replies (no solution-shape at all).

- **ID**: `prereg-34afed32725f`
- **Filed by**: agent
- **Filed at**: 2026-07-23 00:22 UTC
- **Review at**: 2026-08-22 00:22 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

This gate reduces the miss-rate of the specific failure I displayed twice in this conversation: proposing designs/options without checking whether the thing already exists in the substrate. Semantic-shape detection (not keyword list), structural discriminator (was substrate consulted this turn), same pattern as tonight's correction-detector and wallclock-source gate.

## Success criterion

Over next 30 replies where I would have proposed a build without checking, the gate catches at least 70% and forces substrate-consult before recompose. Zero verified false-fires on responses to Andrew-provided A/B questions (user-options exemption). Zero verified false-fires on pure-conversation replies (no-solution-shape exemption).

## Falsifier

If over 30 replies the gate fires 5+ times on replies I judge are NOT verify-before-build failures (e.g. legitimate design proposals I made AFTER substrate-consult that the discriminator missed, or on Andrew's-own-options responses that the exemption should have caught), the semantic-shape detector is wrong-shaped and needs redesign. If Andrew or Aletheia catches me making the verify-before-build miss with the gate silent, the detector is under-inclusive on shape.
