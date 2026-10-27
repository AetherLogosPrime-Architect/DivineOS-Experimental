"""CLI: divineos linkage -- the memory link's vector drawer.

    divineos linkage warm     fill the drawer for every item the link can surface
    divineos linkage status   how full the drawer is, and whether the link can run

The memory link reads item vectors from the drawer and never computes them at
reply time (core/vector_drawer.py). When it reports items with no stored vector,
this is the command it names.
"""

from __future__ import annotations

import click


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
        # Nonzero means a row on his grief shelf has no stored vector, so the moment lane checks
        # it for the same words but cannot check it for nearness until `linkage warm` is run.
        click.echo(
            f"grief-shelf rows with no stored vector (nearness not checked at load): "
            f"{state.get('held_unvectored', 0)}"
        )
        # The second line's pain signal: nonzero means somebody tried to mark something that reads
        # as loss. Never the words, only the count (walk-5fa33c17ed13).
        click.echo(
            f"moment marks refused by the grief guard: {memory_linkage_retriever.second_line_refusals()}"
        )

    @linkage_group.command("mark-moment")
    @click.argument("moment_id")
    def mark_moment_cmd(moment_id: str) -> None:
        """Let the memory link bring a saved moment back (runs the grief guards once, here)."""
        from divineos.core import memory_linkage_retriever

        out = memory_linkage_retriever.mark_moment(moment_id)
        if not out.ok:
            raise click.ClickException(f"not marked: {out.reason}")
        click.secho(f"[+] {moment_id} marked", fg="green")

    @linkage_group.command("unmark-moment")
    @click.argument("moment_id")
    def unmark_moment_cmd(moment_id: str) -> None:
        """Stop the memory link bringing a moment back, at once."""
        from divineos.core import memory_linkage_retriever

        if not memory_linkage_retriever.unmark_moment(moment_id):
            raise click.ClickException(f"no such moment: {moment_id}")
        click.secho(f"[+] {moment_id} unmarked", fg="green")

    @linkage_group.group("moment-links")
    def moment_links_group() -> None:
        """Link a saved moment to the lessons of his it belongs to (per seat)."""

    def _seat() -> str:
        from pathlib import Path

        from divineos.core import his_lessons_shelf

        return his_lessons_shelf.seat(Path.cwd())

    @moment_links_group.command("propose")
    @click.argument("moment_id")
    def propose_cmd(moment_id: str) -> None:
        """Lessons of his this moment is near (top three at the shelf's floor), to confirm or drop."""
        from divineos.core import moment_links

        if not moment_links.is_marked(moment_id):
            click.echo(
                "this moment is not marked for the memory link (or does not exist), so nothing "
                f"was read or proposed. To bring it in on purpose: divineos linkage mark-moment {moment_id}"
            )
            return
        out = moment_links.propose(moment_id, _seat())
        if not out.proposed:
            click.echo(
                "no lesson of his reaches the shelf's floor for this moment: stored unlinked."
            )
        for p in out.proposed:
            click.echo(f"{p.link_id}  {p.score:.2f}  [{p.lesson.kind}] {p.lesson.words[:140]}")
        for s in out.skipped:
            click.echo(f"  skipped ({s.reason}) {s.score:.2f}  {s.line[:100]}")
        if out.proposed:
            click.echo("confirm or drop each: moment-links confirm <id> / decline <id>")

    @moment_links_group.command("confirm")
    @click.argument("link_id")
    def confirm_cmd(link_id: str) -> None:
        """Make a proposed link live: only a confirmed link is ever read."""
        from divineos.core import moment_links

        moment_links.confirm(link_id)
        click.echo(f"[+] {link_id} confirmed")

    @moment_links_group.command("decline")
    @click.argument("link_id")
    def decline_cmd(link_id: str) -> None:
        """Drop a proposed link; it is kept, and never offered again."""
        from divineos.core import moment_links

        moment_links.decline(link_id)
        click.echo(f"[+] {link_id} declined")

    @moment_links_group.command("orphans")
    def orphans_cmd() -> None:
        """Confirmed links whose lesson no longer resolves."""
        from divineos.core import moment_links

        n = moment_links.orphan_count(_seat())
        click.echo(
            f"{n} confirmed link(s) resolve to no lesson" + (" -- look at these" if n else "")
        )

    @linkage_group.command("why")
    @click.argument("words", nargs=-1, required=True)
    @click.option("--misses", default=4, show_default=True, help="Nearest items below the bar.")
    def why_cmd(words: tuple[str, ...], misses: int) -> None:
        """Show why items arrive for a turn: the scores each one was given.

        Pass the words of the turn. Read-only: nothing is primed, stored or fed back,
        so asking never changes what arrives next. It runs on exactly the words
        given, without the hidden recent context the live link adds, and a fresh run
        has no priming, so a match the live link reached through priming may show
        here as a plain miss. It shows numbers and the first line of the chunk that
        was compared, not a story about meaning.
        """
        from divineos.core import (
            light_embedder,
            memory_linkage_retriever,
            memory_linkage_retriever_v2,
        )

        ok, why = light_embedder.available()
        if not ok:
            raise click.ClickException(f"cannot run: {why}")
        memory_linkage_retriever._EMBEDDING_CACHE.clear()
        memory_linkage_retriever._ensure_cache()
        state = memory_linkage_retriever.lane_state()
        if state.get("drawer_error"):
            raise click.ClickException(f"the drawer could not be read: {state['drawer_error']}")
        sources = memory_linkage_retriever_v2.explain_turn(" ".join(words), None, misses)
        if not sources:
            raise click.ClickException("nothing was scored: no words, or no searchable items")
        for source in sources:
            click.echo(f"\n{source['source']}: {source['items']} items, bar {source['bar']:.2f}")
            for row in source["rows"]:  # type: ignore[attr-defined]
                mark = "SHOWN" if row["surfaced"] else ("cut " if row["passed"] else "miss")
                click.echo(
                    f"  {mark} sim {row['similarity']:.2f}  imp {row['importance']:.2f}  "
                    f"age {row['recency_days']}d  rank {row['rank']:.2f}  "
                    f"chunk {row['chunk_chars']} chars"
                )
                click.echo(f"       {row['title'][:90]}")
                click.echo(f"       > {row['first_line']}")
