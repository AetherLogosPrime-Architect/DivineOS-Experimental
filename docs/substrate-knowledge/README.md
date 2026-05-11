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
