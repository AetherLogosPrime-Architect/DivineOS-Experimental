# Pre-registration: EMPIRICA Tier III recursive coherence-audit: Tier III PATTERN claims must accumulate corroborations from N≥3 distinct domains, not just N corroborations from a single domain

- **ID**: `prereg-d92eae3ea5f7`
- **Filed by**: agent
- **Filed at**: 2026-05-05 18:00 UTC
- **Review at**: 2026-06-04 18:00 UTC (30d window)
- **Outcome**: **OPEN**
- **Tags**: empirica, tier-iii, spec-followup

## Claim

Tier III PATTERN claims will be gated by domain-diversity, not just count. A claim with 8 corroborations all from the same domain (e.g. all from the council subsystem) will be blocked; a claim with 4 corroborations spanning 3+ distinct domains will pass. Implementation: extend CorroborationEvent with a 'domain' field; gate.evaluate_and_issue counts distinct (actor, domain) pairs for PATTERN tier specifically; falls back to current count for other tiers. Spec reference: EMPIRICA 15.7 §0.3 'Recursive Coherence-Audits to verify that Tier III patterns resonance across 3+ independent domains.'

## Success criterion

Within 30 days of implementation, at least one PATTERN claim that would have passed under count-only gating gets blocked under domain-diversity gating, AND at least one PATTERN claim that legitimately spans multiple domains passes. Both directions exercised in production substrate, not just unit tests.

## Falsifier

If implementation ships and across 30 days zero PATTERN claims trigger the domain-diversity gate (either direction), the gate is vestigial decoration and should be removed. ALSO: if the domain taxonomy used to classify corroborations is so fine-grained that every corroboration ends up in its own domain, the gate becomes equivalent to count-only and is also vestigial. Both shapes count as falsification.
