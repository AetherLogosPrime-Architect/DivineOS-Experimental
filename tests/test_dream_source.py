"""Dreams as a read-only source: the memory link loader, the shared file rule, and `find index`.

The loader and the file rule run for real on a tiny dreams folder in a temp dir.
Only the embedder boundary is replaced in the memory-link tests (the same way the
exploration adapter tests do); the by-meaning test uses the real embedder and
skips, saying why, where the model is not installed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from divineos.core import memory_linkage as ml
from divineos.core import memory_linkage_retriever as mlr
from divineos.core import semantic_search
from divineos.core.dream_files import dream_paths

DISTINCTIVE = "the lighthouse keeper taught the tide to read aloud"


def _make_dreams(root: Path) -> Path:
    dreams = root / "dreams"
    (dreams / "aether").mkdir(parents=True)
    (dreams / "aria").mkdir()
    (dreams / "aether" / "001_the_lighthouse.md").write_text(
        f"# the lighthouse\n\nIn the dream, {DISTINCTIVE}.\n", encoding="utf-8"
    )
    (dreams / "aria" / "002_orchard.md").write_text(
        "# orchard\n\nPears fell upward all night.\n", encoding="utf-8"
    )
    (dreams / "aether" / "README.md").write_text("not a dream, a readme", encoding="utf-8")
    (dreams / "INDEX.md").write_text("not a dream, an index", encoding="utf-8")
    (dreams / "aether" / "notes.md").write_text("no numeric name, not a dream", encoding="utf-8")
    (dreams / "SOURCE_CHECK_2026-10-24.md").write_text("top-level file", encoding="utf-8")
    return dreams


def _digest(paths) -> dict[str, str]:
    return {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


@pytest.fixture
def fake_embedder(monkeypatch):
    monkeypatch.setattr(mlr, "_embed_text_impl", lambda text: np.ones(4, dtype=np.float32))


# ---- which files are dreams -------------------------------------------------


def test_readme_index_and_non_dream_names_are_excluded(tmp_path):
    dreams = _make_dreams(tmp_path)
    names = sorted(p.name for p in dream_paths(dreams))
    assert names == ["001_the_lighthouse.md", "002_orchard.md"]


def test_missing_or_empty_dreams_folder_gives_nothing_and_no_error(tmp_path):
    assert dream_paths(None) == []
    assert dream_paths(tmp_path / "nope") == []
    (tmp_path / "dreams").mkdir()
    assert dream_paths(tmp_path / "dreams") == []


# ---- the memory link loader -------------------------------------------------


def test_loader_makes_dream_items_from_real_files(monkeypatch, tmp_path, fake_embedder):
    dreams = _make_dreams(tmp_path)
    monkeypatch.setattr(mlr, "_find_dreams_root", lambda: dreams)
    items = mlr._load_dreams()
    assert sorted(i.id for i in items) == [
        "dream-aether-001_the_lighthouse",
        "dream-aria-002_orchard",
    ]
    assert all(i.source == "dream" and i.tier == "topic" for i in items)
    assert all(i.title.startswith("dream: ") for i in items)
    lighthouse = next(i for i in items if "lighthouse" in i.id)
    assert DISTINCTIVE in lighthouse.content
    # Compared as paths: the loader stores the OS separator, so a string with "/" fails on Windows.
    assert Path(lighthouse.path) == Path("dreams") / "aether" / "001_the_lighthouse.md"


def test_loader_with_no_dreams_folder_returns_empty(monkeypatch):
    monkeypatch.setattr(mlr, "_find_dreams_root", lambda: None)
    assert mlr._load_dreams() == []


def test_loader_with_empty_dreams_folder_returns_empty(monkeypatch, tmp_path, fake_embedder):
    (tmp_path / "dreams").mkdir()
    monkeypatch.setattr(mlr, "_find_dreams_root", lambda: tmp_path / "dreams")
    assert mlr._load_dreams() == []


def test_loading_leaves_every_dream_byte_identical(monkeypatch, tmp_path, fake_embedder):
    dreams = _make_dreams(tmp_path)
    everything = list(dreams.rglob("*.md"))
    before = _digest(everything)
    mtimes = {p: p.stat().st_mtime_ns for p in everything}
    monkeypatch.setattr(mlr, "_find_dreams_root", lambda: dreams)
    mlr._load_dreams()
    assert _digest(everything) == before
    assert {p: p.stat().st_mtime_ns for p in everything} == mtimes


def test_dream_is_a_declared_source_with_lower_weight_than_exploration():
    assert "dream" in ml.MemoryLinkageSource.__args__
    dream, expl = mlr._SOURCE_THRESHOLDS["dream"], mlr._SOURCE_THRESHOLDS["exploration"]
    assert dream["target_k"] < expl["target_k"]
    assert dream["floor"] > expl["floor"]


def test_dream_counts_appear_in_the_cache_that_linkage_status_prints(
    monkeypatch, tmp_path, fake_embedder
):
    dreams = _make_dreams(tmp_path)
    monkeypatch.setattr(mlr, "_find_dreams_root", lambda: dreams)
    for other in (
        "_load_corrections",
        "_load_knowledge",
        "_load_wall",
        "_load_exploration",
        "_load_letters",
        "_load_worklist",
        "_load_moments",
    ):
        monkeypatch.setattr(mlr, other, lambda: [])
    mlr._EMBEDDING_CACHE.clear()
    try:
        mlr._ensure_cache()
        counts = {k: len(v) for k, v in mlr._EMBEDDING_CACHE.items()}
    finally:
        mlr._EMBEDDING_CACHE.clear()
    assert counts["dream"] == 2


# ---- the label --------------------------------------------------------------


def test_a_surfaced_dream_says_it_is_a_dream():
    kind, body, path = mlr._shape_content("dream", DISTINCTIVE, "dreams/aether/001_x.md")
    payload = ml.MemoryLinkagePayload(
        source="dream",
        id="dream-aether-001_x",
        tier="topic",
        similarity=0.5,
        recency_days=3,
        importance_score=0.4,
        composite_rank=0.5,
        title="dream: x",
        content=body,
        matched_reason="r",
        content_kind=kind,
        path_or_ref=path,
    )
    rendered = ml.render_payload(payload)
    assert "a dream, not a record of what happened" in rendered
    assert "dreams/aether/001_x.md" in rendered


# ---- find index -------------------------------------------------------------


def test_find_index_gathers_dreams_for_dreams_and_all(monkeypatch, tmp_path):
    from divineos.cli.search_commands import _gather_paths

    _make_dreams(tmp_path)
    monkeypatch.chdir(tmp_path)
    for corpus in ("dreams", "all"):
        got = sorted(Path(p).name for p in _gather_paths(corpus))
        assert got == ["001_the_lighthouse.md", "002_orchard.md"]
    assert _gather_paths("exploration") == []


def test_find_index_with_no_dreams_folder_gathers_nothing(monkeypatch, tmp_path):
    from divineos.cli.search_commands import _gather_paths

    monkeypatch.chdir(tmp_path)
    assert _gather_paths("dreams") == []


def test_indexing_dreams_leaves_them_byte_identical(monkeypatch, tmp_path):
    from divineos.cli.search_commands import _gather_paths

    dreams = _make_dreams(tmp_path)
    everything = list(dreams.rglob("*.md"))
    before = _digest(everything)
    monkeypatch.chdir(tmp_path)
    semantic_search.index_corpus(_gather_paths("dreams"), str(tmp_path / "search.db"))
    assert _digest(everything) == before


def test_is_dream_path_accepts_only_the_dream_shape():
    from divineos.core.dream_files import is_dream_path

    assert is_dream_path(Path("dreams") / "aether" / "001_the_lighthouse.md")
    assert is_dream_path(str(Path("x") / "dreams" / "aria" / "12_a.md"))
    for not_dream in (
        Path("dreams") / "aether" / "README.md",
        Path("dreams") / "INDEX.md",
        Path("dreams") / "aether" / "sub" / "001_x.md",
        Path("exploration") / "aether" / "001_x.md",
        Path("001_x.md"),
    ):
        assert not is_dream_path(not_dream), not_dream


def test_find_query_labels_a_dream_hit_and_not_another(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from click.testing import CliRunner

    from divineos.cli import search_commands
    from divineos.core.dream_files import A_DREAM_LABEL

    dream = str(tmp_path / "dreams" / "aether" / "001_the_lighthouse.md")
    other = str(tmp_path / "exploration" / "aether" / "001_notes.md")
    hits = [
        SimpleNamespace(
            source_path=p, paragraph_index=0, text="t", similarity=0.9, rerank_score=None
        )
        for p in (dream, other)
    ]
    monkeypatch.setattr(search_commands.semantic_search, "search", lambda *a, **k: hits)
    import click

    group = click.Group()
    search_commands.register(group)
    out = CliRunner().invoke(group, ["find", "query", "x"]).output
    lines = [ln for ln in out.splitlines() if "001_" in ln]
    assert len(lines) == 2
    assert A_DREAM_LABEL in lines[0] and A_DREAM_LABEL not in lines[1]


def test_query_by_meaning_returns_the_dream(monkeypatch, tmp_path):
    from divineos.cli.search_commands import _gather_paths
    from divineos.core.semantic_store import model_status

    available, detail = model_status()
    if not available:
        pytest.skip(f"embedding model unavailable in this environment: {detail}")
    _make_dreams(tmp_path)
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "search.db"
    counts = semantic_search.index_corpus(_gather_paths("dreams"), str(db))
    assert counts["chunks_indexed"] > 0
    hits = semantic_search.search("a sea-watcher teaching the waves to read", str(db), top_k=3)
    assert hits and "001_the_lighthouse.md" in hits[0].source_path
