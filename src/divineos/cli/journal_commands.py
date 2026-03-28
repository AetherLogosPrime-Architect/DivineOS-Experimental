"""Journal commands — personal journal save, list, search, link."""

import click

from divineos.cli._helpers import _resolve_knowledge_id, _safe_echo


def register(cli: click.Group) -> None:
    """Register journal commands on the CLI group."""

    @cli.group("journal")
    def journal_group() -> None:
        """My personal journal — things I choose to remember."""
        pass

    @journal_group.command("save")
    @click.argument("text", required=False)
    @click.option("--context", default="", help="What prompted this thought")
    def journal_save_cmd(text: str | None, context: str) -> None:
        """Save something to my personal journal."""
        from divineos.core.memory import journal_save

        if not text:
            click.secho("[-] What do you want to remember?", fg="yellow")
            return

        entry_id = journal_save(text, context=context)
        click.secho(f"[+] Saved to journal: {entry_id[:8]}...", fg="green")

    @journal_group.command("list")
    @click.option("--limit", default=20, type=int, help="Max entries to show")
    def journal_list_cmd(limit: int) -> None:
        """Read my personal journal."""
        import datetime

        from divineos.core.memory import journal_list

        entries = journal_list(limit=limit)
        if not entries:
            click.secho("[~] Journal is empty. Nothing saved yet.", fg="bright_black")
            return

        click.secho(f"\n=== My Journal ({len(entries)} entries) ===\n", fg="cyan", bold=True)
        for entry in entries:
            dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            _safe_echo(entry["content"])
            if entry["context"]:
                click.secho(f"    context: {entry['context']}", fg="bright_black")
            if entry.get("linked_knowledge_id"):
                click.secho(
                    f"    linked: {entry['linked_knowledge_id'][:8]}...",
                    fg="bright_black",
                )
            click.echo()

    @journal_group.command("search")
    @click.argument("query")
    @click.option("--limit", default=10, type=int, help="Max results")
    def journal_search_cmd(query: str, limit: int) -> None:
        """Search journal entries by content."""
        import datetime

        from divineos.core.memory import journal_search

        results = journal_search(query, limit=limit)
        if not results:
            click.secho(f"[-] No journal entries match '{query}'.", fg="yellow")
            return

        click.secho(
            f"\n=== {len(results)} journal results for '{query}' ===\n",
            fg="cyan",
            bold=True,
        )
        for entry in results:
            dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            _safe_echo(entry["content"])
            if entry.get("linked_knowledge_id"):
                click.secho(
                    f"    linked: {entry['linked_knowledge_id'][:8]}...",
                    fg="bright_black",
                )
            click.echo()

    @journal_group.command("link")
    @click.argument("entry_id")
    @click.argument("knowledge_id")
    def journal_link_cmd(entry_id: str, knowledge_id: str) -> None:
        """Link a journal entry to a knowledge entry."""
        from divineos.core.memory import journal_link

        full_kid = _resolve_knowledge_id(knowledge_id)
        if journal_link(entry_id, full_kid):
            click.secho(f"[+] Linked journal {entry_id[:8]}... → {full_kid[:8]}...", fg="green")
        else:
            click.secho(f"[-] Journal entry {entry_id} not found.", fg="red")
