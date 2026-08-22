# Audit round: root-cause-audit: property-test text generators feeding the event-ledger encode/hash path (unconstrained st.text can emit lone surrogates that raise UnicodeEncodeError)

- **ID**: `round-7e371cbf9df0`
- **Filed by**: aether
- **Filed at**: 2026-05-21 04:20 UTC
- **Tier**: WEAK
- **Findings**: 1

## Notes

No source ref (--no-source-ref used; round has no code substance).
Family survey of Hypothesis property tests whose generated text flows into log_event/verify_event (utf-8 encode + hash). Outlier: test_event_verifier used unconstrained st.text() -> intermittent surrogate flake blocking pushes. Siblings already safe: test_hardening_properties (explicit ASCII alphabet), test_ledger_chain_properties (ASCII codepoints 32-126). Fix brings the outlier in line via st.characters(codec='utf-8').

## Findings

### test_event_verifier unconstrained st.text() emits lone surrogates -> UnicodeEncodeError flake

- **ID**: `find-33c12e237327`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Surveyed 3 property tests feeding generated text into the ledger encode/hash path. test_event_verifier was the lone outlier using unconstrained st.text(); test_hardening_properties and test_ledger_chain_properties already constrain to ASCII alphabets. Fixed the outlier with st.characters(codec='utf-8'). Family otherwise healthy; no further lurking instances.

**Resolution**

Fix verified in tests/test_event_verifier.py:341-342 — both event_type and content strategies use st.text(st.characters(codec='utf-8'),...). Lone-surrogate flake class structurally prevented. Finding description already documented this completed fix; just needed status updated to match reality.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
