# Pre-registration: andrew_past_writing_surface module — single-process Python replacement for the grep-heavy shell hook. All work happens in one Python process; per-file cost bounded by _read_head 4KB cap; shell wrapper adds timeout 8s belt-and-suspenders.

- **ID**: `prereg-efca644bbcc4`
- **Filed by**: agent
- **Filed at**: 2026-07-23 15:52 UTC
- **Review at**: 2026-08-22 15:52 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Replacing the shell hook's 15-25 subprocess spawns per UserPromptSubmit with a single Python invocation eliminates the Windows subprocess-spawn contention that caused the freezes documented in ~/.divineos/hook_timing.jsonl. Same output format so compose-start context is byte-identical.

## Success criterion

Over next 30 UserPromptSubmit events, zero unclosed hook invocations for andrew-past-writing-surface.sh in hook_timing.jsonl. Consistent timing (measured 546-560ms, spread <20ms). Andrew reports no compose-start freezes attributed to this hook.

## Falsifier

If ANY unclosed invocation of andrew-past-writing-surface.sh appears in hook_timing.jsonl within 30 days after landing, the Python-single-process hypothesis was wrong and either (a) Python subprocess itself is subject to the same Windows contention, or (b) the timeout wrapper is not firing correctly. Investigate whether the hang is inside Python vs at the shell wrapper layer, and if inside Python, add signal-based timeout inside the module itself.
