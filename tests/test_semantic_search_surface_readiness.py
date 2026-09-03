"""The two things that stood between meaning-search and the per-turn surface.

Both were found by measurement on the real corpus (2026-09-03), and both are
the kind of defect that returns plausible output rather than an error — so a
test that only asserts "results came back" would pass while either was broken.
Each test here asserts the specific discrimination the fix exists to make.
"""

from __future__ import annotations

import numpy as np
import pytest

from divineos.core import semantic_search
from divineos.core.semantic_search import Chunk, index_corpus, search

pytestmark = pytest.mark.usefixtures()


def _write(tmp_path, name: str, paragraphs: list[str]):
    p = tmp_path / name
    p.write_text("\n\n".join(paragraphs), encoding="utf-8")
    return str(p)


def _model_available() -> bool:
    from divineos.core.semantic_store import embed

    return embed("probe") is not None


requires_model = pytest.mark.skipif(
    not _model_available(), reason="embedding model not installed in this environment"
)


@requires_model
def test_short_fragments_are_excluded_when_a_floor_is_set(tmp_path):
    """A near-contentless line must not be able to win a slot.

    The real failure: the four-word line "Dad will relay your reply." was
    returned as one of the top three for a question about Andrew being unable
    to follow technical detail. A very short sentence carries little meaning,
    so it sits near everything — and nothing in the result would have told a
    reader it was noise rather than a find.
    """
    src = _write(
        tmp_path,
        "corpus.md",
        [
            # Long enough to clear the chunker's own 20-char floor and short
            # enough to be the noise the search-time floor exists to catch.
            # The gap between those two numbers is where the real bad hit
            # lived, and the first draft of this test sat below the chunker's
            # floor instead — so it was testing nothing.
            "Dad will relay your reply back to me.",
            (
                "The rule is that any technical word used to describe a fix should be "
                "checked against whether the reader actually holds that term, and "
                "replaced with a plain phrase when they do not."
            ),
        ],
    )
    db = str(tmp_path / "index.db")
    counts = index_corpus([src], db)
    assert counts["chunks_indexed"] == 2, counts

    query = "explaining technical things to someone who cannot follow the jargon"
    unfiltered = search(query, db, top_k=5)
    filtered = search(query, db, top_k=5, min_chars=120)

    assert any(len(h.text) < 120 for h in unfiltered), (
        "precondition: the short fragment must be reachable without a floor, "
        "or this test is not exercising the filter"
    )
    assert filtered, "the substantive paragraph must still be returned"
    assert all(len(h.text.strip()) >= 120 for h in filtered)


@requires_model
def test_failed_embeddings_are_counted_not_silently_skipped(tmp_path, monkeypatch):
    """A chunk that cannot be embedded is a failure, never an absence.

    This is the defect that kept the whole corpus unindexed for months: the
    index loop dropped un-embeddable chunks with no counter, so a missing
    library rendered as a clean "indexed: 0" that looked like nothing needed
    doing.
    """
    src = _write(
        tmp_path,
        "corpus.md",
        [
            "A paragraph with enough substance in it to survive the chunker's floor.",
            "Another paragraph, also long enough to be chunked and counted properly.",
        ],
    )
    db = str(tmp_path / "index.db")
    monkeypatch.setattr(semantic_search, "embed", lambda *a, **k: None)
    counts = index_corpus([src], db)

    assert counts["chunks_seen"] == 2
    assert counts["chunks_indexed"] == 0
    assert counts["chunks_failed"] == 2, (
        "the failures must be reported; a silent skip is what made this "
        "invisible in the first place"
    )


@requires_model
def test_light_runtime_returns_the_same_vectors_as_the_original(tmp_path):
    """The fast query path must BE the model that built the index.

    If it drifts, searches keep returning plausible results while comparing
    against a meaning-space the index was never built in — the failure that
    never announces itself.
    """
    from divineos.core.onnx_embed import artifacts_present, embed_texts_onnx
    from divineos.core.semantic_store import embed

    if not artifacts_present():
        pytest.skip("light runtime not exported on this machine")

    probes = [
        "a review bound to a diff rather than to a branch tip",
        "short",
        "the pull to close the loop before checking the work",
    ]
    fast = embed_texts_onnx(probes)
    assert fast is not None
    for probe, fast_vec in zip(probes, fast, strict=True):
        ref = np.asarray(embed(probe), dtype=np.float32)
        ref = ref / np.linalg.norm(ref)
        agreement = float(np.dot(ref, fast_vec))
        assert agreement > 0.9999, f"{probe!r} drifted: agreement {agreement:.6f}"


def test_chunk_dataclass_carries_its_source_pointer():
    """Cheap guard on the contract the search result depends on."""
    c = Chunk(source_path="x.md", paragraph_index=3, text="body")
    assert c.source_path == "x.md"
    assert c.paragraph_index == 3
