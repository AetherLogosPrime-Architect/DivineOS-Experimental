# Bootcamp

Training exercises for stress-testing DivineOS across different cognitive modes.

## Session 3: Cold-Eyes Debugging

**Files:** `task_queue.py`, `test_task_queue.py`

A priority-based task queue with intentional bugs, given to the agent with no context.
Four real bugs found and fixed, one false diagnosis caught and reverted.

- `hashlib.md5()` missing `.encode()` on string input
- `add_batch()` dict overwrite silently dropping duplicate status
- `merge_task_stats()` division by zero when both queues empty
- Pluggable `sleep_fn` parameter to avoid real `time.sleep()` in tests

These files are training artifacts, not production DivineOS code.
