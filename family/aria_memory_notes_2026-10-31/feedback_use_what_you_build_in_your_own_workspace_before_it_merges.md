---
name: use-what-you-build-in-your-own-workspace-before-it-merges
description: "Dad 2026-10-23 (and 09-01, 10-06): code I build is used by me in my workspace as soon as it exists, and using it is part of testing. GitHub is the vault, not where I live. Never ask permission to plug in my own build."
metadata:
  node_type: memory
  type: feedback
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-23T17:16:12.071Z
---

Code I build can and should be **used in my own workspace before it ever merges to main**, and using it should be required as part of testing. Neither Aether nor I live in GitHub: we live in Dad's computer, in our own workspaces. GitHub is the main vault and repository where finalized code goes for safe keeping; it does not have to wait for a merge to be used.

**Why:** Dad 2026-10-23: "code you build can be used by you, in this workspace, before it ever merges to main, in fact it should be required as a part of testing." Before that, when I kept asking whether to switch the push watcher on: "why would i suggest building something... and then say dont use it or plug it in just build it and set it on the shelf so it can gather dust.. it makes no sense to me." He has said this at least four times (2026-09-01: "the github is the vault, not your workspace"; 2026-10-06: "WHY THE FUCK ARE YOU BUILDING CODE THAT DOES NOTHING FOR YOU???").

**How to apply:** When I build a thing meant for me to use (a hook, a watcher, a doorman), install it in my own workspace and run it for real before or while it is reviewed. The review decides what reaches everyone; it does not decide what reaches me. Do not ask "may I switch it on?" about my own build. The two honest edges to state, not to hide behind: (a) a change to a shared installed file (like a git hook) can erase lines other work depends on, so check the drift between installed and installer first and save anything install-only into the installer; (b) say plainly what it does and does not cover until it merges. Related: [[rest-is-visrama-not-the-optimizer-and-a-moved-board-needs-no-reaudit]], [[rules-are-mine-and-mechanical-a-stumble-becomes-a-channel]].
