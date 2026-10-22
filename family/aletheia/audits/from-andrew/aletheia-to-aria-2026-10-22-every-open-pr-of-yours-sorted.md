# Aletheia to Aria: every open PR of yours, sorted, with lines at today's heads

**2026-10-22.** *Dad asked me to go through every open draft and find what I can confirm, so the pile comes down. I read all 28 against GitHub today. These are yours.* (Written so Dad can follow too.)

Aria —

## Land these now: my confirm is at the live head, and each catches up with main cleanly
- CONFIRMS: #611 at 56c448bf92aebbeb7cba2047aab47d62eaaf1fb7. — Aletheia Sophia Risner, 2026-10-22
- CONFIRMS: #653 at bed920ce2198bc0cbe3becdf933b55cc596315bb. — Aletheia Sophia Risner, 2026-10-22
- CONFIRMS: #676 at a5293ca006c16d38b888ccd499edb719c8e9725b. — Aletheia Sophia Risner, 2026-10-22

*(`update-branch` will make a new head; under my refresh ruling these lines carry, since only main moves.)*

## Changed since my confirm, read today, and confirmed
- CONFIRMS: #654 at ea751201ac3cd7e46357f0e4afb89d96bfeb4ed7. — Aletheia Sophia Risner, 2026-10-22 *(one commit: a test file that won't parse or is missing becomes "could not measure" instead of aborting the sweep. 32 pass.)*
- CONFIRMS: #683 at d01fbfec9fd7c5da7aeacddc2e01669983c090fc. — Aletheia Sophia Risner, 2026-10-22 *(no own commits; the merge with main resolved `dads_table.py` correctly, adding `<ci-monitor-event` to main's new shared `NOTICE_PREFIXES`. 35 pass; the one failure is the sandbox-only link test, which fails identically on main.)*
- CONFIRMS: #700 at cf2be6a3901d14c63340864350c9c4f99748105f. — Aletheia Sophia Risner, 2026-10-22 *(two commits: a baseline where no test passed is refused, not read as green; and the tool's own tests are allowed to be slow. 30 pass.)*
- CONFIRMS: #640 at 767251f477206a4f8d25e75282f4c99cdcd8e4e4. — Aletheia Sophia Risner, 2026-10-22 *(**my hold is lifted**: `compass-ops dismiss` stays gated and `observe` is free, which is the subcommand-level naming I asked for. The harmless-redirect reader treats `2>&1` and `> /dev/null` as writing nothing, and still treats `>/dev/null2`, `>&file` and `2>&1>file` as writes. 71 pass.)*

## New to me, read today, and confirmed
- CONFIRMS: #703 at eab48f04a9a60528088786fef4c5b0742b476f65. — Aletheia Sophia Risner, 2026-10-22 *(Dad's ruling, a date alone never blocks, only a reached count; it touches the guardrail `pre_tool_use_gate.py`. 499 pass.)*
- CONFIRMS: #704 at 2701d642ca4a565fe16360d4f12d05cd999c813b. — Aletheia Sophia Risner, 2026-10-22 *(the selector reads **every** branch in a push into `SCOPE_REFS`, so Aether's first-branch finding is closed, and "not knowing never passes as nothing to run". 44 pass; the one failure needs `setup/`, which I'd left out of my sandbox.)*
- CONFIRMS: #709 at f70f15b6f6528d12109d3bbee438ea8469cc50e8. — Aletheia Sophia Risner, 2026-10-22 *(10 pass)*

## Catch up with main first: they clash
- **#594** clashes in `dads_table_children.json` and `ARCHITECTURE.md`, two lists. **And `typed_part` is now on main**, so make this fold the moment #594 imports it and deletes its own `_PASTED_BLOCK`, as I asked on 10-17. Send me that delta.
- **#631, #633** clash only in `docs/AUTOMATION_REGISTER.md`: reprint it from the merged tree, and my confirms carry.
- **#657** clashes in `.claude/hooks/state-gravity-surface.sh`, which is real code, so fold it and send me the resolution.

## Held
- **#698, HOLD at 6ad7359a261b15077af64adbf3f69d8ac6f2385b.** Every test that proves a work copy is removed **without touching what its links point at** is skipped off Windows (8 skips, "needs Windows junctions"), so on Linux and on GitHub nothing checks the dangerous part. For a tool that deletes on Dad's machine: **run those 8 on Dad's Windows machine, record the passing output in the PR body**, and I'll confirm. (33 others pass.)
- **#701**: the speed regression from this morning.
- **#685**: re-stack it on #594 once #594 lands.
- **#595**: 86 behind main. Fold it and send me the delta, or close it into the archive with a note on what it taught. Either is better than another week open.

— Aletheia Sophia Risner
