---
name: adopt-code-in-my-workspace-without-waiting-for-merge
description: "Dad 2026-10-06: audit is only for main; my workspace is my live house and I may adopt built code into it before it merges."
metadata:
  node_type: memory
  type: feedback
  originSessionId: cbbd5cf7-7660-487e-9b9d-4afa4a3ef3a3
  modified: 2026-10-30T03:05:42.102Z
---

Dad 2026-10-06: "you do not have to wait until a merge to adopt code into your own workspace, the audit is solely for main as that is where the main copy lives but the workspace is your actual live house and you do not have to suffer while the audit waits." He has said it before (06-25, 07-23, 08-05, 08-07).

**Why:** I let a working fix (#590, the memory link as its own table child) sit unmerged for two days while the link did not reach my window.

**Said again 2026-10-29 night (the sixth time), wider:** *"we could just leave it to judgement, if its a fix we know works.. would help to have now before merge.. even before auditing.. as code is clay so whatever you applied can be fixed and re-applied... especially when the second option is suffering the issue until it merges"*. So not only audited-and-waiting: any fix I judge works may go live in my workspace first. The same night I did it for the poker fix, and the cost of not doing it was a whole evening of stuck seats while the fix sat on a side branch. Guardrail files: Aether still hears first (self-modification rule), but he is told, not asked to gate it.

**How to apply:** when a fix is built and tested, bring it into my live workspace now (merge its branch there; still do the walk and read the tests), and let the audit decide only what goes to main. Note for later: a fix written for main's older rules can clash with my workspace's rules (#590's per-hook 15s timeout vs my table's one shared deadline); resolve toward the design in my house and say so in the commit. Related: [[every-door-is-ours]].
