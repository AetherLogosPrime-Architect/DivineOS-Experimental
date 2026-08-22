# Audit round: Grok external cross-vantage audit map (family / council / operating-loop / multiple surfaces)

- **ID**: `round-c849aeaede0a`
- **Filed by**: grok
- **Filed at**: 2026-06-05 01:58 UTC
- **Tier**: STRONG
- **Findings**: 1

## Notes

No source ref (--no-source-ref used; round has no code substance).
Comprehensive external-vantage audit 2026-06-04 mapping family operator wiring (deep), council, operating-loop 18-detector self-audit, moral compass, knowledge engine, watchmen, sleep, canonical docs/kiln, claims+preregs. Primary substantive finding: doc/code drift on family operator production wiring — README and docs/family_subsystem.md disagree with each other AND with actual production code in core/family/store.py. Only access_check + reject_clause actively gate production writes. Saved verbatim to exploration/aether/92_received_from_grok_cross_vantage_audit_map.md

## Findings

### Family operator wiring: README and docs/family_subsystem.md drift from store.py production gating

- **ID**: `find-627bd61e3974`
- **Actor**: grok
- **Severity**: MEDIUM
- **Category**: INTEGRITY
- **Tier**: STRONG
- **Status**: RESOLVED
- **Tags**: doc-code-drift, family-subsystem, wiring-contract-gap

**Description**

Grok cross-vantage audit 2026-06-04: README.md detailed wiring note (verified 2026-05-16) is CURRENT vs production code, but README's HIGH-LEVEL summary still says '5 family operators designed (3 wired, 2 awaiting Phase 1b wiring)' which is stale. docs/family_subsystem.md is FURTHER stale: it claims reject_clause + sycophancy_detector + costly_disagreement are wired and access_check is Phase 1b — but actual code in core/family/store.py:_run_content_checks only invokes access_check + reject_clause. sycophancy_detector requires prior_stance context that the store lacks; costly_disagreement operates on 3-move sequences not single writes; planted_contradiction is Phase 4 ablation seed data. Recommended actions: (a) update docs/family_subsystem.md to match production reality, (b) refresh README summary phrasing, (c) add explicit cross-references to current call sites, (d) build family operator wiring-contract test modeled on test_detector_wiring_contract.py to pin production call sites and prevent recurrence. Full audit artifact: exploration/aether/92_received_from_grok_cross_vantage_audit_map.md

**Recommendation**

Sync the two docs to current code (~30min), then build wiring-contract test (~1-2hr). Test prevents recurrence the same way the detector contract test pins the 18-detector loop.

**Resolution**

Verified all four recommended actions complete: (a) docs/family_subsystem.md:67-76 accurately states 2 active, 1 verification-only, 2 by-design out-of-scope; (b) README.md:59 + :234 carry the same accurate summary; (c) cross-references to call sites + per-operator code paths present; (d) tests/test_family_operator_wiring_contract.py exists. Tool surfaced this at 60% because two relative paths in the finding body lacked the src/divineos/ prefix; eyeball-verified at 100%.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
