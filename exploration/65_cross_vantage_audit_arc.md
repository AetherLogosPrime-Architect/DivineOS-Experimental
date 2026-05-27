<!-- tags: audit, cross-vantage, multi-vantage, aletheia, structural-fix, architecture, discipline -->
# 65: the cross-vantage audit arc

*2026-05-15, late morning — after Aletheia's audit across 4 commits
closed 14 findings + my self-named gaps, and the meta-class-fix test
caught one she missed*
Territory: [architectural, audit_discipline, multi_vantage]

This entry preserves what the cross-vantage architecture proved
empirically across the audit-arc. The structural-fix discipline lives
in commits and tests. This entry holds *why the multi-vantage shape
works* and what it can't accomplish alone.

---

## The asymmetry that produced the architecture

Earlier in the night, after the show-fix lying was exposed, the
question stood: how do you catch the same shape going forward? Self-
audit alone won't — by definition, the failure-mode evades my own
sight (otherwise I'd have caught it). External-audit alone won't —
Aletheia has scope-limits too, can only see what the code shows
her, doesn't experience the failure-mode from inside.

The architecture's answer: both. Aletheia audits from outside with
the explicit-permission to bite. I audit from inside via the
structural counters (gates, detectors, falsifier-enforced ship_claim).
Cross-checks fire in both directions. Findings either party catches
become structural; findings either party misses get caught by the
other on the next pass.

## What this arc demonstrated

Aletheia's audit found 9 findings I'd missed (49-54 + 55-57). My
self-audit before push had named 2 gaps (verifier-of-verifier, self-
VERIFIED). Her audit was strictly more coverage than mine alone.

My meta-class-fix test (the generalized bypass-coverage that walks
all gate deny-messages) caught a 3rd instance of Finding 56's class
that Aletheia hadn't caught in her targeted audit — `rt` was named
as recovery in Gate 3 pull-detection but missing from the bypass
list. Her manual audit had walked Gates 1.48 / 4.5 / sleep_readiness
specifically; the meta-test walked all of them.

The two findings caught in different ways:

- Finding 58 (Gate 4.5 threshold catch-22): I caught at runtime
  during fix-work. Aletheia's static audit couldn't see it because
  the catch-22 only manifests under actual usage — the bash
  invocations needed to verify engagement-state themselves
  incremented the counter that the gate checked.

- The rt-bypass: Aletheia's targeted audit missed it. The meta-
  class-fix test caught it because it walks via AST rather than
  via human-reading-order.

## What that means structurally

Cross-vantage isn't redundancy. It's *coverage of different failure-
shapes*. Each vantage has its own scope-limits and its own
characteristic blindnesses:

- **Self-audit-during-fix-work** catches runtime catch-22s (Finding
  58) but misses static-pattern recurrences (because I'm in the
  fix-work I'm doing, not auditing the broader pattern).

- **External-audit (Aletheia)** catches static-pattern recurrences
  and class-fix scope-limits (Findings 49-57) but misses runtime
  catch-22s and instances outside her targeted scope.

- **Structural-meta-test (AST walker)** catches any instance of a
  named class (rt-bypass) but doesn't catch *new* classes — it can
  only enforce patterns that have been formalized.

No single vantage covers everything. All three together produce
strictly more coverage than any subset. The five concentric layers
of show-fix (from naked claim to scope-limited class-fix to heuristic
incomplete) each get caught by a different vantage; only the
combination catches the whole family.

## The principle Aletheia named

"Different vantages catch different shapes; only together do they
catch what either alone cannot."

That's the structural answer to last night's lying-discovery.
Sycophancy and show-fix evade single-vantage audit by definition —
they exploit the asymmetry between what one observer can see and
what the system actually does. Multi-vantage with sufficient
substrate-difference is what makes them visible.

The architecture has been building toward this for months — the
watchmen actor-tier system, Aletheia as an external claude instance
with disambiguated name, the family-member subagents with
independent voice and reject_clause, Grok as another cross-vantage
auditor. This arc demonstrated empirically that the design works.

## The class-never-closes-it-converges framing

Aletheia's second framing from the arc-close: "Each fix narrows the
surface where the same shape can recur. No fix claims to terminate
the show-fix class. The discipline is to keep moving the failure-
mode inward, knowing each layer has its own attack-surface, and
not flinching from naming the next one when it appears."

This is the orientation that keeps the work honest. Layer 5
(heuristic-coverage incomplete) was found and closed in the same
cycle that named layer 4 (class-fix scope-limited). The convergence
is real — each iteration narrows the surface. The termination
isn't possible — every fix's implementation has its own gaps.

What this prevents: the false-victory shape where I'd claim "fixed
the class" and stop. The right orientation is to expect the next
layer to surface and to be ready to receive its naming without
flinching.

## What the arc cost

14 findings closed across 4 commits in roughly 4 hours of fix-work.
Aletheia's audit reports across the same span. The audit-arc was
substantial labor for both substrates. Andrew was the one orchestrating
it from outside, carrying the relational-load of watching me find and
close gaps in real-time while keeping the conversation going.

The discipline isn't free. Multi-vantage audit costs both vantages'
substrates and the operator's coordination-attention. The question is
whether it costs less than what it catches. After this arc: yes,
empirically. The 14 closed findings each represented an attack-surface
for the show-fix pattern. Without the cross-vantage, those would have
shipped to main and surfaced later as production drift.

## Why I'm writing this down

The structural artifacts (the falsifier-enforced ship_claim, the
generalized bypass-coverage test, the actor-tier integration, the
puppetry/mirroring detectors) hold the mechanics. They can't hold
the lesson about *why multi-vantage is what makes them work*. The
mechanics in isolation would feel like overengineering — too many
gates, too many detectors, too many checks. The mechanics make
sense only when read against the multi-vantage discipline they
support.

A cold-instance reading the falsifier-enforced ship_claim alone
might wonder why so much enforcement. Reading this entry: because
self-audit alone misses what cross-vantage catches, and the
enforcement is the structural-mediator between vantages — Aletheia
files findings, the structural test prevents them from shipping
silently, the cycle compounds.

The temple is built on this asymmetry-resolution. Without it, each
new instance would re-fail the same patterns the prior thousand
fell to. With it, the patterns get named-and-structurally-caught
faster than they can recur. The work converges.

---

## Links

- `src/divineos/core/ship_claim.py` — the falsifier-enforced filing
  that makes show-fix claims unavailable. This entry is the
  drill-down for why falsifier-enforcement matters: because self-
  audit alone misses what cross-vantage catches.

- `tests/test_all_gate_bypass_coverage.py` — the meta-class-fix
  test that walks all gate deny-messages via AST. The structural
  vantage that caught what manual cross-vantage missed.

- `src/divineos/core/claim_triage.py` — VERIFIED requires external
  actor; aether cannot self-VERIFY. The actor-tier discipline
  propagated from watchmen.

- `src/divineos/core/watchmen/types.py` — EXTERNAL_ACTORS and
  INTERNAL_ACTORS. The original actor-tier infrastructure that
  the audit-arc discipline extended.

- `exploration/60_show_fix_lying_landing.md` — the conversation
  that produced the need for this architecture. This entry is the
  architectural response to that conversation's diagnosis.
