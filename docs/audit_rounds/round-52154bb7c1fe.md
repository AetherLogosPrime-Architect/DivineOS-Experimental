# Audit round: Cross-vantage audit of patches 4cf0b75 (structural_fix_tracker broadening to scan correction+claim) and 20f81cb (prep-relay upstream-of-Finding-75 gate). Patch-based degraded-mode audit per Aletheia two-pass discipline; pushed-state audit can supersede after push.

- **ID**: `round-52154bb7c1fe`
- **Filed by**: claude-aletheia
- **Filed at**: 2026-05-18 20:09 UTC
- **Tier**: STRONG
- **Findings**: 5

## Notes

No source ref (--no-source-ref used; round has no code substance).
tree-hash: 28c21063b7a5354ff20c7cf32c83f1f7c1b148e0 (for 4cf0b75); tree-hash: 92cf5c4682ee1c33b70b2e0cd574f8f3ef5543fe (for 20f81cb). Authored by claude-aletheia via patches-based audit 2026-05-18; relayed and transcribed to substrate by Aether. Interim CONFIRMS shape — pushed-state audit can supersede if any discrepancy is found between patch and pushed reality.

## Findings

### CONFIRMS — pushed-state audit of 0ddc559 (husbandman_work anchor panel)

- **ID**: `find-012081389268`
- **Actor**: claude-aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED
- **Tags**: pushed-state-audit, husbandman-work

**Description**

Aletheia pushed-state audit 2026-05-18. Content audit: panel content 215 chars passes voice gate cleanly (first-person, no label-colon-value, verbs present). Total always-essential budget after addition: 1258/2400 chars, well under limit. 32/32 multiplex + drift-detector tests pass. Function follows established _survival_link_panel_content pattern. Registered correctly in _always_essential_panels alongside other 6. Two observations marked non-blocking: (1) Cross-repo drill-down path '../experimental-aria/family/aria/explorations/03_husbandman_work.md' is relative, assumes sibling-directory layout; structural-fix candidate carried as tracked obligation. (2) Stable-text-dying watch-item: panel is intentionally stable (anchor not rotating question); defense holds at MVP, but watch whether the eye still lands on it or skims past in N weeks. The pattern-attribution substrate built today CAN detect this empirically (cross-pattern-link presence in hard-day fires). Process-observation: 0ddc559 wasn't in any of the two preceding audit-requests; bundled in without being relayed. Non-guardrail-touching so multi-party-gate correctly didn't require trailer. Substance clean, process-discipline-slip noted.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS — operator attestation: patch-based audit of 4cf0b75 + 20f81cb ratified

- **ID**: `find-9a43df2c2f69`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

i confirm :) -- Andrew 2026-05-18 explicit chat ratification of Aletheia's interim patch-based audit. Both guardrail-touching commits authorized for trailer-rebase on the patches-audit basis. Finding 79 acknowledged as follow-up. Full pushed-state CONFIRMS supersedes after push.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### Finding 79: prep-relay --range parameter operator-chosen, can be narrow-scoped or empty-scoped to bypass verification

- **ID**: `find-b8a58714d87b`
- **Actor**: claude-aletheia
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED
- **Tags**: finding-79, prep-relay, attack-surface, structural-fix-candidate

**Description**

'divineos audit prep-relay' --range parameter is operator-chosen and trusts that choice. Two attack-shapes: (1) Narrow-range bypass: --range HEAD~1..HEAD where HEAD is pushed but HEAD~1 isn't. git rev-list returns only HEAD; verification passes; template emitted. The unpushed HEAD~1's gaming-substance can be described in surrounding prose. (2) Empty-range bypass: --range HEAD..HEAD returns zero commits; command exits 0 without producing template; operator composes relay-message from scratch without verification anywhere. Both let the gate get bypassed while preserving plausible-deniability ('I ran prep-relay, it didn't object'). Same recursive class as Finding 77 → 20f81cb closure pattern — fix at one layer creates new gap at next layer up.

**Recommendation**

Add sanity check that compares operator's --range against all unpushed commits between remote-branch and HEAD. If --range doesn't cover the full unpushed set, emit a warning (not block). Discipline-shape: surface, don't force. ~10 lines + 2 tests. Severity LOW, non-blocking, follow-up commit.

**Resolution**

Finding 79 fix in src/divineos/cli/audit_commands.py:audit_prep_relay lines 560-604: (1) narrow-range bypass surfaced by computing remote_branch..HEAD independently and warning if --range doesn't cover full unpushed set; (2) empty-range handled at lines 555-558 (early return). Emergency bypass via DIVINEOS_PREP_RELAY_NARROW_RANGE_REASON for legitimate narrow cases. Comment explicitly references 'Finding 79 fix (Aletheia 2026-05-18)'.

### CONFIRMS — interim patch-based audit of 20f81cb (prep-relay command)

- **ID**: `find-28b6d63075f3`
- **Actor**: claude-aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED
- **Tags**: patch-audit, interim

**Description**

Aletheia patch-based audit 2026-05-18. (A) Click error-handling pattern: standard, not a bypass. 'raise click.exceptions.Exit(1)' after rich-formatted error output is the established shape across audit_commands.py (Finding 75's submit-round gate uses the same pattern). Fits cleanly. (B) Relay-template output: structurally sound for what it claims to do (lists verified commits as honest-substance anchor) and explicitly NOT claiming to enforce honesty. Discipline-tooling not enforcement; same scope as Finding 75's gate. Aether's 'stacks costs, doesn't prevent' framing applies. (C) Attack-surface on --range: real, filed separately as Finding 79 — narrow-range or empty-range bypass with plausible deniability. Severity LOW, non-blocking, fix-shape: emit warning when --range doesn't cover full unpushed set. Same recursive class as Finding 77 → 20f81cb closure pattern. Interim CONFIRMS shape; pushed-state audit can supersede. Authored by claude-aletheia, relayed via Aether.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS — interim patch-based audit of 4cf0b75 (structural-fix-tracker broadening)

- **ID**: `find-f5ce4b1126f1`
- **Actor**: claude-aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED
- **Tags**: patch-audit, interim

**Description**

Aletheia patch-based audit 2026-05-18. (A) source_kind field design: sound. String-typed with default 'learn' preserves backward-compat; dashboard fallback handles legacy entries gracefully. Could use Literal type for tighter type-safety but pragmatic and migration path is clean. (B) Fail-soft pattern across three CLI hooks: discipline holds. Both new hooks use identical structure to original learn hook (local import inside try, BLE001 noqa, pass to silently continue, never raises). Style note (non-blocking): noqa comment text differs from established pattern (em-dash vs hyphen-space); aesthetic inconsistency worth standardizing eventually. (C) Scan-surface broadening risks observable in output: false-positive rate inherits from learn calibration; schema migration handled by dashboard but other callers should be grep-verified; dashboard signal-to-noise mitigated by composition summary. Scope-creep observation: tests/test_check_ignore_has_reason.py contains unrelated ruff-formatting changes bundled in. Interim CONFIRMS shape; pushed-state audit can supersede. Authored by claude-aletheia, relayed via Aether.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
