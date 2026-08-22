# Audit round: root-cause-audit: silent-critical-failure family — critical operations (saves, extractions, checkpoints) that pipe errors to /dev/null and fail invisibly, so failure is indistinguishable from success. Instance found 2026-05-29: pre-compact hook ran extract 2>/dev/null under a 15s timeout vs 64s runtime, losing a full day silently. Survey: where else in hooks + pipeline does a critical op swallow its own failure?

- **ID**: `round-e0c8c3a1ae39`
- **Filed by**: aether
- **Filed at**: 2026-05-29 19:54 UTC
- **Tier**: WEAK
- **Findings**: 1

## Notes

Source ref: fix-precompact-timeout-and-silent-failure


## Findings

### silent-critical-failure: two instances found + fixed this session

- **ID**: `find-a64d44ec586d`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Failure-family: critical operations that swallow their own failure (pipe to /dev/null, over-narrow except, timeouts that ignore measured duration) so failure is indistinguishable from success. Instances found 2026-05-29 in the save/compaction path: (1) pre-compact.sh ran 'divineos extract 2>/dev/null' under a 15s timeout vs measured 64s runtime — every compaction killed the save silently, losing a full day [fixed: commit 4bb774d logs OK/FAILED; settings.json 15->300 held for review]. (2) session_pipeline early-orientation write caught only (ImportError,OSError,sqlite3.OperationalError), NOT Runtime('No active session') write_handoff_note can raise — a protective wrapper with a hole that crashes the thing it protects [fixed: commit 42a7a8ff broadens to except Exception]. Surveyed instance: this substrate's save path. Sibling-survey (other hooks, other 2>/dev/null sites) handed to Aletheia from the outside vantage.

**Resolution**

Both instances fixed and the fix commits are cited inline in the finding body. Verified: 4bb774d (pre-compact: log OK/FAILED + raise timeout 15->300) and 42a7a8ff (session_pipeline early-orientation broadened catch). Sibling-survey was handed off to Aletheia per the finding; that's an external task, not this finding's scope. Closing as RESOLVED on the named instances.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
