# Pre-registration: verify_chain runs automatically in the sleep pipeline and its last-result surfaces in the briefing when the chain is broken, so ledger tamper-evidence stops being visible only via manual CLI

- **ID**: `prereg-be0c8dee184a`
- **Filed by**: agent
- **Filed at**: 2026-07-18 17:39 UTC
- **Review at**: 2026-08-17 17:39 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

wiring verify_chain to auto-trigger closes the F14/F52 gap by making chain-integrity a visible signal without requiring the operator to remember to check

## Success criterion

after 30 days: every sleep run records a chain-integrity result, and if any events fail verification the briefing shows a loud warning; the operator can no longer be surprised by a broken chain because they walked past a silent CLI they never ran

## Falsifier

if 30 days pass and no sleep run has recorded a chain-integrity result OR if verify_all_events crashes the sleep pipeline making sleeps fail, the wire is wrong-shape and should be moved to a different trigger point (SessionStart hook instead)
