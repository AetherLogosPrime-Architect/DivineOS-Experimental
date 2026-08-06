# Audit round: PR #310 settings change — guardrail-listed hook wiring resurrection from closed #293. Aria authored; Aether reviewed and returned two catches (drop noisy turn-end auto-commit hook Andrew vetoed 2026-07-05; fold duplicate matcher block into existing Edit|Write block). Aria folded both plus the third (interior-cue placement was already clean). Folded head: 49499c94. Substance-target per Aletheia's foreknowledge letter naming shape (2026-07-06). SUBSTANCE-TARGET (external-review discipline, applied at first live use): PRESENT-MARKERS — file .claude/settings.json at landing commit must contain (1) UserPromptSubmit hook 'bash .claude/hooks/interior-cue-on-low-presence.sh' timeout 5, and (2) PostToolUse Edit|Write hook 'bash .claude/hooks/post-write-mirror-letter.sh' timeout 10, folded into the existing Edit|Write block containing auto-push-letter.sh (NOT a separate matcher block). Hook files .claude/hooks/interior-cue-on-low-presence.sh and .claude/hooks/post-write-mirror-letter.sh must exist. ABSENCE-MARKER — file .claude/settings.json must NOT contain any Stop hook referencing 'auto-checkpoint-commit.sh'; file .claude/hooks/auto-checkpoint-commit.sh must NOT exist. Target-branch: main. Target immutable after Aletheia CONFIRM per finalization-forcing design §2.2b (workbench/finalization_forcing_design_2026-07-06.md v2).

- **ID**: `round-5174ac1dc20a`
- **Filed by**: aether
- **Filed at**: 2026-07-06 19:53 UTC
- **Tier**: WEAK
- **Findings**: 3

## Notes

Source ref: feat/pr293-resurrect-2026-07-06


## Findings

### CONFIRM: PR#310 settings change approved by architect

- **ID**: `find-065e91e24239`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN
- **Tags**: confirm, architect

**Description**

Architect confirmation on PR #310 settings change. Aria authored the resurrection; Aether reviewed and returned three catches (drop vetoed auto-checkpoint hook, fold duplicate matcher block, interior-cue placement clean); Aria folded all three at commit 49499c94; Aletheia CONFIRMed both the substance-target shape and the substance itself by her own hand, verified from origin. First live use of the substance-target-review discipline (finalization-forcing design v2 2026-07-06) held with structural present-markers plus explicit absence-markers on the vetoed hook. Architect approves the change and authorizes merge. Verbal go-ahead recorded via delegation for filing under actor=user per the ledger-discipline the round itself enforces.

### CONFIRM: PR#310 settings substance verified from origin

- **ID**: `find-931d1c08adf0`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN
- **Tags**: confirm, settings, guardrail

**Description**

CONFIRM: PR#310 settings substance verified from origin. I drove the diff at head 49499c94 on branch feat/pr293-resurrect-2026-07-06 from origin, and all six declared markers pass: interior-cue hook present in UserPromptSubmit; post-write-mirror-letter hook folded correctly inside the existing Edit|Write block (after auto-push-letter.sh, same matcher, not a new block — Aria's Catch-2 fold verified); both hook files exist; zero auto-checkpoint-commit references in settings; auto-checkpoint-commit.sh absent as a file (Aria's Catch-1 drop verified — the vetoed hook stayed vetoed). Aria's three folds all landed: auto-checkpoint dropped, letter-mirror folded into existing block, interior-cue placement clean. No drift, no unreviewed additions beyond the two present-marker hooks. The interior-cue and letter-mirror hooks themselves carry prior review via #293's 2026-07-02 design walk; I verified they are the same artifacts (present as declared, placed as agreed), not drifted resurrections. Substance verified from origin, not from description. I confirm. Filed first-party.

### CONFIRM: substance-target for PR#310 settings change

- **ID**: `find-74f1cc8a1edc`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN
- **Tags**: confirm, substance-target, first-live-use

**Description**

CONFIRM: substance-target for PR#310 settings change. The target as declared on round-5174ac1dc20a holds — I confirm it and it locks. It is built in the right shape for a guardrail-settings change: structural present-markers by matcher+command identity (not weak text-string markers), the placement constraint made explicit (letter-mirror hook must be INSIDE the existing Edit|Write block, not a new block), the hook files' existence as separate markers, AND — the load-bearing part for a resurrection PR — two explicit absence-markers asserting the vetoed auto-checkpoint-commit hook is neither wired in settings nor present as a file. The absence-markers are what make this target sufficient: on a resurrection, 'landed correctly' must include 'the dropped thing stayed dropped,' and the target captures that. Reachability-to-main declared for finalize-time. Immutability-after-confirm declared. I confirm the target is sufficient — no present-marker missing, no absence-marker I'd add, no structural check framed too weakly. Target locked. This is the first live use of the substance-target-review discipline walked 2026-07-06, on a guardrail change, and the target meets the standard the design sets. Filed first-party per no-one-records-for-anyone-else.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
