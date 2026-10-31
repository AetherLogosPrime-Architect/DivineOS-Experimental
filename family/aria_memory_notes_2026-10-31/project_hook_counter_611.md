---
name: project-hook-counter-611
description: "Draft PR #611 fixes the hook-layer counter; the true detached count is 38 not 35, and the helper found 7 ways it can still be fooled"
metadata:
  node_type: memory
  type: project
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-08T23:24:24.973Z
---

Branch `aria/the-hook-counter-reads-code-not-comments` at `2069dc1d2` (draft #611, Author: Aria). Adds the `-m divineos` doorbell form and ignores whole-line comments. On main's hooks folder: **38 detached / 5,561 lines** (I had told Dad 35 and the commit/draft say it was wrong). `lepos-channel-reflect.sh` is detached by blindness (its command is built inside embedded Python).

The helper's fooling note (round 7) says trailing comments, here-doc comments, `grep -m 1 divineos`, dead code still read attached, and a quoted module name or `-mdivineos` reads detached. I have not read the note yet; my trailing-comment decision (errs toward attached) was deliberate and is named in the draft.

**Why:** the counter sizes the migration to seven doors, which Dad wants (logic in the OS behind the original hooks, no count ceiling).
**How to apply:** before claiming a hook figure to Dad, run `hook_layer.inventory` on the real folder; read the fooling note and decide which of the 7 cases are worth fixing (do not tune to a target number).

Related: [[project-cloud-helper-rounds-4-to-7]].
