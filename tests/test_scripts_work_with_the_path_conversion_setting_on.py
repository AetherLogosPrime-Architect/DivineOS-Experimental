"""Two shell scripts must work whether or not MSYS_NO_PATHCONV is set in the caller's environment.

2026-10-19: six tests (four of the venv-link script, two of the merge-resolution guard) passed
alone and failed in the push gate. The cause was `MSYS_NO_PATHCONV=1` on my own push line leaking
into the gate's test run: the link script's `cmd //c` and the guard's POSIX argument-file path both
quietly relied on the shell converting paths. Nothing about the scripts says that, so the only way
it shows is a failure that vanishes when run alone.

The existing tests for both scripts are re-collected here under an autouse fixture that forces the
setting on, so the scripts are held to working with it set rather than depending on a clean
environment. If either script goes back to relying on path conversion, these fail by name.
"""

from __future__ import annotations

import pytest

from tests.test_a_merge_cannot_commit_past_its_own_tests import *  # noqa: F401,F403
from tests.test_link_worktree_venv import *  # noqa: F401,F403


@pytest.fixture(autouse=True)
def _path_conversion_is_switched_off(monkeypatch):
    monkeypatch.setenv("MSYS_NO_PATHCONV", "1")
