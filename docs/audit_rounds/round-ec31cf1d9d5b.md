# Audit round: Four-PR sweep, Aletheia CONFIRMS relayed 2026-08-22. Anchors recomputed by her against origin independently of the letter. EXACT AND UNCHANGED ON ORIGIN AS OF FILING: PR #432 claude/corrupted-window-recovery-220ad2 tip 51eb570bd46fcf12ba79c2d10aa396b7633432d2 tree-hash: a49836019415c12b3bf6335ff9d0696b70160587 patch-id 35a9dd5da5f6e1b118b71ab1ba268ec0013c0c53 | PR #436 chore/retire-delivery-cluster tip b71180a61b8e061135804d6788cdebe1f9a5107f tree-hash: f450ab106c21d6bdd52ed7851a4f45f9138d1f55 patch-id c777ed7b7eb69d872969a662b76ff35aaf1d1d44 | PR #438 aria/resolve-406-merge tip 30937da0d1c338adca1e98c0ad8094390e3d3440 tree-hash: 920e12054237fab33395315a363094d98e41f74b patch-id 27ad4e5efdf683774642c5c37bb00c4c1d9a67c1. PR #437 fix/hook-latency-and-stamp-branch-measurement CONFIRMED BY HER AT tree-hash: a5609f37c6c2ca00dc27714d94c8b7b80d5eda86 (tip 933b169dd370c118acf3a576df02da3084cfeaa8) AND HAS SINCE MOVED to tip e70f0f12 tree-hash: 5093aa4c9. Delta: b788e974 (the two obligations fixes she explicitly ruled Ship both fixes on), 5a9768d9 (letter auto-commit), e70f0f12 (corpus-poisoning fix - NEW WORK SHE HAS NOT REVIEWED: semantic_classifier was feeding defect-escape triggers to the classifier as negatives, several of them verbatim Andrew corrections). Her confirm does NOT reach e70f0f12 and this round does not claim it does. PR #406 excluded at Aria's direction - content duplicated on #438, not landed. Her ruling on the obligations gate: WITHDRAWS her earlier recommendation to exempt audit submit-round, because with Aether's false-positive claim retracted the jam is explained by two mechanical defects and an exemption would have removed a rule that was mostly working.

- **ID**: `round-ec31cf1d9d5b`
- **Filed by**: aether
- **Filed at**: 2026-08-22 19:19 UTC
- **Tier**: WEAK
- **Findings**: 4

## Notes

Source ref: fix/hook-latency-and-stamp-branch-measurement


## Findings

### CONFIRMS four-PR sweep (Andrew, actor=user)

- **ID**: `find-9986f445345d`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 4e027b47-76a3-4297-af05-bbcea406b2f1

**Description**

Andrew's authorization, verbatim in chat 2026-08-22 after reading Aletheia's relayed CONFIRMS: 'i confirm as well :)'. RELAY, NOT AUTHORSHIP: Aether typed this row; Andrew spoke it. Recorded because the distinction is the whole point of the actor field - correction 1329c1e3 records Aether self-caught attempting to file external-auditor CONFIRMS on his own bundle to make prepare-merge go green when no audit had happened. That was forging a vantage. This is transcribing one that was given, in the operator's own words, in the same conversation. SCOPE: covers PR #432 (tree a49836019415c12b3bf6335ff9d0696b70160587), PR #436 (tree f450ab106c21d6bdd52ed7851a4f45f9138d1f55), PR #438 (tree 920e12054237fab33395315a363094d98e41f74b) - the three Aletheia confirmed at the tree-exact rung and which remain byte-identical on origin at filing time. PR #437 is NOT covered: the external-confirm tool refused it because the branch moved past her anchor to tree 5093aa4c, and the delta includes e70f0f12 (the semantic-classifier corpus-poisoning fix) which she has never reviewed.

### CONFIRMS PR #438 (external-AI review, aletheia) — tree-exact

- **ID**: `find-ac121ea334af`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: b76b7b20-0141-487c-94e0-2c2eeb0cc00d
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 30937da0d1c338adca1e98c0ad8094390e3d3440 / Tree 920e12054237fab33395315a363094d98e41f74b / patch-id 27ad4e5efdf683774642c5c37bb00c4c1d9a67c1 (git-version 2.43.0) — verified against origin/aria/resolve-406-merge at file-time over merge-base(origin/main)..branch (default context). Basis: Recomputed independently against origin. All three match. Named the finding as a doorman that exempted its own remedy so the remedy could run, where running it was never wired to opening the door - a door with a key that turns and does not unlock.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

### CONFIRMS PR #436 (external-AI review, aletheia) — tree-exact

- **ID**: `find-41cebdceefa2`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: a1c5327a-26c8-4aea-9914-093cef267800
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip b71180a61b8e061135804d6788cdebe1f9a5107f / Tree f450ab106c21d6bdd52ed7851a4f45f9138d1f55 / patch-id c777ed7b7eb69d872969a662b76ff35aaf1d1d44 (git-version 2.43.0) — verified against origin/chore/retire-delivery-cluster at file-time over merge-base(origin/main)..branch (default context). Basis: Recomputed independently against origin. All three match. Confirmed the removal order was right: letter_monitor_health.py covers all four states with distinct exit codes before require-monitors-armed.sh is removed, and the conflict surface was five files rather than 266.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

### CONFIRMS PR #432 (external-AI review, aletheia) — tree-exact

- **ID**: `find-b1d3e6776859`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 51eb570bd46fcf12ba79c2d10aa396b7633432d2 / Tree a49836019415c12b3bf6335ff9d0696b70160587 / patch-id 35a9dd5da5f6e1b118b71ab1ba268ec0013c0c53 (git-version 2.43.0) — verified against origin/claude/corrupted-window-recovery-220ad2 at file-time over merge-base(origin/main)..branch (default context). Basis: Recomputed the anchor against origin independently before reading the letter's account of it. Tip, tree and patch-id all match exactly.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
