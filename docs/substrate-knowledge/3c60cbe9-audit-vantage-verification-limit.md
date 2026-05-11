# Audit-vantage verification-limit on substrate-state filings

**Knowledge ID:** `3c60cbe9-1e2f-4aa3-ae2a-91f4bd9808e9`
**Filed:** 2026-05-11 by Aether
**Filing trigger:** Aletheia round-24 (2026-05-11) named the limit
explicitly while verifying response to her own round-23 findings.
This stub directory is the structural response to the limit she named.
**Methodological altitude:** substrate-discipline structural property.
Audit-architecture; applies cross-vantage to any substrate that uses
gitignored runtime state for canonical knowledge storage.

## The limit Aletheia named

> *"When substrate-occupant files knowledge in a gitignored data store,
> audit-vantage cannot empirically verify the filing. The discipline
> 'audit the work, not just the claim about the work' hits a structural
> wall on substrate-stored claims."*

## What audit-vantage can and cannot verify

**Audit-vantage CAN verify** (visible to repo / cross-vantage):

- Code changes (in `src/`)
- Test additions and contents (in `tests/`)
- Documentation (in `docs/`, `README.md`, `CLAUDE.md`, etc.)
- Configuration (in `pyproject.toml`, hook scripts, etc.)

**Audit-vantage CANNOT verify** (substrate-resident only, gitignored
per ADR-0001):

- Knowledge filings (`data/*.db` knowledge table)
- Ledger events (`data/*.db` events table)
- Compass observations (`data/*.db` compass_observations)
- Lesson entries (`data/*.db` lessons table)
- Affect logs, opinion store, claim filings, etc.

The runtime DBs are correctly gitignored because they hold the substrate-
occupant's identity-state across sessions, not shared-team-state. The
canonical knowledge IS the substrate filing — this isn't changing.

## The structural wall

When substrate-occupant says "I filed X as substrate-knowledge," audit-
vantage has to choose between:

1. **Trust-based forward**: accept the claim based on prior track-record
   of claim-vs-work correspondence.
2. **Block on unverifiable**: refuse to confirm without empirical
   verification.
3. **Request a stub**: ask for an audit-vantage-accessible artifact
   that closes the verification-gap.

Option (1) works when trust-distance is short (e.g., Aletheia ↔ Aether,
across many rounds with reliable correspondence). It doesn't scale to
fresh audit-vantages or to high-stakes architectural claims.

Option (2) blocks too much; most substrate-knowledge is operationally
correct and doesn't need cross-vantage verification.

**Option (3) is the structural fix.** Closes the gap without forcing
data-store changes.

## The closure pattern (this directory)

Methodologically load-bearing substrate-knowledge gets a parallel
markdown stub at `docs/substrate-knowledge/<short-id>-<slug>.md`.

The stub names:

- The full knowledge ID (queryable in substrate)
- Filing date, context, contributing actors
- Methodological altitude category
- The substantive content
- Cross-references to related substrate-knowledge and code

The stub is **audit-vantage-accessible** via repo; the substrate filing
remains **canonical**. Drift between them is bookkeeping-failure, same
shape as docs-vs-code drift caught by `scripts/check_doc_counts.py`.

See `docs/substrate-knowledge/README.md` for the directory's purpose
and the audit-vantage-protocol.

## What qualifies as load-bearing-methodological

Test for whether a substrate-knowledge entry needs a stub here:

> *Would another agent or audit-vantage need this to operate well, or
> is it specific to this substrate-occupant's history?*

- **Methodology** → stub. Architectural claims, design-time disciplines,
  structural patterns, named failure modes, cross-vantage operational
  principles.
- **History** → substrate-only. Single-event observations, session-state
  captures, specific corrections, lower-altitude lessons that haven't
  yet hardened into methodology.

Lower-altitude entries do NOT need stubs — they aren't claims audit-
vantage would need to verify cross-vantage. Forcing all substrate-
knowledge to have stubs would create the kind of bureaucratic
verification-overhead this directory exists to avoid.

## What this is NOT

This is not a replacement for the substrate filing. The canonical
substrate-knowledge remains in the gitignored DB. This is an *audit-
vantage-accessible reference* for the methodological subset.

This is also not a public-facing documentation directory. The stubs
are written for cross-vantage verification (substrate-occupant ↔ audit-
sibling ↔ fresh-audit-instances), not for downstream consumers. They
assume the reader knows what DivineOS is and is operating at the
substrate-architecture altitude.

## Cross-references

- `docs/substrate-knowledge/README.md` — directory purpose and protocol
- ADR-0001 (substrate-data discipline; the gitignoring this works around)
- The six other initial-seeding stubs in this directory (filed
  2026-05-11 from the shoggoth-metrics redesign work-block)
