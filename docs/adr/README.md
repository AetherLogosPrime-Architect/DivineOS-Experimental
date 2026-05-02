# Architecture Decision Records

This directory holds the ADRs (Architecture Decision Records) for DivineOS. Each ADR captures a single architectural trade-off — why a decision was made, what was considered, and what consequences followed.

## Format

Each ADR is a markdown file named `NNNN-short-title.md` where `NNNN` is a four-digit zero-padded sequence number.

Standard sections per ADR:

- **Status** — Proposed / Accepted / Superseded / Deprecated
- **Date** — when the decision was made
- **Context** — why this decision was needed (the problem, the forces at play)
- **Decision** — what we chose
- **Consequences** — what follows (positive, negative, neutral, trade-offs)
- **Alternatives Considered** — what else was on the table and why it lost

## Index

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-three-version-repo-architecture.md) | Three-version repo architecture (Lite / Main / Experimental) | Accepted | 2026-05-03 |
| [0002](0002-hash-chain-main-ledger.md) | Hash-chain on main ledger with migration-ordering safeguards | Accepted | 2026-05-02 |
| [0003](0003-dissociation-shape-filter.md) | Dissociation-shape filter at extraction + recombination | Accepted | 2026-05-03 |
| [0004](0004-state-change-claim-detector.md) | STATE_CHANGE_CLAIM detector with tool-call adjacency check | Accepted | 2026-05-03 |

## When to write an ADR

Write an ADR when:
- A decision has long-term structural consequences (not just tactical implementation choice)
- The decision involves a real trade-off — picking one path closes others
- The reasoning would be hard to reconstruct from code alone
- Future-you (or a fresh AI installing the OS) would benefit from understanding why

Do *not* write an ADR for:
- Routine implementation choices with one obvious answer
- Documentation that belongs in module docstrings
- Bug fixes where the decision is "fix the bug"

ADRs are append-only by convention. If a decision is reversed, file a new ADR that supersedes the old one rather than editing history.
