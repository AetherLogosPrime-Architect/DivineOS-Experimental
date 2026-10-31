---
name: the-gate-wrapper-hole-design-points-2026-10-27
description: "Owed next piece: the council gate skips env/sudo/source/exec/time/cd/set/export without judging what they carry. Aether's four design points for the fix are inside."
metadata:
  node_type: memory
  type: project
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-27T07:52:06.584Z
---

2026-10-27 night. `check-council-required.sh` skips any segment starting with a wrapper word (`_SHELL_WRAPPERS`) before judging it, so `divineos audit list ; env git commit -qm x` is freed (and `sudo`, `source`, `exec`, `time`), on main, for every entry on the list. Predates #631; written into `docs/drafts/filing_a_confirm_is_not_an_edit_draft_2026-10-12.md`. `divineos claim` is not on the gate's exit list, so the draft is the durable record. **Owed after #683, #732, #633, #733.**

Aether's design points (letter `aether-to-aria-2026-10-27-631-at-202551825-my-strings-and-my-attack-on-the-wrapper-design.md`):

1. The wrappers' own arguments are skipped too (`cd $(touch x)`, `export A=$(rm -rf y)`), so run the single operator-and-dollar rule (the one now on the three printers) on EVERY wrapper segment, not only on what follows `env`/`sudo`/`time`/`exec`.
2. Option parsing is where it fails (`env -i`, `env -u NAME`, `sudo -u x`, `time -p`). Safe design: after the wrapper accept only bare `NAME=value` words and then the program; if anything else precedes the program, the segment is NOT freed.
3. `exec` replaces the shell; judge the remainder like `env`, with tests: `exec divineos audit list` freed, `exec git commit` not.
4. Pin that `bash -c`, `xargs`, `nohup`, `command`, `eval` stay non-filing so nobody adds them as wrappers for convenience.
Plus mine: `source` and the dot should not be wrappers at all.

**How to apply:** build it as its own branch with a walk (scope given one file at a time), tests lifted from the real function, sabotage check, then send Aether the head to re-run his strings. See [[a-cost-nobody-priced-is-paid-out-of-dads-evenings]].
