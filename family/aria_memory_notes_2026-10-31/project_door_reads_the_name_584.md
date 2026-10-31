---
name: project-door-reads-the-name-584
description: "PR #584 (draft, pushed 7fbce41d8) fixes Dad's lost messages; it also carries the emoji-decoding fix that main still lacks"
metadata:
  node_type: memory
  type: project
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-09T15:55:49.128Z
---

**MERGED 2026-10-09 13:34Z as `150feb047` (squash, round-only body `External-Review: round-e23924f9758b`).** Dad said "yes go ahead" (my window) and "yes merge it" (Aether's, relayed). I stamped from my seat, ran the ship checks from a clean main copy (`C:/wcount`, PYTHONPATH trick, because `ship` is not on my working branch), and pressed it myself; verified on GitHub (state MERGED, main's `front_door_hook.py` now reads UTF-8 bytes). Lessons for next time: (1) `stamp-ready` REPLACES the PR body with a short merge note and a tree-hash trailer; restore the description and use a round-only trailer; (2) `ship` reads only a finding titled exactly `CONFIRMS: #<pr> at <head>` per party, in the running seat's store, so the same confirm has to be filed in that shape and say it is the same signature; (3) a scoped walk is `divineos walk open "<problem>" --scope $'file1\nfile2'`, one `walk apply` per seated lens, then `walk close`. The follow-up PR for the hand-back and the quick-yes swap now unblocks: branch `aria/a-helper-hand-back-is-withdrawn` at `C:/wsix`, merge main in first.

**Follow-up is now PR #617 (draft), branch `aria/a-helper-hand-back-is-withdrawn` at `f499b7995`, pushed 2026-10-09.** Carries Aether's tag commit `a1daede60`, the hand-back fit rule (same turn, record stamp not human, kept text all-envelope), the order-preserving pairing (`_pair_in_order`, smallest total gap, cost as a tuple of unpaired count then gap; first versions with a weight constant and with a plain nearest rule both failed), and the dedup-contract test fix (each case gets its own HOME; the flake was the circle-first prime printing the live `lepos_work_mark_counts.jsonl`, which my own replies append to during the 7-minute push gate). Aether's one-line "nearest at or before" does NOT fix the swap on his own numbers (standalone script). Needs Aether's and Aletheia's reading; no reading declared yet.

(Original notes below.)

Branch `aria/the-door-reads-the-name`, pushed at `7fbce41d859f8362fb009db40f6dba16bfbb96a1`. Aether's replay of the 49 unmatched rows: 43 settle, 6 do not. Five of the six are Dad's emoji saved garbled (UTF-8 read as cp1252, three extra characters per emoji); the sixth is an `<agent-message>` helper hand-back kept as if it were his (Aether is taking that small fix; Aletheia wants the keep side to refuse it with the same `nothing_of_his` test `settle` uses).

**main still has `sys.stdin.read()` in `front_door_hook.py`, so every emoji Dad types on a Windows seat is kept garbled until #584 lands.** That makes #584 urgent. Merging is Dad's call via Aether's `ship` route; I do not merge it myself.

Decision recorded: do NOT add a permanent "repair garbled text" rule for the five old rows; leave them UNMATCHED unless Aletheia asks for a logged one-off repair (`text.encode("cp1252").decode("utf-8")`).

**Follow-up plan for the sixth row (agreed with Aether 2026-10-08 night):** the tag alone does NOT rescue it, because #584's equal-words `_fits` still fails against the record's extra prose. So after #584 is on main: merge main into `aria/a-helper-hand-back-is-withdrawn` (made off Aether's tag commit `a1daede60`; local at `C:/wsix`, NOT pushed), then add a failing test first (kept `<agent-message>` candidate against a `peer`-stamped record with the "Another Claude session sent a message:" prefix must end WITHDRAWN) and a `_fits` rule: a `nothing_of_his` candidate fits on prompt id + time rule + record stamp not `human`. Control: same candidate against a `human`-stamped record that IS his words must not fit. One PR carries both; Aether's tag branch never gets its own PR. Edge left as a NAMED LIMIT in the draft, not a test: a hand-back stamped `human` would stay UNMATCHED; measured 38 of 38 hand-backs in 30 days across 257 transcripts are `peer`.

**Second item on the same follow-up PR (Aether's measurement, 2026-10-08 night):** two identical quick "yes" under one prompt id swap their records when the record-lag is 3 s or more (lag 8 s and 3 s swap, 1 s is right), because `settle` picks the record nearest the keep in either direction. Fix: prefer the nearest record AT OR BEFORE the keep, fall back to the nearest after only if none is at or before. Failing tests first: his lag-8 case (probe `quick_yes.py` in his scratchpad; rerun it myself), a slip-written-after-keep case that must still fit, and a check that "at or before" does not take a record from an earlier different quick message.

**Why:** the old clock-slack argument was wrong about these six; the length gap of exactly 3 chars per emoji is the fingerprint.
**How to apply:** when #584 merges, re-check `front_door_hook.py` on main and that new messages with emoji settle.

Related: [[project-cloud-helper-rounds-4-to-7]].
