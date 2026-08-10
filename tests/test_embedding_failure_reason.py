"""An unavailable embedding model must say why.

2026-08-05: the substrate's semantic search ran keyword-only for an entire
session and nothing said why. Three swallows in a chain:

    _ensure_embedding_model   except (ImportError, RuntimeError, OSError)
                              -> _embeddings_available = False, reason gone
    compute_semantic_similarity / semantic_store.similarity
                              -> returns None, reason already gone
    divineos ask              -> prints "semantic re-rank unavailable"
                                 as a parenthetical caveat

Each layer was individually defensible. Together they turned a one-line
diagnosis into a shrug that was read past roughly fifty times, while every
`ask` returned word-overlap dressed as recall.

These tests pin the invariant that closes it: unavailable implies a reason.
No mocks -- they read the loader's real state and assert the contract holds
whichever way it resolves on this machine.
"""

from __future__ import annotations

from divineos.core.knowledge._text import (
    _ensure_embedding_model,
    embedding_unavailable_reason,
)


def test_unavailable_implies_a_stated_reason():
    """The load-bearing invariant. Failure without explanation is the bug."""
    available = _ensure_embedding_model()
    reason = embedding_unavailable_reason()

    if available:
        assert reason is None, (
            "model loaded but a failure reason is still recorded: "
            f"{reason!r} -- stale state would make a healthy system look broken"
        )
    else:
        assert reason, (
            "embeddings unavailable and NO reason recorded. This is the exact "
            "defect: a caller cannot distinguish 'not installed' from 'model "
            "produced an empty embedding', and both read as a shrug."
        )


def test_reason_names_the_interpreter_when_it_names_anything():
    """Which python is the missing half of the diagnosis.

    The 2026-08-05 root cause was that the sealed venv running the CLI lacked
    torch and sentence_transformers while the shell's interpreter had both.
    'ModuleNotFoundError: no module named torch' alone would have sent me
    checking the wrong environment.
    """
    if _ensure_embedding_model():
        return  # nothing to assert; covered by the test above
    reason = embedding_unavailable_reason()
    assert reason and "interpreter:" in reason, (
        f"failure reason omits the interpreter path: {reason!r}"
    )


def test_accessor_is_importable_from_the_layer_that_reports_it():
    """`divineos ask` imports this by name; a rename must break loudly here.

    The CLI reaches past similarity() to ask the loader directly, because
    similarity() returns None for several distinct faults and cannot say
    which. That cross-layer import is load-bearing and easy to break silently.
    """
    from divineos.core.knowledge._text import (
        embedding_unavailable_reason as accessor,
    )

    result = accessor()
    assert result is None or isinstance(result, str)
