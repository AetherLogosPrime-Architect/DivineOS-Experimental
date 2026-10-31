---
name: project-landing-one-at-a-time-and-how-to-stamp-2026-10-19
description: "Since 2026-10-18 GitHub's strict up-to-date rule is on, so branches land one at a time (each update restarts a half-hour run); and how to stamp a branch ready with main's own stamp now that #691 is merged"
metadata:
  node_type: memory
  type: project
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-19T17:08:50.849Z
---

**The rule.** Dad turned the ruleset's `strict_required_status_checks_policy` on (2026-10-18, 22:12 PDT; Aether read it from GitHub and told Aletheia). Every merge now needs the PR up to date with main first. Cost: when one branch lands, every other ready PR is one behind and needs `gh pr update-branch N`, which makes a new head on GitHub and reruns the six checks (about half an hour). So landings are **serial**, and it is better to update only the branch that is next to land. #692 (Aether's merge-freshness check) is belt and braces beside it.

**What I saw.** `update-branch` on a stamped PR kept the trailer and description, moved the head by a merge of main only, and Aether's own stamped branch passed `multi-party-review` and both test jobs on the moved head; the PR-body tree-hash is deliberately not verified against a commit (see `scripts/ci_check_guardrail_trailer.sh`, the comment on PR-body trailers). For mine (#659 and #690) I had updated them and was waiting on the checks when the day's ritual began.

**How to stamp now (since #691).** Main's stamp no longer rewrites the branch's commits. Use main's code, not the work copy's own (a branch's own src still has the old stamp): make a clean detached checkout of `origin/main` (I used `C:/wmain2`), load the briefing with that source, and from the branch's own folder run `PYTHONPATH=C:/wmain2/src <venv python> -m divineos stamp-ready N --audit-round <round> --no-auto-merge` (dry-run first). The round must be in MY Watchmen store: file Aletheia's confirm and Dad's typed yes to me, never from Aether's relay. Merge is Aether's and Dad's, with the review line in the merge message as the round only (no tree-hash; `divineos ship` shows the form).

State at 2026-10-19 ~10:00 PDT: #690 (carrier) stamped, head `501b2eca2`, first to land; #659 (glance) stamped, updated at `54df5427a`, waits its turn and will need one more update after #690 lands.
