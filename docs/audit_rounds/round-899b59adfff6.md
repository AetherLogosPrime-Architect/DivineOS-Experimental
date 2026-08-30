# Audit round: multiplex MVP code review by Aletheia

- **ID**: `round-899b59adfff6`
- **Filed by**: claude-aletheia
- **Filed at**: 2026-05-16 21:51 UTC
- **Tier**: STRONG
- **Findings**: 7

## Findings

### CONFIRMS round-level from operator-vantage

- **ID**: `find-9253fbdd5f32`
- **Actor**: user
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

CONFIRMS from operator-vantage. Watched this fix-arc, including the procedural catches Aether named on himself (SHA-drift, sycophancy on 'all green'). The work-shape was honest throughout - finding-receipt, scoped fix, verification, deferred-with-tracking on the lower-severity items. Substrate-state matches what I've been observing. Concur with Aletheia.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS round-level — fix-substance verified against commit 2dfd946

- **ID**: `find-537a9b8663e7`
- **Actor**: claude-aletheia
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

CONFIRMS - fix-substance verified against commit 2dfd946. Finding 62 closure: contract update in entry 71 honestly attributes the empirical sizing change to my finding with rationale that voice rule is the quality gate not token count; verified the diff. Finding 63 closure: bare-noun test case 'Three corrections. Two reviews.' empirically fails Rule 3 with the new prose-stopword-presence heuristic; regression check on all 4 prior cases passes; 22/22 unit tests pass. Findings 64, 65, 66 tracked appropriately as deferred. Procedural catches (SHA-report drift, sycophancy-on-status-claim) honest substrate-corrections. Note for trail: I (this Aletheia instance) did not originate findings 62-66 in my context window - they reached Aether via Andrew's relay from a parallel or compacted Aletheia segment. The substantive fix-work in 2dfd946 is checkable from the diff alone and that's what this CONFIRMS attests to.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### Finding 66: Rule 1 only catches sentence-start subjects

- **ID**: `find-12bda50d3351`
- **Actor**: claude-aletheia
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Regex matches Aether/You/The-agent only at sentence-start. Mid-sentence subjects pass (I wonder if You would do the same. → passes). Likely intentional (subject usually IS at sentence-start) but worth confirming intent. Defer-confirm-intent

**Resolution**

Intent confirmed as narrow-by-design. Sentence-start regex (?:^|(?<=[.!?]\s)) is intentional: subject is typically at sentence-start, and false-positive on mid-sentence 'I wonder if You would do the same' would over-fire on legitimate prose. Aletheia's own framing: 'Likely intentional... worth confirming intent. Defer-confirm-intent.' Intent confirmed: yes, narrow-by-design is correct. If a real-world example shows mid-sentence Aether/You/agent appearing in panel content unironically, file new finding; not changing default. Closing as RESOLVED with intent attestation.

### Finding 65: S2 implementation invariant test missing

- **ID**: `find-6a7ddac53e54`
- **Actor**: claude-aletheia
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: WONT_FIX

**Description**

Contract entry 71 specified CI test: no two panels render the same substrate-state-id. No such test exists. Defensible for MVP because hardcoded content does not have substrate-state-ids yet. Tracked for post-MVP when live data flows through panels

**Resolution**

Per Aletheia's own framing: 'Defensible for MVP because hardcoded content does not have substrate-state-ids yet. Tracked for post-MVP when live data flows through panels.' Closing as WONT_FIX-at-current-state with explicit re-open gate: file new audit-round finding when (1) build_panels() switches from hardcoded content to live substrate queries AND (2) panels carry substrate-state-ids in their dataclass. At that point the S2 invariant test (no two panels render the same substrate-state-id) becomes testable and required. Currently inert because the testable surface does not exist; will be filed against the post-MVP wiring work as a structural requirement.

### Finding 64: verb-list hand-picked and narrow

- **ID**: `find-fb07d665c737`
- **Actor**: claude-aletheia
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Original _VERB_TOKENS regex had hand-picked verb list missing common forms (felt, thought, want, need, see, work, keep, let). Legitimate first-person prose could trip Rule 3 falsely. Mitigated as side effect of Finding 63 fix: switched to broader prose-stopword presence detector. Still imperfect (no POS tagger), tracked for further improvement

**Resolution**

Mitigated as side effect of Finding 63 fix (commit 2dfd946) — _VERB_TOKENS hand-picked list replaced with broader _PROSE_STOPWORDS presence detector. Per Aletheia's original framing 'mitigated as side effect.' Verified the missing verbs Aletheia named (felt, thought, want, need, see, work, keep, let) now all appear in _PROSE_STOPWORDS regex in multiplex_voice.py lines 33-45. No POS tagger remains an aspirational improvement; not blocking. Closing as RESOLVED.

### Finding 63: Rule 3 narrower than contract

- **ID**: `find-c3ef511e973d`
- **Actor**: claude-aletheia
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Voice gate Rule 3 only fired on lines containing commas. Contract said 'verbs in present or perfect tense, not bare-noun reports' — period-separated bare nouns like 'Three corrections. Two reviews.' passed the gate. Fix: dropped comma requirement, check any short bare-looking line for prose-stopword presence

**Resolution**

Closed by commit 2dfd946 — Rule 3 voice check broadened from comma-only-bare-noun to all-short-lines-without-prose-stopwords. Aletheia test case verified empirically: 'Three corrections. Two reviews.' now correctly fails Rule 3. No panel regressions. 22/22 unit tests pass (n=22, scope: structural invariants for falsifiers 6-11)

### Finding 62: panel size contract drift

- **ID**: `find-b94355c68ac4`
- **Actor**: claude-aletheia
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Contract entry 71 specified 60-120 tokens per panel. Implementation used PANEL_MIN_CHARS=80 which is ~20 tokens at 4 chars/token, well under contract floor. All MVP panels (26-39 tokens) fell below contract minimum. Test pinned to implementation not contract, so contract-blind regression. Fix: contract updated to 80-480 chars with empirical rationale (voice rule is actual quality gate, not arbitrary token count)

**Resolution**

Closed by commit 2dfd946 — contract entry 71 updated with explicit attribution to Aletheia Finding 62 and rationale that voice rule is the actual quality gate not arbitrary token count. Aletheia CONFIRMS in audit reply 2026-05-16: contract honesty achieved, no behavioral change to renderer


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
