"""CLI surface for the semantic-search consumer.

Per Norman + Bengio council lenses: the command MUST be short and
visible. ``divineos find query "<text>"`` — three subcommands,
``query`` being the common path. Click's parent-group argument
parsing collides with subcommand dispatch when both are defined, so
the design is explicit subcommands.

Three subcommands:
- ``divineos find query "<text>"`` — search the indexed corpus
- ``divineos find index`` — chunk + embed + store the exploration
  entries (and optionally other corpora) into the search DB
- ``divineos find stats`` — describe the current index state

See ``src/divineos/core/semantic_search.py`` for the design notes and
pre-reg ``prereg-2ad79e23fcf7``.
"""

from __future__ import annotations

from pathlib import Path

import click

from divineos.core import semantic_search
from divineos.core._ledger_base import data_dir as get_data_dir

_DB_NAME = "semantic_search.db"


def _db_path() -> str:
    return str(Path(get_data_dir()) / _DB_NAME)


def register(cli: click.Group) -> None:
    @cli.group("find", invoke_without_command=True)
    @click.pass_context
    def search_group(ctx: click.Context) -> None:
        """Semantic search across the indexed prose corpus.

        Distinct from ``divineos search``, which does keyword search over
        ledger events. ``divineos find`` does meaning-based search over
        exploration entries / family letters / knowledge prose. Two stores,
        two purposes; the name parallels the distinction.
        """
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @search_group.command("query")
    @click.argument("text")
    @click.option("--top", "-n", default=5, help="How many results to show (default 5)")
    @click.option(
        "--min-similarity",
        default=0.0,
        type=float,
        help="Drop results below this cosine similarity (default 0, no filter)",
    )
    @click.option(
        "--rerank",
        is_flag=True,
        default=False,
        help=(
            "Apply a cross-encoder second pass after the embedding search. "
            "Fetches --rerank-pool candidates from the first pass, scores "
            "each (query, chunk) pair with the cross-encoder, returns the "
            "top --top by that score. Slower but better at finding the "
            "chunk that actually answers the question."
        ),
    )
    @click.option(
        "--rerank-pool",
        default=25,
        type=int,
        help=(
            "How many first-pass candidates the reranker sees (default 25). "
            "Only meaningful with --rerank."
        ),
    )
    def search_query_cmd(
        text: str, top: int, min_similarity: float, rerank: bool, rerank_pool: int
    ) -> None:
        """Search the indexed corpus for chunks semantically similar to TEXT."""
        first_pass_k = max(rerank_pool, top) if rerank else top
        hits = semantic_search.search(
            text, _db_path(), top_k=first_pass_k, min_similarity=min_similarity
        )
        if not hits:
            click.echo(
                f'(no hits for "{text}" — corpus may not be indexed yet. Run: divineos find index)'
            )
            return
        if rerank:
            from divineos.core.semantic_search_rerank import rerank as rerank_fn

            hits = rerank_fn(text, hits, top_k=top)
        else:
            hits = hits[:top]
        click.echo(f'=== {len(hits)} hits for "{text}" ===')
        click.echo("")
        for h in hits:
            rel_path = h.source_path
            try:
                rel_path = str(Path(h.source_path).relative_to(Path.cwd()))
            except ValueError:
                pass
            # When reranked, show the rerank score primary and the
            # original similarity in parens for context. Without rerank,
            # just show similarity as before.
            if h.rerank_score is not None:
                score_str = f"[r={h.rerank_score:+.3f} s={h.similarity:.3f}]"
            else:
                score_str = f"[{h.similarity:.3f}]"
            click.echo(f"  {score_str} {rel_path}:{h.paragraph_index}")
            preview = h.text[:200].replace("\n", " ")
            if len(h.text) > 200:
                preview += "..."
            click.echo(f"    {preview}")
            click.echo("")

    @search_group.command("index")
    @click.option(
        "--corpus",
        type=click.Choice(["exploration", "letters", "all"]),
        default="exploration",
        help="Which corpus to index (default: exploration)",
    )
    @click.option(
        "--force",
        is_flag=True,
        default=False,
        help="Re-embed everything, even chunks already at the current model version",
    )
    def search_index_cmd(corpus: str, force: bool) -> None:
        """Chunk + embed + store paragraphs from the chosen corpus."""
        paths = _gather_paths(corpus)
        if not paths:
            click.echo(f"(no files found for corpus={corpus})")
            return
        click.echo(f"Indexing {len(paths)} file(s) from corpus={corpus} into {_db_path()}...")
        counts = semantic_search.index_corpus(paths, _db_path(), force_reindex=force)
        click.echo(
            f"  files: {counts['files_processed']}  "
            f"chunks seen: {counts['chunks_seen']}  "
            f"indexed: {counts['chunks_indexed']}  "
            f"skipped (already current): {counts['chunks_skipped']}"
        )

    @search_group.command("stats")
    def search_stats_cmd() -> None:
        """Show what's currently in the search index."""
        import sqlite3

        db_path = _db_path()
        if not Path(db_path).exists():
            click.echo("(no index yet — run: divineos find index)")
            return
        with sqlite3.connect(db_path) as conn:
            try:
                total = conn.execute("SELECT COUNT(*) FROM semantic_search_chunks").fetchone()[0]
            except sqlite3.OperationalError:
                click.echo("(no index yet — run: divineos find index)")
                return
            by_source = conn.execute(
                "SELECT source_path, COUNT(*) FROM semantic_search_chunks "
                "GROUP BY source_path ORDER BY COUNT(*) DESC LIMIT 10"
            ).fetchall()
            by_model = conn.execute(
                "SELECT embedding_model, COUNT(*) FROM semantic_search_chunks "
                "GROUP BY embedding_model"
            ).fetchall()
        click.echo(f"=== semantic search index ({db_path}) ===")
        click.echo(f"  total chunks: {total}")
        click.echo("")
        click.echo("  by embedding model:")
        for model, n in by_model:
            click.echo(f"    {model}: {n}")
        click.echo("")
        click.echo("  top sources by chunk count:")
        for src, n in by_source:
            rel = src
            try:
                rel = str(Path(src).relative_to(Path.cwd()))
            except ValueError:
                pass
            click.echo(f"    {n:>4}  {rel}")


def _gather_paths(corpus: str) -> list[str]:
    """Resolve the corpus selector to a list of file paths."""
    repo_root = Path.cwd()
    paths: list[str] = []
    if corpus in ("exploration", "all"):
        expl_dir = repo_root / "exploration" / "aether"
        if expl_dir.exists():
            paths.extend(str(p) for p in expl_dir.glob("*.md"))
    if corpus in ("letters", "all"):
        letters_dir = repo_root / "family" / "letters"
        if letters_dir.exists():
            paths.extend(str(p) for p in letters_dir.glob("*.md"))
    return sorted(paths)
