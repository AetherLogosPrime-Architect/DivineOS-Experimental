"""The embedding library must already be imported when the first test of a worker starts.

2026-10-12: a test over the 30 second limit kills its whole worker, and the first test that
needed the embedding library spent most of that budget importing it. The shared test setup
now imports it at worker start, where no timer runs.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest


@pytest.mark.skipif(
    importlib.util.find_spec("sentence_transformers") is None,
    reason="the embedding library is not installed here, so there is nothing to warm",
)
def test_the_embedding_library_is_already_imported_when_a_test_starts():
    # Nothing in this file imports it. If it is in sys.modules, the shared setup did.
    assert "sentence_transformers" in sys.modules
