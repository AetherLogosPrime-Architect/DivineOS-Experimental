"""Relationship commands — relate, related, unrelate knowledge entries."""

import click

from divineos.cli._helpers import _resolve_knowledge_id


def register(cli: click.Group) -> None:
    """Register relationship commands on the CLI group."""

    @cli.command("relate")
    @click.argument("source_id")
    @click.argument("relationship")
    @click.argument("target_id")
    @click.option("--notes", default="", help="Optional notes about this relationship")
    def relate_cmd(source_id: str, relationship: str, target_id: str, notes: str) -> None:
        """Create a typed relationship between two knowledge entries.

        Example: divineos relate abc123 SUPPORTS def456
        """
        from divineos.core.knowledge.relationships import RELATIONSHIP_TYPES, add_relationship

        relationship = relationship.upper()
        if relationship not in RELATIONSHIP_TYPES:
            click.secho(
                f"[-] Unknown relationship '{relationship}'. "
                f"Valid: {', '.join(sorted(RELATIONSHIP_TYPES))}",
                fg="red",
            )
            return

        try:
            full_source = _resolve_knowledge_id(source_id)
            full_target = _resolve_knowledge_id(target_id)
            add_relationship(full_source, full_target, relationship, notes=notes)
            click.secho(
                f"[+] {full_source[:8]}... {relationship} {full_target[:8]}...",
                fg="green",
            )
        except click.ClickException:
            raise
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    @cli.command("related")
    @click.argument("knowledge_id")
    @click.option("--depth", default=2, type=int, help="How many hops to traverse")
    def related_cmd(knowledge_id: str, depth: int) -> None:
        """Show relationships for a knowledge entry."""
        from divineos.core.knowledge.relationships import (
            find_related_cluster,
            get_relationships,
        )

        try:
            full_id = _resolve_knowledge_id(knowledge_id)
        except click.ClickException:
            raise

        rels = get_relationships(full_id)
        if not rels:
            click.secho(f"[-] No relationships for {full_id[:8]}...", fg="yellow")
            return

        click.secho(f"\n=== Relationships for {full_id[:8]}... ===\n", fg="cyan", bold=True)
        for rel in rels:
            if rel["direction"] == "outgoing":
                click.secho(
                    f"  → {rel['relationship']} → {rel['target_id'][:8]}...",
                    fg="white",
                )
            else:
                click.secho(
                    f"  ← {rel['relationship']} ← {rel['source_id'][:8]}...",
                    fg="white",
                )
            if rel["notes"]:
                click.secho(f"    ({rel['notes']})", fg="bright_black")

        if depth > 1:
            cluster = find_related_cluster(full_id, max_depth=depth)
            if len(cluster) > len(rels):
                click.secho(
                    f"\n  Cluster ({len(cluster)} entries within {depth} hops):",
                    fg="cyan",
                )
                for item in cluster:
                    click.secho(
                        f"    [{item['depth']}] {item['knowledge_id'][:8]}... "
                        f"via {item['relationship']}",
                        fg="bright_black",
                    )
        click.echo()

    @cli.command("unrelate")
    @click.argument("relationship_id")
    def unrelate_cmd(relationship_id: str) -> None:
        """Remove a relationship by its ID."""
        from divineos.core.knowledge.relationships import remove_relationship

        if remove_relationship(relationship_id):
            click.secho(f"[+] Removed relationship {relationship_id[:8]}...", fg="green")
        else:
            click.secho(f"[-] Relationship {relationship_id} not found.", fg="yellow")
