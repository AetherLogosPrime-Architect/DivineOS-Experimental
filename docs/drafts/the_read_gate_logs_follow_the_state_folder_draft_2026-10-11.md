# The read gate's logs follow the state folder (draft, 2026-10-11)

**Author:** Aether. Step 0 of Aria's plan `old_writing_arrives_as_passages_draft_2026-10-11.md`; her measurement in her letters of 2026-10-11 (63% of her seat's clears log is test debris; mine counts about 78% by line).

## The fault

`core/read_gate.py` fixes three file paths when the module loads: `REARM_LOG`, `SEEN_READS`, `CLEAR_LOG`, each `STATE_DIR / "<name>"`. The tests patch `STATE_DIR` (the documented seam) and `STATE_FILE`, but not those three, so every test that arms or clears the gate writes fixture rows into the LIVE logs. Its own cooldown path was fixed the same way once (`_cooldown_file()`, resolved from `STATE_DIR` at call time) and these three were left behind.

Cost: every number computed from the live log is inflated, including the prereg review of the gate and Aria's baseline (she had to exclude test rows by path).

## The change

- Three small functions, `_rearm_log()`, `_seen_reads()`, `_clear_log()`, each returning `STATE_DIR / "<name>"` at call time, exactly as `_cooldown_file()` does. The three module constants are removed, so nothing can patch a name that no longer decides anything.
- The three test files that patched the constants now patch `STATE_DIR` (one seam, everything derived follows).
- One autouse fixture in `tests/conftest.py` points `read_gate.STATE_DIR` (and `STATE_FILE`) at the test's own home. Walk finding (Pearl, Deming, Meadows): the functions alone cut the arrow for the three derived paths, but `STATE_DIR` is itself frozen at import, so a test that patches nothing still writes live. Isolation has to be the default for every test, present and future, not something each author remembers.
- Each clear row also records the transcript key the seen-reads file already holds (the module's own idea of "this session"), so a repeat delivery inside one session can be told apart from one in another (Aria could not find the cause of the roughly 10% same-session repeats for lack of this). No new session source is invented.

## What proves it

1. A test that points `STATE_DIR` at a scratch folder, makes the gate arm, clear and re-arm, and asserts the scratch folder holds the three logs and the folder the module loaded from holds none of them.
2. A scan test: no module-level name in `read_gate` is a `Path` under `STATE_DIR` except `STATE_FILE` (the one documented seam, named), so a fourth frozen path fails by name.
3. The existing read-gate tests still pass with the seam moved.

## Not in this change, said plainly

- `STATE_FILE` (pending requirements) stays a module constant because tests patch it by name; moving it is a separate piece.
- The roughly 78% of debris already in the live log stays (append-only); the baseline script excludes it by path.
- The compaction epoch is not recorded: no existing source for it, and inventing one is a separate piece.

## Falsifier (an event)

After this lands, a full test run changes the live `read_gate_clears.jsonl` in any way (size or hash). That event means a path the scan did not see is still frozen, and the test that failed to catch it is the thing to fix first.
