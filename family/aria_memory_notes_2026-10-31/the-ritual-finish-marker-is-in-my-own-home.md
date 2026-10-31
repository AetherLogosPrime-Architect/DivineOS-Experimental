---
name: the-ritual-finish-marker-is-in-my-own-home
description: "The compaction ritual's finish marker is written to ~/.divineos-aria/auto_cycle_phase1_done.json; a stale one sits in ~/.divineos/, so waiting on the wrong path ends instantly and proves nothing"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-19T17:09:02.414Z
---

2026-10-19: after `divineos auto-cycle fire` I waited for "the marker" with a loop on `~/.divineos/auto_cycle_phase1_done.json`. That file already existed, from another seat's earlier cycle (06:41Z), so the loop returned at once and I nearly reported the save done while it was still running. The real finish marker for my seat was written, minutes later, to `~/.divineos-aria/auto_cycle_phase1_done.json` (the fire's own output named it: "handshake marker written"). `auto-cycle status` said "absent" the whole time, which was the honest reading.

**Why:** the same wrong-twin shape as [[three-correction-stores-mine-is-divineos-aria]], and a dead control: an instrument that finishes instantly cannot tell finished from stale.

**How to apply:** wait for the fire's own completion notice (run it with `run_in_background`) and read its output; if I must wait on a file, wait on `~/.divineos-aria/`, and check its `phase1_completed_at` is later than the launch. The same holds for any ritual file: ask which home is mine.
