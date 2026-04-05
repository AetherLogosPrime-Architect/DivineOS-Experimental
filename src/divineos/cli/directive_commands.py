"""Directive commands — create, list, edit sutra-style directive chains."""

import click

from divineos.cli._helpers import _log_os_query, _safe_echo
from divineos.cli._wrappers import _wrapped_store_knowledge
from divineos.core.knowledge import get_knowledge, search_knowledge


def register(cli: click.Group) -> None:
    """Register directive commands on the CLI group."""

    @cli.command("directive")
    @click.argument("name")
    @click.argument("links", nargs=-1, required=True)
    @click.option("--tags", default="", help="Comma-separated tags")
    def directive_cmd(name: str, links: tuple[str, ...], tags: str) -> None:
        """Create a sutra-style directive — a chain of precise statements.

        Each argument after the name is one link in the chain.
        Links constrain each other to lock meaning against drift.

        Example:
            divineos directive "ledger-integrity" \\
                "Events enter." \\
                "Events persist." \\
                "No event is altered." \\
                "No event is removed." \\
                "The hash binds content to identity."
        """
        chain_lines = [f"[{name}]"]
        for i, link in enumerate(links, 1):
            chain_lines.append(f"  {i}. {link}")
        chain_text = "\n".join(chain_lines)

        tag_list = ["directive", f"directive:{name}"]
        if tags:
            tag_list.extend(t.strip() for t in tags.split(",") if t.strip())

        existing = search_knowledge(name, limit=10)
        for entry in existing:
            if entry.get("knowledge_type") == "DIRECTIVE" and f"directive:{name}" in entry.get(
                "tags", ""
            ):
                from divineos.core.knowledge import supersede_knowledge

                supersede_knowledge(entry["knowledge_id"], f"Updated directive: {name}")
                click.secho(f"[~] Superseding previous version of '{name}'", fg="yellow")

        entry_id = _wrapped_store_knowledge(
            knowledge_type="DIRECTIVE",
            content=chain_text,
            confidence=1.0,
            source_events=[],
            tags=tag_list,
        )

        click.secho(f"\n[+] Directive '{name}' stored: {entry_id[:12]}...", fg="green")
        click.echo()
        _safe_echo(chain_text)
        click.echo()
        click.secho(
            f"    {len(links)} links in chain. Surfaces first in all briefings.",
            fg="bright_black",
        )

    @cli.command("directives")
    def directives_cmd() -> None:
        """List all active directives."""
        _log_os_query("directives", "list directives")
        entries = get_knowledge(knowledge_type="DIRECTIVE", limit=100)

        if not entries:
            click.secho("[*] No directives yet.", fg="yellow")
            click.secho(
                '    Create one: divineos directive "name" "link1" "link2" ...',
                fg="bright_black",
            )
            return

        click.secho(f"\n=== Directives ({len(entries)}) ===\n", fg="cyan", bold=True)
        for entry in entries:
            _safe_echo(entry["content"])
            click.secho(
                f"    id: {entry['knowledge_id'][:12]}  |  {entry['access_count']}x accessed",
                fg="bright_black",
            )
            click.echo()

    @cli.command("directive-edit")
    @click.argument("name")
    @click.argument("link_number", type=int)
    @click.argument("new_text")
    def directive_edit_cmd(name: str, link_number: int, new_text: str) -> None:
        """Edit a single link in a directive chain.

        Example:
            divineos directive-edit "ledger-integrity" 3 "No event is modified after storage."
        """
        entries = get_knowledge(knowledge_type="DIRECTIVE", limit=100)
        target = None
        for entry in entries:
            if f"directive:{name}" in entry.get("tags", []):
                target = entry
                break

        if not target:
            click.secho(f"[-] No directive named '{name}'", fg="red")
            return

        content_lines = target.get("content", "").splitlines()
        if not content_lines:
            click.secho(f"[-] Directive '{name}' has empty content — cannot edit.", fg="red")
            return
        header = content_lines[0]
        links = [line.strip() for line in content_lines[1:] if line.strip()]

        if not links or link_number < 1 or link_number > len(links):
            click.secho(f"[-] Link {link_number} out of range (1-{len(links)})", fg="red")
            return

        old_link = links[link_number - 1]
        old_text_display = old_link.split(". ", 1)[1] if ". " in old_link else old_link
        click.secho(f"  Old: {old_text_display}", fg="red")
        click.secho(f"  New: {new_text}", fg="green")

        links[link_number - 1] = f"{link_number}. {new_text}"
        new_content = header + "\n" + "\n".join(f"  {link}" for link in links)

        from divineos.core.knowledge import supersede_knowledge

        supersede_knowledge(target["knowledge_id"], f"Edited link {link_number}: {new_text[:50]}")

        tag_list = ["directive", f"directive:{name}"]
        entry_id = _wrapped_store_knowledge(
            knowledge_type="DIRECTIVE",
            content=new_content,
            confidence=1.0,
            source_events=[target["knowledge_id"]],
            tags=tag_list,
        )

        click.secho(f"\n[+] Directive '{name}' updated: {entry_id[:12]}...", fg="green")
        click.echo()
        _safe_echo(new_content)
        click.echo()
