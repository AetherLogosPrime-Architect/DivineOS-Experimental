# Pre-registration: per-clone data-home separation via .divineos_data_home marker + bidirectional checkout-owner verification + junction-shared family.db

- **ID**: `prereg-f6a7d7ee5adb`
- **Filed by**: agent
- **Filed at**: 2026-05-17 17:18 UTC
- **Review at**: 2026-05-24 17:18 UTC (7d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-05-24 22:15 UTC

## Claim

Two DivineOS checkouts pointing at different .divineos_data_home destinations will maintain full separation of identity, event_ledger, and knowledge.db while sharing family.db and family/letters/ via junction. The bidirectional checkout_owner marker will fail-loud if a clone tries to read from a data-home owned by a different checkout.

## Success criterion

Running divineos doctor verify-clone-separation --partner OTHER from each clone returns all 5 falsifiers passing: identity_differs, ledger_separated, letters_shared, family_db_shared, knowledge_separated. The CLONE_SEPARATION_VERIFIED ledger event records the result.

## Falsifier

Any of: (a) identity slot in clone A returns clone B identity; (b) a TEST event logged in A appears in B context; (c) a learn entry in A appears in B ask; (d) a letter in A is invisible from B; (e) family.db file sizes diverge between clones; (f) the checkout-owner check fails to fire when a misconfigured clone tries to mount a data-home owned by the other checkout.

## Outcome notes

Assessed 2026-05-24 (just overdue, +0.2d). Mechanism shipped: divineos doctor verify-clone-separation exists (the 5-falsifier Popper suite: identity_differs, ledger_separated, letters_shared, family_db_shared, knowledge_separated). But the success criterion requires running it with --partner OTHER from EACH of two configured clones; I am in a single checkout and cannot execute the two-clone suite solo this session. No falsifier observed (nothing failed) — but unverifiable alone. Recommend KEEP OPEN / re-review when a second clone is configured and the partner run can execute. Not FAILED (no negative evidence), not SUCCESS (success test not runnable).
