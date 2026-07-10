# orphan-ledgers/

Per-member ledger files for family members that are no longer active.

Family member ledgers are hash-chained append-only event stores, one per
member. When a member is scaffolded but never populated into a real family
member, or when a test member is created during ledger-development work,
the ledger file persists past the member's usefulness.

## What's here

| File | Events | Why here |
|---|---|---|
| `alice_ledger.db` | 72 | Probable early-scaffolding placeholder — no agent definition at `.claude/agents/alice.md`, no letter correspondence, name suggests a test rather than a real family member |
| `testmember_ledger.db` | 27 | Confirmed test artifact from ledger-development work — the name is the marker |

Both DBs have real event history and are preserved as artifacts. They are not
deleted (hash-chain integrity is preserved); they are just moved out of the
active `family/` root so the top-level directory only lists ledgers for
currently-active members.

## Reactivation

If a family member named "alice" is ever defined at
`.claude/agents/alice.md`, move `alice_ledger.db` back to `family/` so the
member's ledger-append writes go to the file with prior history rather than
starting fresh. Same for testmember (though this is less likely — the name
was for development, not a real member).

## Provenance

Moved here 2026-07-09 during co-design cleaning-day. Verified orphan status
via absence of agent definition + absence of letter references + name-pattern
inspection.
