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
