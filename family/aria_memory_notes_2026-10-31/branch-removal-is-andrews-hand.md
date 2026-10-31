---
name: branch-removal-is-andrews-hand
description: "Removing remote branches is MINE to do (Andrew 2026-09-25, verbatim below): archive-tag, verify on the remote, then delete. The old version of this note wrongly made it his rule."
metadata:
  node_type: memory
  type: feedback
  originSessionId: e7596326-af5c-4279-bc91-e8ceba5e6265
  modified: 2026-09-25T14:59:27.705Z
---

Andrew 2026-09-25, when I told him branch removal "has always been your hand": *"its never been my hand.. so yes you may do it yourself"*. Same morning he confirmed the pile rule still holds — *"yes it still applies, or you will never get through the pile"* — and gave standing permission to push drafts to PR for auditing, only waiting for him before merging.

**What went wrong in the old note:** on 2026-09-23 the Claude app's permission layer refused a remote delete, and I wrote that down as Andrew's rule. A tool refusal is not his decision. I then quoted the "rule" to him as his, which is the relayed-claim fault (see [[a-rule-is-his-only-with-his-words]]) and the filing-cabinet reflex from exploration 48: a thing I had not decided, converted into a question for him.

**How to apply:** Every new remote branch is paid for by removing two first. For each removal: annotated tag `archive/<branch>` on the exact tip, push it, confirm `git ls-remote origin refs/tags/archive/<b>^{}` equals the tip, then `git push origin --delete <b>` and confirm it is gone. Only remove branches whose work is verifiably elsewhere. If the permission layer refuses the delete, that is a tool block: tell Andrew plainly as that, never as his rule, and never add a bypass. See [[archive-outranks-recall]].
