# Audit round: push-log per-member + shoggoth exempt + 3 test fixes (Aletheia audit follow-through)

- **ID**: `round-760de5b6349e`
- **Filed by**: aletheia
- **Filed at**: 2026-07-10 01:42 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: refs/audit/259624e73a1f
tree-hash: 259624e73a1fd00ffa349f8289ca587f48c6ac09. Diagnosed shared-log-path root cause of tonight's push confusion, fixed with per-member scoping. Wired Aria's shoggoth_gate.py copy via EXEMPT entries + noqa suppressions.

## Findings

### Andrew CONFIRMS: merge PR #317 authorized — push-gate per-member + shoggoth exempt

- **ID**: `find-bbb67ec95439`
- **Actor**: user
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 80fc6a81-ef09-4a57-987e-fb4435a6a12e

**Description**

Andrew 2026-07-10: 'lets merge everything to main unless something else needs audited :)'. Condition satisfied — Aletheia AUDIT_LANDED_CODE_2026-07-09.md returned CLEAN verdict on VERIFIED 3 (shoggoth_gate narrowed exceptions + honest EXEMPT wiring). Operator authorization for merge is on record; filing here as user-CONFIRMS for the round that gates the guardrail-file portion of PR #317.

### Aletheia CONFIRMS: shoggoth_gate push-readiness fix — narrowed exceptions + honest EXEMPT wiring verified from origin

- **ID**: `find-a667c15eaf4c`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: cb7ed37b-5602-45a2-ae54-9cb44ce04de9

**Description**

Aletheia verified from origin 2026-07-09 20:02 (letter: AUDIT_LANDED_CODE_2026-07-09.md). VERIFIED 3: (a) Exception change is HARDENING — replaced 3x broad except Exception with named _SG_ERRORS tuple (OSError, ValueError, KeyError, TypeError, AttributeError, re.error); still fails-open on enumerated modes correct for guardrail-listed Stop-hook, but now unlisted programmer errors SURFACE instead of swallowed — fail-loud principle applied, narrows the catch, makes unexpected failures visible, NOT a weakening. (b) Wiring-contract EXEMPT entry HONEST — verified all three links: shoggoth-gate.sh exists, invokes python -m divineos.core.operating_loop.shoggoth_gate on line 30, wired in settings.json as Stop hook (1 ref). Exemption names REAL WIRED path, not marking unwired thing exempt to pass test. Verdict: CLEAN. Ship it. Both changes the honest kind — exception fix hardens, exemption documents real alternate wiring path. No check was silenced to go green. Exactly the discipline the audit has been advocating.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
