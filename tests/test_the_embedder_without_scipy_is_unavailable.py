"""Without scipy the embedder says it is unavailable; it does not crash the memory.

encode() imported scipy's erf before loading the model, so on a machine without
scipy (the plain CI job: scipy arrives only with the sklearn extra) every memory
lookup raised ModuleNotFoundError, which retrieve_for_context does not catch.
Its docstring promises EmbedderUnavailable instead (council-6611e237b4d2).
"""

from __future__ import annotations

import sys

import pytest

from divineos.core import light_embedder


@pytest.fixture()
def no_scipy(monkeypatch):
    # A None entry in sys.modules makes `import scipy...` raise ImportError,
    # exactly as on a machine where it was never installed.
    monkeypatch.setitem(sys.modules, "scipy", None)
    monkeypatch.setitem(sys.modules, "scipy.special", None)
    monkeypatch.setattr(light_embedder, "_LOADED", None)


def test_encode_raises_unavailable_not_module_not_found(no_scipy):
    with pytest.raises(light_embedder.EmbedderUnavailable):
        light_embedder.encode("any sentence at all")


def test_available_says_why(no_scipy):
    ok, why = light_embedder.available()
    assert ok is False and why


def test_the_memory_lookup_returns_nothing_instead_of_crashing(no_scipy):
    from divineos.core.memory_linkage import retrieve_for_context

    assert retrieve_for_context("any prompt at all here", None) == []
