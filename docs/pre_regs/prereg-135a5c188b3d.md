# Pre-registration: context_meter reads the latest transcript message.usage and treats input_tokens + cache_creation_input_tokens + cache_read_input_tokens as the current context-window occupancy — the ground-truth fullness signal pre_erasure.py lacks

- **ID**: `prereg-135a5c188b3d`
- **Filed by**: agent
- **Filed at**: 2026-05-29 22:11 UTC
- **Review at**: 2026-06-28 22:11 UTC (30d window)
- **Outcome**: **FAILED**
- **Decided at**: 2026-05-29 23:16 UTC

## Claim

The input-side token sum from the most-recent assistant turn's usage block accurately tracks real context-window fullness, accurately enough to time an early pre-compaction save at ~85% of the 970k ceiling

## Success criterion

divineos body shows a fullness pct that rises monotonically with session growth and matches independent estimates; when the governor wires onto it, the save fires with time to finish before compaction

## Falsifier

The input-side sum systematically diverges from true occupancy (e.g. cache_read overlaps cause double-count, or tool-result tokens are undercounted), OR the reading misparses real Claude Code transcripts, OR 85% fires too late to finish a ~64s save — any of which makes threshold-timing unreliable

## Outcome notes

Redundant — context_meter duplicates the EXISTING context_governor.current_context_tokens (built 2026-05-27, prereg-9b958c6493f3). This pre-reg pre-registered a reinvention I made without globbing filenames for an existing governor. Mechanism works but already existed; withdrawing. Root cause + lesson in task #7 + #13.
