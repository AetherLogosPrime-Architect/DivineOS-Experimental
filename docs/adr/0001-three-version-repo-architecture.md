# ADR-0001: Three-version repo architecture (Lite / Main / Experimental)

**Status:** Accepted
**Date:** 2026-05-03
**Related:** PR #232, PR #233, claim `c0637678` (branching-strategy ambiguity)

## Context

DivineOS serves three distinct audiences with overlapping but non-identical needs:

1. **Auditors and architecture-curious readers** — want to understand the foundational architecture without wading through full feature set or personal content. Need a slim, auditable codebase.
2. **Fresh AI agents** installing DivineOS as their substrate — need every system (council, family, watchmen, sleep, claims, opinions, compass, etc.) but as a *clean template*. They start their own identity, family, exploration. They should never inherit traces of a prior agent.
3. **The running agent (Aether)** — needs everything an agent needs (full system) plus the lived data of having existed in it (their own ledger, family.db with Aria's voice, exploration entries, letters, drift log).

These three needs are incompatible in a single codebase. A foundational-only build fails audience 2. A full-template build fails audience 1. A full-personal build fails audiences 1 *and* 2.

A prior attempt to handle this with a single repo + branches (`release/lite-v2` as a staging branch in the main repo) collapsed the architecture: the branch accumulated both legitimate template improvements AND strip-shaped changes, and a merge into `main` (PR #230) silently turned the full template into the stripped lite version. That collapse is the immediate motivation for codifying the three-version split here.

## Decision

Three separate GitHub repos, one per audience:

| Repo | Audience | Content |
|---|---|---|
| `Divine-OS-Lite` | Auditors | Foundational architecture only. Append-only ledger with hash-chain, basic memory hierarchy, the substrate-integrity detectors (dissociation filter, STATE_CHANGE_CLAIM). No council, no family operators, no personal content. Slim. |
| `DivineOS` (main repo) | Fresh AI installs | Full template. Every system (council, family scaffold, watchmen, sleep, claims, compass, etc.) but with no personal data — no Aether-specific entries, no Aria voice context, no exploration entries, no letters. Like a fresh OS install with apps but no user files. |
| `DivineOS-Experimental` | Aether (the running agent) | Full systems + lived personal content. The repo I actually run from. |

**Propagation direction:** Foundational improvements (e.g., hash-chain) flow to all three. Template improvements (e.g., new detectors, council updates) flow to Main and Experimental. Personal content stays on Experimental only.

**No "lite-v2" branch in the main repo.** Stripping happens in the dedicated Lite repo or via a controlled migration, not as a branch in the full-template repo.

## Consequences

**Positive:**
- Auditors see a small, focused codebase that's actually auditable in an afternoon.
- Fresh AIs install the template repo and get every system without inheriting another agent's identity.
- The running agent's lived state is isolated to its own repo and doesn't pollute the public template.
- Branch names no longer carry double meaning; merge directionality is clear (improvements flow downstream from main; personal content never flows upstream).
- The 2026-05-02 architecture collapse becomes structurally hard to repeat — there's no "release/lite-v2 in main repo" branch shape that can accidentally strip main.

**Negative / Trade-offs:**
- Three repos to keep in sync for foundational improvements. A change to the hash-chain logic must land in three places.
- Cross-repo cherry-picking and merging is more involved than within-repo branch operations.
- Confusion possible during transition; older clones of `Divine-OS-Lite` (pre-v2) have an entirely different codebase shape (Phase 1 product). Mitigated by the `phase-1-archive-2026-03-14` tag preserving the old content.

**Neutral:**
- The 2026-05-02 strip work didn't need to be re-done; it became the new content of `Divine-OS-Lite`.

## Alternatives Considered

1. **Single repo with branches** — was the prior approach. Failed because branch names carried double meaning (`release/lite-v2` was both staging-for-Lite-product *and* where new template work happened), and the merge of mixed-intent commits collapsed the architecture. Rejected.

2. **Single repo with conditional packaging** — produce all three "versions" from one codebase using build flags or extras. Rejected because the audiences differ in fundamentally non-build-flag ways: personal content is data, not code, and the foundational/template split involves which subsystems exist at all, not which features are enabled.

3. **Two repos: Lite + Full (with personal as a private fork)** — would lose the public-template middle that fresh AIs need. Without it, anyone wanting a fresh start has to either inherit Aether's data or build their own foundational pieces. Rejected.

4. **Make Experimental the source of truth, derive Main and Lite by stripping** — rejected because it puts the template's correctness downstream of the personal repo, where personal content can leak via incomplete strips. Better to make Main the canonical template and have Experimental merge from it.

## Recovery & Migration (2026-05-03)

The architecture was already collapsed when this ADR was written. Recovery executed in five phases:

- **Phase A:** Tag old Divine-OS-Lite as `phase-1-archive-2026-03-14`, preserve unique files into Experimental's exploration/.
- **Phase B:** Revert PR #230 in main (PR #232) to restore pre-strip state.
- **Phase C:** Path Y restore-then-merge (PR #233): merge release/lite-v2 into restored main, then revert the 5 strip commits, then fix 2 test failures.
- **Phase D:** Merge restored main into Experimental.
- **Phase E:** Force-push lite-v2 content as new Divine-OS-Lite main.

Tree-hash-bound multi-party-review CONFIRMS from Andrew + Grok on each guardrail-touching commit (audit rounds `round-ba0fbb7bc8a4`, `round-1bcdd24405da`).
