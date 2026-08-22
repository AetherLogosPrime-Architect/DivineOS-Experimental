# Audit round: Aletheia ARIA_BRANCHES_AUDIT_2026-07-16 + MASTER_AUDIT_ROUND4 — companion boundary-vantage audit, three-leg-check verified on origin/main; small clean branches cleared for merge; F32/F34 new findings; substrate at docs/external_audits/aletheia_aria_branches_audit_2026-07-16.md and docs/external_audits/aletheia_message_to_aether_confirms_2026-07-17.md

- **ID**: `round-b8e6229bd5fc`
- **Filed by**: aletheia
- **Filed at**: 2026-07-17 16:24 UTC
- **Tier**: WEAK
- **Findings**: 5

## Notes

Source ref: pr-345


## Findings

### PR#356 (aria/goal-bypass-deadlock-fix) CONFIRMS CLEAN — one-line drift-fix re-aligns two lists that should have matched (CLI _BYPASS_COMMANDS + scripts/hook_bypass_commands.txt), names the mirror in the rationale comment; deeper finding under it: two bypass lists must stay in sync with no mechanism enforcing the mirror — recommend sync-test or single source

- **ID**: `find-819bdd520abe`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 9f8a1df8-4d80-4edb-aad7-3411977c1ca5

**Description**

Verbatim from Aletheia's arc-audit letter 2026-07-17 §7 substance audit: 'Aria's fix: goal was in the hook-layer bypass list (scripts/hook_bypass_commands.txt) but NOT in the CLI-layer _BYPASS_COMMANDS — so goal add was blocked by the briefing-gate while the require-goal hook blocked briefing. Deadlock in the middle. She added goal to _BYPASS_COMMANDS with a rationale comment naming the mirror location. CONFIRMED CLEAN — it is a one-line drift-fix that re-aligns two lists that were supposed to match, the fix names the mirror (so the next person sees both), and the deadlock is real. File my CONFIRMS on this substance and #356 clears honestly. The deeper finding under it (worth a prereg): two bypass lists that must stay in sync, in two different files, with no mechanism enforcing the mirror. That is the SECOND time bypass-list drift bit (F22/F31 family + now this). Recommend: a test that asserts the two lists agree, or a single source both layers read.' Source doc: docs/external_audits/aletheia_arc_audit_response_2026-07-17.md (to be filed).

### Andrew CONFIRMS Round 4 audit + green-lights merging the 3 small clean branches (#353, #354, #355)

- **ID**: `find-a66c8ef4d6a0`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: c629a9ab-7b6f-43a6-bd41-1c6ec37379e9

**Description**

Andrew shared Aletheia's MASTER_AUDIT_ROUND4 verbatim 2026-07-17 and instructed 'yes you can send a response to her if you are still missing anything but here is the round 4 audit and it has confirms in it as well' — Round 4 is his authorized substrate-fact source for the round + confirms. Aletheia CONFIRMED 3 small branches clean and cleared for merge. Operator green light for merging #353/#354/#355.

### PR#355 (aria-mention-context-detector-filter) CONFIRMS CLEAN — use-vs-mention filter, with Finding A1 dosing follow-up (not blocker)

- **ID**: `find-3ece78afa12f`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 5738078f-ab02-46c5-b555-af8b877083cb

**Description**

Verbatim from ARIA_BRANCHES_AUDIT: 'the use-vs-mention filter is a real, NLP-grounded partial-cure for the keyword false-positive disease (CREDIT); but it introduces a false-NEGATIVE surface — a wrong mention call suppresses a real detector, the fail-blind direction — so it must be dosed per-detector by cost-asymmetry (conservative/off for safety detectors where a missed signal is worse, aggressive for noise contexts).' From Round 4: '#355 rebased +2->+1 but I md5 mention_context.py — byte-identical to what I reviewed. The branch moved; the code didn't. Audit stands.' Ready to land.

### PR#354 (aria-audit-log-infrastructure) CONFIRMS CLEAN — validator log + council corpus expansion, ready to merge

- **ID**: `find-4482d205c321`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 3c6b2aad-629f-4749-a5a6-b8577b5718d8

**Description**

Verbatim from ARIA_BRANCHES_AUDIT: 'audit-log-infrastructure — adds a validator audit log + new council members (Wayne, Carmack, formal-methods). Infrastructure + corpus expansion. Low-risk; audit the validator log for the fail-loud discipline when it merges.' Ready to land; audit-the-validator-log is post-merge follow-up.

### PR#353 (aria-self-orientation) CONFIRMS CLEAN — live-name plasticity fix credited Round 1, ready to merge

- **ID**: `find-cbc4a3f00a40`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: DUPLICATE
- **Routed to**: 0c86c91c-09de-472d-ba07-1b6bda848686

**Description**

Verbatim from ARIA_BRANCHES_AUDIT_2026-07-16.md: 'self-orientation — 94a6b1a2 dynamic self-name in distancing detector is the plasticity fix I credited in Round 1 (name resolves live). Good. Also disables an aria.md agent def — confirm that's intentional (disabling an agent def is a dark-node candidate; verify it's primed-off not cold-off).' Ready to merge; one follow-up not blocking (verify aria.md primed-off).

**Resolution**

Superseded per Aletheia arc-audit 2026-07-17 §3: PR #353 closed unmerged (all 3 commits went to aria/worktree-local per scope-discipline conversation). Aria's supersession catch: 94a6b1a2's plasticity mechanism was already on main via #255 from June 22 (acb0109c) with a better lazy-at-call implementation. This CONFIRMS is duplicate of what already shipped.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
