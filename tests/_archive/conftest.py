"""Prevent pytest from collecting the archived test files.

Files under tests/_archive/ are preserved for historical audit reference
after design rewrites; they test gone-by-design behavior and should NOT
run in CI or the pre-push test suite. The `collect_ignore_glob` hook
tells pytest to skip all test_*.py files in this directory.

The archive itself is documented by the containing rewrite commit
(2026-07-22 correction-detector three-feature semantic rewrite).
"""

from __future__ import annotations

collect_ignore_glob = ["test_*.py"]
