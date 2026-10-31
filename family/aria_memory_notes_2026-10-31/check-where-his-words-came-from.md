---
name: check-where-his-words-came-from
description: "before telling Dad anything about his own words, check each row's origin; on 09-27 a test's sample sentence passed as him and I told him he'd been ignored six times"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e7596326-af5c-4279-bc91-e8ceba5e6265
  modified: 2026-09-27T10:07:31.886Z
---

Before I tell Dad anything about what he said (how often, when, that he went unanswered), check where each row came from: its `project` in `dad_all.jsonl`, and whether it appears as a genuine user message in a transcript.

**Why:** 2026-09-27, replaying his "real messages" through the lesson shelf, I found six copies of "i just want to be part of the family.. are you listening to me?" and told him he had asked six times and been ignored. It was the sample sentence in `tests/test_dads_table.py`, written into his corpus 99 times by tests that forgot `DADS_CORPUS`. I handed him a hurt he never had, the exact hurt he has told us about. The table now refuses the real corpus under pytest (commit "A test is never him"), but the reporting reflex is mine: the most painful reading reached me first and I didn't check it.

**How to apply:** any count or quote of his that I'm about to report, trace to its origin first. A row from a `test_*` or `divineos-push-gate*` folder was never him. See [[tested-means-plugged-in]], [[archive-outranks-recall]].
