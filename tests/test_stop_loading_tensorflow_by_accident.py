"""Importing divineos must stop the embedding library from importing TensorFlow.

2026-10-12: unexplained test-worker deaths ("node down: Not properly terminated") on every
push. The test runner kills a worker that spends more than 30 seconds in one test; the
first test in a worker that needed the embedding library spent 14-17 seconds importing it,
8 of them on TensorFlow, which nothing in this house uses, and any load pushed it past 30.
Measured: import sentence_transformers 13.9s with TensorFlow, 6.0s without.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import divineos

SRC = str(Path(__file__).resolve().parents[1] / "src")

needs_both = pytest.mark.skipif(
    importlib.util.find_spec("sentence_transformers") is None
    or importlib.util.find_spec("tensorflow") is None,
    reason="needs sentence_transformers and tensorflow installed to be a meaningful probe",
)

REPORT = "print('TENSORFLOW_LOADED' if 'tensorflow' in sys.modules else 'TENSORFLOW_ABSENT')"
WITH_DIVINEOS = f"import sys, divineos; import sentence_transformers; {REPORT}"
WITHOUT_DIVINEOS = f"import sys; import sentence_transformers; {REPORT}"


def test_importing_divineos_turns_tensorflow_off_for_the_embedding_library(monkeypatch):
    # Remove the variable first, so a value exported from outside the process
    # cannot make this pass without the package doing anything.
    monkeypatch.delenv("USE_TF", raising=False)
    importlib.reload(divineos)
    assert os.environ.get("USE_TF") == "0"


def _probe(code: str) -> str:
    """Run ``code`` in a fresh interpreter that sees THIS checkout's source, with USE_TF unset
    so only the package itself can have turned TensorFlow off."""
    env = {k: v for k, v in os.environ.items() if k != "USE_TF"}
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=180, env=env
    )
    return done.stdout


@needs_both
@pytest.mark.timeout(240)  # a cold import of a heavy library; the very thing this change speeds up
def test_the_embedding_library_no_longer_pulls_in_tensorflow_after_divineos_is_imported():
    assert "TENSORFLOW_ABSENT" in _probe(WITH_DIVINEOS)


@needs_both
@pytest.mark.timeout(240)
def test_control_the_same_probe_sees_tensorflow_when_divineos_is_not_imported():
    # Without this, the test above would pass if the probe were blind: this is the
    # behaviour the package had before the change, in the same interpreter and environment.
    assert "TENSORFLOW_LOADED" in _probe(WITHOUT_DIVINEOS)
