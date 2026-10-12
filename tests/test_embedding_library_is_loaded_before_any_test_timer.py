"""The shared test setup must import the embedding library before any test runs.

2026-10-12: a test over the 30 second limit kills its whole worker, and the first test that
needed the embedding library spent most of that budget importing it. The shared test setup
now imports it at worker start, where no timer runs.

The proof runs in fresh child interpreters. Checking ``sys.modules`` from inside a test would
pass whenever any earlier test in the same worker had imported the library, hook or no hook.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = str(Path(__file__).resolve())

needs_library = pytest.mark.skipif(
    importlib.util.find_spec("sentence_transformers") is None,
    reason="the embedding library is not installed here, so there is nothing to warm",
)

PROBE = (
    "import sys, pytest; "
    "pytest.main(['--collect-only', '-q', '-p', 'no:cacheprovider', '-n', '0', {extra}'{target}']); "
    "print('LIBRARY_LOADED' if 'sentence_transformers' in sys.modules else 'LIBRARY_ABSENT')"
)


def _collect_then_report(extra: str) -> str:
    """Start a fresh interpreter in the repo root, collect (not run) this file, and report
    whether the embedding library got loaded along the way."""
    code = PROBE.format(extra=extra, target=THIS_FILE.replace("\\", "/"))
    env = {k: v for k, v in os.environ.items() if k != "USE_TF"}
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=ROOT,
        env=env,
    )
    return done.stdout


@needs_library
@pytest.mark.timeout(240)  # a cold import of a heavy library; the very thing this change moves
def test_collecting_with_the_shared_setup_loads_the_embedding_library():
    assert "LIBRARY_LOADED" in _collect_then_report("")


@needs_library
@pytest.mark.timeout(240)
def test_control_collecting_without_the_shared_setup_leaves_it_unloaded():
    # Same child, same command, with the shared setup switched off. Without this, the test
    # above would pass if the probe could only ever say yes.
    assert "LIBRARY_ABSENT" in _collect_then_report("'--noconftest', ")
