# Audit round: PR #10: noqa BLE001 fix for 7 observability-boundary broad-excepts (same pattern as PR #12)

- **ID**: `round-16fb5c382d57`
- **Filed by**: user
- **Filed at**: 2026-05-18 01:25 UTC
- **Tier**: WEAK
- **Findings**: 3

## Notes

PR #10 noqa BLE001 fix — observability boundaries.

Scope: a single commit (b6229b3) that adds # noqa: BLE001 to 7
broad-except sites in PR #10 modules. Pattern is established by
PR #12 work earlier today (round-25213ab69777 CONFIRMS by both
Andrew + Aletheia) for the same kind of sites in hedge_audit,
mid_turn_surfacer, pre_response_context, theater_audit.

The 7 sites are all observability/audit boundary layers that
catch broad Exception by design to prevent observation code
from crashing user-facing flows. Per scripts/check_broad_exceptions.py:
If suppression is truly justified, append # noqa: BLE001.

Authorized commit tree-hash:
  tree-hash: 3390f1a0cf1030133e092e4bff2e5f3b576e3fbd  b6229b3 — fix(observability): add # noqa to 7 sites

Same shape as round-25213ab69777 noqa work; CONFIRMS at info-severity
is appropriate (mechanical pattern application, no novel risk).


## Findings

### Finding 74: --ignore flags should require structurally-enforced # REASON: comment

- **ID**: `find-0de1120c778e`
- **Actor**: aletheia
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

The bypass-discipline-failure pattern recurred twice in one day: (1) DIVINEOS_SKIP_MULTIPARTY_CHECK + DIVINEOS_SKIP_TESTS used together when the actual chicken-and-egg only required bypassing multiparty; (2) pytest --ignore=test_check_broad_exceptions used during local sweep to mask PR #12 pre-existing failures, which then hid PR #10's new violations. Both shapes: bypass-too-broad catches less than intended. Fix-shape: --ignore flags should require an inline # REASON: comment naming what is being masked and why, structurally enforced (e.g. a precommit hook that rejects --ignore without an adjacent comment). Substrate-level prevention beyond honest-naming-after-the-fact. Non-blocking; tracked for post-merge structural-fix queue.

**Resolution**

scripts/check_ignore_has_reason.py exists and is wired into scripts/precommit.sh:219-221. The script enforces that any --ignore=foo in pytest invocations has an adjacent # REASON: comment. Structural enforcement landed; the fix-shape Aletheia named is in place.

### CONFIRMS — user (Andrew): noqa BLE001 fix ratification authorized

- **ID**: `find-bd357b6c2de0`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew CONFIRMS in chat ('i confirm as well'). Pairs with Aletheia's CONFIRMS finding on the same round. Authorizes the trailer-amend on commit b6229b3 and the subsequent push.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS — Aletheia: 7 noqa BLE001 additions verified pure-mechanical per-site

- **ID**: `find-d4298a7b5847`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Verified full diff: 7 files, 7 insertions, 7 deletions, all of the form 'except Exception:' -> 'except Exception:  # noqa: BLE001 - observability boundary'. No new exception handlers, no modifications, no smuggled changes. Per-site verification confirms each is a genuine observability/fallback boundary: sleep_commands fail-open, claim_triage/ship_claim narrow-ValueError-first then broad-fall-through for import failures, hud graceful-degradation, pre_response_context proceed-without-section, read_before_write documented per-process-token fallback, sleep_readiness no-blocker-on-marker-failure. Tree-hash matches: 3390f1a0cf1030133e092e4bff2e5f3b576e3fbd. Strict-mode gate empirically blocks b6229b3 without trailer (exit 1) confirming gate-fix works. Same pattern as round-25213ab69777 noqa work; mechanical.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
