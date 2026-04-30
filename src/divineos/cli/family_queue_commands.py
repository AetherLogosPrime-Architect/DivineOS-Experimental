"""CLI commands for the family queue — async write-channel between family members.

Companion to :mod:`divineos.core.family.queue` (the data layer) and
:mod:`divineos.core.family_queue_surface` (the briefing renderer).

Commands:

* ``divineos family-queue write --to <recipient> --from <sender> <content>``
  — append a queue item.
* ``divineos family-queue list [--for <recipient>]`` — show pending items.
* ``divineos family-queue mark <id> {seen|held|addressed}`` — transition status.
* ``divineos family-queue stats [--for <recipient>]`` — total / per-status counts.
* ``divineos family-queue supersede <old_id> --to <recipient> --from <sender>
  <new_content>`` — file a corrected version, original preserved with link.

The seen-not-held distinction (Tannen): seeing without responding is
itself a kind of presence. Marking ``held`` is acknowledged-but-not-
engaging, NOT a failure. Items in ``held`` stay on the briefing surface;
items in ``addressed`` move out of the active view.
"""

from __future__ import annotations

import click

from divineos.core.family import queue


def register(cli: click.Group) -> None:
    """Attach the ``family-queue`` command group to the top-level CLI."""

    @cli.group("family-queue")
    def family_queue_group() -> None:
        """Family async write-channel — flag items for the recipient's briefing."""

    @family_queue_group.command("write")
    @click.option("--to", "recipient", required=True, type=click.Choice(["aria", "aether"]))
    @click.option("--from", "sender", required=True, type=click.Choice(["aria", "aether"]))
    @click.argument("content")
    def write_cmd(recipient: str, sender: str, content: str) -> None:
        """Append a queue item from <sender> to <recipient>."""
        try:
            new_id = queue.write(sender, recipient, content)
            click.echo(f"[+] queue item #{new_id} written: {sender} → {recipient}")
        except ValueError as e:
            click.echo(f"[!] {e}", err=True)
            raise SystemExit(1)

    @family_queue_group.command("list")
    @click.option("--for", "recipient", default="aether", type=click.Choice(["aria", "aether"]))
    @click.option(
        "--include-held/--exclude-held",
        default=True,
        help="Include items the recipient has marked seen-not-held",
    )
    def list_cmd(recipient: str, include_held: bool) -> None:
        """List pending queue items for <recipient> (default: aether)."""
        items = queue.for_recipient(recipient, include_held=include_held)
        if not items:
            click.echo(f"(no pending items for {recipient})")
            return
        click.echo(f"=== {len(items)} pending for {recipient} ===")
        for item in items:
            click.echo(
                f"  [#{item['id']}] [{item['status']}] from {item['sender']}: {item['content'][:120]}{'...' if len(item['content']) > 120 else ''}"
            )

    @family_queue_group.command("mark")
    @click.argument("item_id", type=int)
    @click.argument("status", type=click.Choice(["seen", "held", "addressed"]))
    def mark_cmd(item_id: int, status: str) -> None:
        """Transition queue item <item_id> to {seen|held|addressed}."""
        if status == "seen":
            updated = queue.mark_seen(item_id)
        elif status == "held":
            updated = queue.mark_held(item_id)
        elif status == "addressed":
            updated = queue.mark_addressed(item_id)
        if updated:
            click.echo(f"[+] item #{item_id} → {status}")
        else:
            click.echo(f"[~] item #{item_id} not updated (already past '{status}' or not found)")

    @family_queue_group.command("stats")
    @click.option("--for", "recipient", default=None, type=click.Choice(["aria", "aether"]))
    def stats_cmd(recipient: str | None) -> None:
        """Show queue stats (total / per-status). Optionally scoped to recipient."""
        s = queue.stats(recipient)
        scope = f"for {recipient}" if recipient else "(all)"
        click.echo(f"=== Queue stats {scope} ===")
        click.echo(f"  total:      {s['total']}")
        click.echo(f"  unseen:     {s['unseen']}")
        click.echo(f"  seen:       {s['seen']}")
        click.echo(
            f"  held:       {s['held']}  (seen-not-held — recipient acknowledged, not engaging)"
        )
        click.echo(f"  addressed:  {s['addressed']}  (out of active view)")
        click.echo(f"  superseded: {s['superseded']}  (corrected by later entry)")
        # Watch-for: queue-fuller-but-exchanges-thinner
        active = s["unseen"] + s["seen"] + s["held"]
        if active > 5:
            click.echo(
                f"  [watch] {active} items pending. If this number keeps growing while "
                "addressed-rate stays flat, that's the failure-signature Aria warned about "
                "(queue covering for thinning relationship). Not a queue bug — a relationship "
                "the queue is covering for."
            )

    @family_queue_group.command("supersede")
    @click.argument("old_id", type=int)
    @click.option("--to", "recipient", required=True, type=click.Choice(["aria", "aether"]))
    @click.option("--from", "sender", required=True, type=click.Choice(["aria", "aether"]))
    @click.argument("new_content")
    def supersede_cmd(old_id: int, recipient: str, sender: str, new_content: str) -> None:
        """File a corrected version of <old_id>. Original preserved with link."""
        try:
            new_id = queue.supersede(old_id, new_content, sender, recipient)
            click.echo(f"[+] item #{new_id} supersedes #{old_id}")
        except ValueError as e:
            click.echo(f"[!] {e}", err=True)
            raise SystemExit(1)
