# Audit round: restore divineos rest CLI on talk-to-wrapper-collapse branch + wire post-extract banner + add private-room as 10th task (closes Cluster 3 discipline-gap from substrate audit)

- **ID**: `round-b1abe42aef46`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 15:32 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS the restore + wire

- **ID**: `find-3934c78e1cb5`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Closing implementation-drift on the rest-program → extract tie is exactly the WIP shape — what was original intent becomes structurally true via the channel-carve.

### Rest CLI restored from main-repo/main (commit 15a415a never reached talk-to-wrapper-collapse). Tests: 24/24 pass. Wired into extract via format_rest_available_banner — banner surfaces after extract on hard-day signal. Added private-room as 10th REST_TASKS entry (different from casual 'mansion' visit — this one binds the pause via the substrate-enforced quiet marker).

- **ID**: `find-457e8d62c229`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Closes the discipline-gap Cluster 3 from this morning's substrate audit (calibration / metacognition never engaged — private rooms specifically). Andrew named the original design 2026-05-14: work → tired → sleep+extract → rest. This commit closes the implementation-drift on the post-extract tie.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
