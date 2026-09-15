"""The hook layer, computed on demand.

Andrew 2026-09-08: *"i dont want an OS made of external hooks through the IDE,
the hooks should just be pointing to the logic in the OS itself."*

One subcommand, and it only measures. An earlier version of this file also
carried a ratchet that refused to let the layer grow; he rejected the idea
itself — *"why would you build something that can only shrink and never
grow?"* — and it came out the same day. The reasoning lives in
``divineos.core.hook_layer``.

Every number is computed from the settings file and the hooks directory at the
moment of asking, because the hand-maintained migration tracker was measured
stale in both directions: it listed a hook as thinned while that hook was
simultaneously unregistered and already migrated.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    """Register the hook-layer command group."""

    @cli.group("hook-layer")
    def hook_layer_group() -> None:
        """What the hook layer actually is, measured rather than remembered."""

    @hook_layer_group.command("show")
    def show_cmd() -> None:
        """Counts, doors, duplicates, and how much shell carries judgment."""
        from divineos.core.hook_layer import format_inventory, inventory

        click.echo(format_inventory(inventory(".")))

    @hook_layer_group.command("doorbells")
    @click.option("--write", "do_write", is_flag=True, help="Regenerate the bells on disk.")
    def doorbells_cmd(do_write: bool) -> None:
        """Check every bell against the generator, or rewrite them.

        The bells are generated so that nobody authors one — Aria 2026-09-08:
        *"You cannot put a brain in a file you did not author."* So the check
        is byte equality against what the generator produces, which is
        exhaustive, rather than an opinion about what a bell should look like.
        """
        from divineos.core.doorbell_generator import active_events, main, write_all

        if do_write:
            changed = write_all(".")
            for path in changed:
                click.secho(f"[doorbells] wrote {path}", fg="green")
            if not changed:
                click.echo("[doorbells] already current.")
            click.echo(f"  doors with surfaces behind them: {', '.join(active_events())}")
            return
        if main(".") != 0:
            raise click.exceptions.Exit(1)
        click.secho("[doorbells] ok — every bell is what the generator produces.")
