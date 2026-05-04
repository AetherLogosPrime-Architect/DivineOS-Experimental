"""Directive commands — create, list, edit sutra-style directive chains."""

import click

from divineos.cli._helpers import _log_os_query, _resolve_knowledge_id, _safe_echo
from divineos.cli._wrappers import _wrapped_store_knowledge
from divineos.core.knowledge import get_knowledge, search_knowledge
from divineos.core.knowledge.crud import set_integration_state


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
            click.secho(f"[-] Directive '{name}' has empty content -- cannot edit.", fg="red")
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

    @cli.command("integrate")
    @click.argument("knowledge_id")
    @click.option(
        "--notes",
        default=None,
        help="Why this is now internalized (e.g. 'consistent for 8 sessions, behavior is automatic')",
    )
    def integrate_cmd(knowledge_id: str, notes: str | None) -> None:
        """Mark a directive/preference as internalized.

        Internalized entries stay queryable but are suppressed from foreground briefing
        surfacing. Use this when a behavior has become consistent enough that
        re-surfacing it every session is noise rather than reinforcement.

        Example:
            divineos integrate db45c4b3 --notes "plain english is consistent practice now"
        """
        full_id = _resolve_knowledge_id(knowledge_id)
        result = set_integration_state(
            full_id,
            "internalized",
            marked_by="user",
            notes=notes,
        )
        click.secho(
            f"[+] {result['knowledge_type']} {full_id[:8]}: "
            f"{result['prior_state']} -> internalized",
            fg="green",
        )
        preview = result["content"][:120]
        click.secho(f"    {preview}", fg="bright_black")
        if notes:
            click.secho(f"    notes: {notes}", fg="bright_black")
        click.secho(
            "    No longer surfaces in briefing foreground. Still queryable via ask/recall.",
            fg="bright_black",
        )

    @cli.command("archive")
    @click.argument("knowledge_id")
    @click.option("--reason", default=None, help="Why this is being archived")
    def archive_cmd(knowledge_id: str, reason: str | None) -> None:
        """Mark a directive/preference as archived (retired but kept for record).

        Use this for directives that are no longer applicable (project-specific
        rules that no longer apply, deprecated practices, things you tried and
        don't want anymore). Distinct from supersede — archive doesn't claim
        replacement; it claims retirement.

        Example:
            divineos archive 388cb3bf --reason "stale question, not a directive"
        """
        full_id = _resolve_knowledge_id(knowledge_id)
        result = set_integration_state(
            full_id,
            "archived",
            marked_by="user",
            notes=reason,
        )
        click.secho(
            f"[+] {result['knowledge_type']} {full_id[:8]}: {result['prior_state']} -> archived",
            fg="yellow",
        )
        preview = result["content"][:120]
        click.secho(f"    {preview}", fg="bright_black")
        if reason:
            click.secho(f"    reason: {reason}", fg="bright_black")

    @cli.command("reactivate")
    @click.argument("knowledge_id")
    @click.option("--reason", default=None, help="Why this is being reactivated")
    def reactivate_cmd(knowledge_id: str, reason: str | None) -> None:
        """Restore an internalized or archived directive to active surfacing.

        Use this when a previously-internalized directive needs renewed attention
        (regression, change in practice, or you want it back in the foreground).

        Example:
            divineos reactivate 8dd6474f --reason "drifted on this, need to re-attend"
        """
        full_id = _resolve_knowledge_id(knowledge_id)
        result = set_integration_state(
            full_id,
            "active",
            marked_by="user",
            notes=reason,
        )
        click.secho(
            f"[+] {result['knowledge_type']} {full_id[:8]}: {result['prior_state']} -> active",
            fg="cyan",
        )
        preview = result["content"][:120]
        click.secho(f"    {preview}", fg="bright_black")
        if reason:
            click.secho(f"    reason: {reason}", fg="bright_black")

    @cli.command("integration-status")
    @click.option(
        "--state",
        type=click.Choice(["active", "internalized", "archived", "all"]),
        default="all",
        help="Filter by integration state",
    )
    @click.option(
        "--type",
        "ktype",
        default=None,
        help="Filter by knowledge type (DIRECTION, PREFERENCE, INSTRUCTION, etc.)",
    )
    def integration_status_cmd(state: str, ktype: str | None) -> None:
        """Show integration-state distribution across the knowledge store.

        Examples:
            divineos integration-status
            divineos integration-status --state internalized
            divineos integration-status --type DIRECTION
        """
        from divineos.core.knowledge._base import get_connection

        conn = get_connection()
        try:
            cur = conn.cursor()
            where = ["superseded_by IS NULL"]
            params: list[object] = []
            if state != "all":
                where.append("integration_state = ?")
                params.append(state)
            if ktype:
                where.append("knowledge_type = ?")
                params.append(ktype.upper())
            where_sql = " AND ".join(where)

            cur.execute(
                f"SELECT integration_state, knowledge_type, COUNT(*) FROM knowledge "
                f"WHERE {where_sql} GROUP BY integration_state, knowledge_type "
                f"ORDER BY integration_state, COUNT(*) DESC",
                params,
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            click.secho("[*] No matching entries.", fg="yellow")
            return

        click.secho("\n=== Integration State Distribution ===\n", fg="cyan", bold=True)
        current_state = None
        for st, kt, count in rows:
            if st != current_state:
                color = {"active": "green", "internalized": "cyan", "archived": "bright_black"}.get(
                    st, "white"
                )
                click.secho(f"\n[{st}]", fg=color, bold=True)
                current_state = st
            click.echo(f"  {kt:14s} {count:4d}")
