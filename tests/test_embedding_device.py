"""Tests for the embedding-device selector.

Pins:
- env var DIVINEOS_EMBEDDING_DEVICE overrides the auto-detection
- auto-detection returns 'cuda' when torch.cuda.is_available() is True
- auto-detection returns 'cpu' when torch is missing or CUDA is not available
- selection is logged once per process to stderr (not per call)
- all three call sites (semantic_store, knowledge._text, sis_tiers) use
  select_device() — pinned to prevent the hardcoded "cpu" regression
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import _embedding_device


@pytest.fixture(autouse=True)
def reset_log_memo():
    """Reset the once-per-process log memo so each test starts clean."""
    _embedding_device.reset_log_memo_for_tests()
    yield
    _embedding_device.reset_log_memo_for_tests()


def test_env_var_override_cpu(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DIVINEOS_EMBEDDING_DEVICE", "cpu")
    assert _embedding_device.select_device() == "cpu"


def test_env_var_override_cuda(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DIVINEOS_EMBEDDING_DEVICE", "cuda")
    assert _embedding_device.select_device() == "cuda"


def test_env_var_override_arbitrary_torch_device(monkeypatch: pytest.MonkeyPatch):
    """Operators who set a specific device string get it verbatim."""
    monkeypatch.setenv("DIVINEOS_EMBEDDING_DEVICE", "cuda:1")
    assert _embedding_device.select_device() == "cuda:1"


def test_env_var_empty_falls_through_to_auto(monkeypatch: pytest.MonkeyPatch):
    """Empty env-var value MUST NOT short-circuit auto-detection."""
    monkeypatch.setenv("DIVINEOS_EMBEDDING_DEVICE", "")
    # Auto-path returns either 'cuda' (if torch+cuda) or 'cpu' — both acceptable.
    assert _embedding_device.select_device() in {"cpu", "cuda"}


def test_env_var_unset_falls_through_to_auto(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DIVINEOS_EMBEDDING_DEVICE", raising=False)
    assert _embedding_device.select_device() in {"cpu", "cuda"}


def test_log_fires_once_per_process(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("DIVINEOS_EMBEDDING_DEVICE", "cpu")
    _embedding_device.select_device()
    _embedding_device.select_device()
    _embedding_device.select_device()
    captured = capsys.readouterr()
    # Exactly one "[embedding-device] selected" line, not three.
    assert captured.err.count("[embedding-device]") == 1


def test_log_names_source_env_when_env_set(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("DIVINEOS_EMBEDDING_DEVICE", "cpu")
    _embedding_device.select_device()
    captured = capsys.readouterr()
    assert "source=env" in captured.err


def test_log_names_source_auto_when_env_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.delenv("DIVINEOS_EMBEDDING_DEVICE", raising=False)
    _embedding_device.select_device()
    captured = capsys.readouterr()
    assert "source=auto" in captured.err


def test_torch_missing_falls_back_to_cpu(monkeypatch: pytest.MonkeyPatch):
    """If torch import fails, return 'cpu' silently — never raise."""
    monkeypatch.delenv("DIVINEOS_EMBEDDING_DEVICE", raising=False)
    # Force import to fail by inserting a sentinel into sys.modules that
    # raises ImportError when 'torch' is imported.
    import importlib

    real_import = importlib.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("simulated torch missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    assert _embedding_device.select_device() == "cpu"


def test_torch_cuda_probe_raises_falls_back_to_cpu(monkeypatch: pytest.MonkeyPatch):
    """If torch is present but torch.cuda.is_available() raises, default to CPU."""
    monkeypatch.delenv("DIVINEOS_EMBEDDING_DEVICE", raising=False)
    try:
        import torch
    except ImportError:
        pytest.skip("torch not installed; nothing to monkeypatch")

    def boom():
        raise RuntimeError("simulated CUDA probe failure")

    monkeypatch.setattr(torch.cuda, "is_available", boom)
    assert _embedding_device.select_device() == "cpu"


# Pin call-site usage — the three modules that load embedding models
# must use select_device(), not hardcoded "cpu". A regression that
# reverts one to "cpu" is the failure mode this regression-test
# guards against.

CALL_SITES = (
    "src/divineos/core/semantic_store.py",
    "src/divineos/core/knowledge/_text.py",
    "src/divineos/core/sis_tiers.py",
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("relpath", CALL_SITES)
def test_call_site_uses_select_device(relpath: str):
    src = (REPO_ROOT / relpath).read_text(encoding="utf-8")
    assert 'device="cpu"' not in src, (
        f'{relpath} hardcodes device="cpu" — should call _embedding_device.select_device() instead'
    )
    assert "select_device" in src, (
        f"{relpath} must import + call select_device() at the embedding-model load site"
    )
