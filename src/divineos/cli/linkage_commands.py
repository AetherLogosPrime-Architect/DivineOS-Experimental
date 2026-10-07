"""CLI: divineos linkage -- the memory link's vector drawer.

    divineos linkage warm     fill the drawer for every item the link can surface
    divineos linkage status   how full the drawer is, and whether the link can run

The memory link reads item vectors from the drawer and never computes them at
reply time (core/vector_drawer.py). When it reports items with no stored vector,
this is the command it names.
"""

from __future__ import annotations

import click


def _letter_index_status() -> None:
    """What the letter passage index holds, and whether it can be searched. The check
    is the one the compose path uses, so status cannot say fine where a turn would say
    it could not look."""
    import sqlite3

    import numpy as np

    from divineos.core import letter_passages

    _, problem = letter_passages.best_letters(np.ones(384, dtype=np.float32), k=1)
    if problem and "different vector size" not in problem:
        click.secho(f"letter index: CANNOT SEARCH: {problem}", fg="red")
        return
    conn = sqlite3.connect(f"file:{letter_passages.db_path().as_posix()}?mode=ro", uri=True)
    try:
        passages = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
        letters = conn.execute("SELECT COUNT(DISTINCT letter_id) FROM passages").fetchone()[0]
    finally:
        conn.close()
    click.echo(f"letter index: {letters} letters as {passages} passages")
    stale = letter_passages.staleness()
    if stale:
        click.secho(f"letter index: {stale}", fg="yellow")


def register(cli: click.Group) -> None:
    @cli.group("linkage", invoke_without_command=True)
    @click.pass_context
    def linkage_group(ctx: click.Context) -> None:
        """The memory link's vector drawer: fill it, and see how full it is."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @linkage_group.command("warm")
    def warm_cmd() -> None:
        """Compute and store a vector for every item that has none yet."""
        from divineos.core import memory_linkage_retriever, vector_drawer

        click.echo(f"drawer: {vector_drawer.drawer_path()}")

        def progress(done: int, total: int) -> None:
            click.echo(f"  {done}/{total}")

        out = memory_linkage_retriever.warm(progress)
        click.secho(
            f"[+] {out['computed']} computed, {out['already']} already stored, "
            f"{out['asked']} items in all.",
            fg="green",
        )
        click.secho(
            f"[+] letters: {out['letters']} indexed as {out['letter_passages']} passages.",
            fg="green" if out["letter_passages"] else "red",
        )

    @linkage_group.command("status")
    def status_cmd() -> None:
        """Whether the link can run here, and how many items it would search."""
        from divineos.core import light_embedder, memory_linkage_retriever, vector_drawer

        ok, why = light_embedder.available()
        click.echo(f"embedder: {'ok' if ok else 'CANNOT RUN: ' + why}")
        click.echo(f"drawer:   {vector_drawer.drawer_path()}")
        memory_linkage_retriever._EMBEDDING_CACHE.clear()
        memory_linkage_retriever._ensure_cache()
        counts = {k: len(v) for k, v in memory_linkage_retriever._EMBEDDING_CACHE.items()}
        state = memory_linkage_retriever.lane_state()
        click.echo(f"searchable items by source: {counts}")
        if state.get("drawer_error"):
            raise click.ClickException(f"the drawer could not be read: {state['drawer_error']}")
        click.echo(f"items with no stored vector: {state.get('missing', 0)}")
        _letter_index_status()
