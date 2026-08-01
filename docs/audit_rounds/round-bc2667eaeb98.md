# Audit round: root-cause-audit: destructive-mutation-on-conflicted-state — tooling that appends/rewrites a file by parsing it, run while the file holds unresolved git conflict markers, duplicates content into ghosts. Instance: check_doc_counts.py --fix appended into a conflicted docs/ARCHITECTURE.md and mangled the tree (PR #213, knowledge a9e533c2). Survey: where else does --fix-style tooling mutate parsed state without first checking the file is conflict-free?

- **ID**: `round-bc2667eaeb98`
- **Filed by**: aether
- **Filed at**: 2026-05-29 21:37 UTC
- **Tier**: WEAK
- **Findings**: 1

## Notes

Source ref: doc-counts-conflict-guard


## Findings

### destructive-mutation-on-conflicted-state: check_doc_counts --fix ghost-mangle, guarded

- **ID**: `find-86afa06dafce`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Instance + fix (this branch): check_doc_counts.py --fix appended undocumented-file entries into docs/ARCHITECTURE.md by blind regex-match; run while the file held unresolved conflict markers, it duplicated entries into ghost files and mangled the tree (PR #213, knowledge a9e533c2). Fix: _files_with_conflict_markers() guard refuses --fix and returns 1 if any mutation-target doc (CLAUDE.md, README.md, seed.json, ARCHITECTURE.md) contains '<<<<<<<'/'>>>>>>>' markers, with a clear resolve-first message. Keys on angle-bracket markers not '=======' to avoid false-positives on Markdown rules. Tested: TestConflictMarkerGuard (4 cases incl. the markdown-equals false-positive guard). Survey handed forward: other --fix-style mutators (fix_test_counts/fix_hook_counts share the same targets, now covered by the same guard); audit whether other repo tooling mutates parsed state without a conflict-free precheck.

**Resolution**

Guard implemented and tested. Verified: scripts/check_doc_counts.py:617 _files_with_conflict_markers(); called from --fix path at line 664. Tests at tests/test_check_doc_counts.py::TestConflictMarkerGuard (4 cases including the markdown-equals false-positive). Survey of other --fix mutators handed to the survey backlog (separate concern).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
