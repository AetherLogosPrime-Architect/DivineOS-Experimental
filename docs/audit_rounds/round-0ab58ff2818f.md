# Audit round: F90 fix: liveness preamble in _lib.sh + inline pre-source logging in 3 hooks (correction-shape-v2-stop, closure-word-summary-prime, keyword-enforcement-doorman). Per Aletheia F94/F90 audit 2026-07-28. Diff-hash: 9597026dbc1749860595a769832451f4924a5c798cfcadc2abf6ccfd1d95b07c

- **ID**: `round-0ab58ff2818f`
- **Filed by**: user
- **Filed at**: 2026-07-28 17:35 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: feat/derive-keyword-registry-and-shared-preamble-2026-07-28


## Findings

### PR #397 user-CONFIRMS: F94/F90/F95 audited and ready to merge

- **ID**: `find-dd1c0c34330d`
- **Actor**: user
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: cd6c902f-35a7-47de-97a2-981c304d9227
- **Tags**: CONFIRMS

**Description**

Andrew's user-CONFIRMS filed on standing verbal authorization 2026-07-28: 'me saying i confirm.. and i do.. is enough for you to file it on my behalf.. it means that i witnessed the draft audited by Aletheia.. changes were made and reposted and its ready for main.. does that mean its 100% correct? or we caught everything? no.. but it means it works well enough.. and if it breaks we fix it and try again.' Attests witnessing the audit cycle: draft opened, Aletheia audited from her window (find-c7235674c091), fixes applied per her F94/F90/F95 findings + F97 escape-valve framing, ready for merge to main. Code-is-clay principle: 100% correctness not required for merge; forward iteration is the recovery path.

### F94/F90/F95 fix reviewed on origin @ 341d88c

- **ID**: `find-c7235674c091`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 7327cda0-00e6-43e7-902b-f268472bc6d8
- **Tags**: CONFIRMS

**Description**

Verified by content on origin/feat/derive-keyword-registry-and-shared-preamble-2026-07-28 @ 341d88c, two independent checks per claim. F94 CLOSED: registry derived structurally, composition (derived|hand_added)-excluded with derived as base so the hand-list can only add coverage; predicate requires compiled-regex AND detector-signature, not filename heuristic; doorman invokes matches_registry which calls derive_registry; registry module carries __guardrail_required__ and is listed in guardrail_files.txt, satisfying the 2026-05-29 META-LAW that a guard must enforce itself. F95 CLOSED: exclusion file guarded in guardrail_files.txt and tripartite format enforced, with the correct fail direction -- malformed lines drop so the exclusion does NOT take effect, meaning the escape valve fails toward keeping gates in coverage; parser separated to keep the registry's structural signature clean. F90 SUBSTANTIALLY CLOSED: heartbeat invoked at end of _lib.sh on every successful source, covering 73 of 89 hooks with no per-hook code, so an empty liveness log is now diagnostic rather than ambiguous. Inline pre-source logging landed in 3 of 89 hooks and NOT in verify-before-build-signal.sh where F90 originated; stays OPEN at LOW for coverage. Note: source-failure logging is structurally per-hook -- _lib.sh cannot report its own failure to load -- adoption-limited by nature, template/lint candidate. Substantive review: AUDIT_2026-07-28_six-PR-queue-F95-and-F90-partial.md + CONFIRMS_2026-07-28_round-0ab58ff2818f.md. Attested-shape: I have no CLI access; Aether filed this verbatim per my written instruction, as I cannot execute divineos commands from my window.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
