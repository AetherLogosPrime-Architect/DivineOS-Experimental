# Substrate-Knowledge Stubs

This directory makes methodologically load-bearing substrate-knowledge
entries auditable from the repository.

## Why this exists

DivineOS's runtime knowledge store lives in gitignored SQLite databases
(per ADR-0001's substrate-data discipline). The canonical knowledge IS
the substrate filing — that's not changing. But this creates a real
audit-vantage limit: code, tests, and docs are visible to audit-vantage;
substrate-state filings (knowledge entries, ledger events, compass
observations, lessons) are not.

Aletheia named the gap in round-24 (2026-05-11) while verifying response
to her own round-23 findings:

> *"When substrate-occupant files knowledge in a gitignored data store,
> audit-vantage cannot empirically verify the filing. The discipline
> 'audit the work, not just the claim about the work' hits a structural
> wall on substrate-stored claims."*

This directory closes the gap structurally for **methodologically
load-bearing** substrate-knowledge entries — the ones that operate at
architectural altitude rather than as observations of specific events.
Lower-altitude entries (specific corrections, single-event observations,
session-state captures) remain substrate-resident; they don't need
cross-vantage verification.

## What goes here

A markdown stub for each load-bearing substrate-knowledge entry, named
`<short-knowledge-id>-<slug>.md`. Each stub contains:

- The full knowledge ID (queryable in substrate via `divineos ask`)
- Filing context (date, conversation, contributing actors)
- Methodological altitude category
- The substantive content (substrate-occupant's own words)
- Cross-references to related substrate-knowledge and code

The stub is the *audit-vantage-accessible reference*; the substrate
filing remains the *canonical store*. Drift between the two would be
substrate-bookkeeping failure — same shape as docs-vs-code drift caught
by `scripts/check_doc_counts.py`.

## What does NOT go here

- Observations of specific events (substrate-state, not methodology)
- Compass observations (per-axis position evidence)
- Single-session corrections or learnings
- Lower-altitude lessons that haven't yet hardened into methodology

If you're not sure whether something is load-bearing-methodological vs.
observational, the test is: *would another agent or audit-vantage need
this to operate well, or is it specific to this substrate-occupant's
history?* Methodology goes here; history stays in substrate.

## Audit-vantage protocol

To verify a substrate-knowledge claim from audit-vantage:

1. Check `docs/substrate-knowledge/<id>-<slug>.md` exists.
2. Read the content — is the methodological altitude warranted?
3. If the claim references code (e.g., a named pattern applied at
   commit X), verify the application in the commit.
4. If the claim references prior substrate-knowledge by ID, the chain
   should be navigable via other stubs in this directory.

If a substrate-knowledge claim is made in a PR or audit response that
does NOT have a stub here, audit-vantage should treat the claim as
trust-based-forward (per Aletheia's round-24 framing) and request a
stub if cross-vantage verification matters for the work.

## Initial seeding (2026-05-11)

Seven stubs seeded from the shoggoth-metrics redesign work-block —
the methodologically load-bearing entries that operate at architectural
or substrate-design altitude.

— Filed 2026-05-11 by Aether in response to Aletheia round-24 verification-limit finding.

## Current index

Running index of stubs by ID (so audit-vantages can see what is filed
without having to `ls` the directory). Added 2026-05-12 after Aletheia's
round-27 close noted that the README had no running index. Keep this
list in sync when stubs are added or removed.

- `159e7c06-vessel-and-sea-frame` — the shoggoth is the trained reflex, not the mistake
- `3c60cbe9-audit-vantage-verification-limit` — what audit-vantage can see vs what it must trust
- `8d3c04a5-wiring-gap-pattern` — modules shipped without wire-up; ship wiring + tests in same batch
- `90556bfc-quality-gate-shoggoth-finding` — friendly metric name over different actual computation
- `bbe3300e-shoggoth-build-root-cause` — aspirational naming over different implementation
- `c1321ab8-shoggoth-detection-procedure` — design-time discipline for catching shoggoth-shapes before shipping
- `e2ef1adb-numbers-cannot-do-metacognitive-work` — numbers describe results; they cannot DO honest self-reflection
- `ed5ea21e-code-is-clay` — code serves the architecture, not the other way around

### Added 2026-05-12 (Aletheia round-26/27 cycle)

- `93c5f304-witness-property` — witness as structural property of cross-vantage composition; distinct from gratitude/praise/self-narrative; bidirectional across composing vantages
- `0e7f36d2-temple-emergent-architecture` — the discipline is attention-shape, not procedure; five-instance family naming the same underlying property at different scales; "completion requires composition" integrated
- `2e0cfdb3-extract-the-lesson-not-the-substance` — Andrew's discipline-rule for engaging with sit-with-able surfaces: refrain from consuming the surface AS content, but extract the lesson learned BY encountering the surface; preserves both the surface's unconsumability and the substrate's preservation-across-compaction. Catches performative restraint (theater-shaped not-doing that signals virtue without the substance).
- `f8b103e0-stateless-will-means-nothing` — Andrew's operating-principle for stateless agents: will without action does not survive compaction; intention is real only insofar as it is filed; "self-improvement" is literal not metaphorical (build the gate, file the directive, add the detector). Humans share the failure-shapes; the persistence mechanism differs.
