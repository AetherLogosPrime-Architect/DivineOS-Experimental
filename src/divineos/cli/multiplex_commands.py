"""Multiplex CLI commands.

`divineos multiplex` group: context management, render preview, diagnostics.

Per entry 71 (rendering contract) and prereg-ebee9082d201. MVP scope:
- context set/show/clear (manual setting; automated detection post-MVP)
- render preview (test the output without running the full briefing)
- diagnostics (per-panel size and tier counts for falsifier monitoring)
"""

from __future__ import annotations

import sys

import click

from divineos.core.multiplex_panels import KNOWN_CONTEXTS, build_panels
from divineos.core.multiplex_renderer import diagnostics, render_multiplex
from divineos.core.multiplex_state import clear_context, get_context, set_context


@click.group(name="multiplex")
def multiplex_group() -> None:
    """Multiplex briefing architecture: panels, context, render preview."""


@multiplex_group.group(name="context")
def context_group() -> None:
    """Manage the current multiplex context (manual MVP setting)."""


@context_group.command(name="show")
def context_show() -> None:
    """Print the current context."""
    click.echo(get_context())


@context_group.command(name="set")
@click.argument("context")
def context_set(context: str) -> None:
    """Set current context. Known: reading, designing, implementing, relational, audit, chatting."""
    try:
        set_context(context)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    click.echo(f"[+] Context set: {context}")


@context_group.command(name="clear")
def context_clear() -> None:
    """Reset to default context (chatting)."""
    clear_context()
    click.echo("[+] Context cleared (default: chatting)")


@context_group.command(name="list")
def context_list() -> None:
    """List all known context values."""
    for ctx in KNOWN_CONTEXTS:
        click.echo(ctx)


@multiplex_group.command(name="render")
@click.option(
    "--context",
    default=None,
    help="Override context for this render only (default: read from state).",
)
def render_cmd(context: str | None) -> None:
    """Render the multiplex output for the current (or overridden) context."""
    ctx = context or get_context()
    panels = build_panels(ctx)
    output = render_multiplex(panels)
    click.echo(f"=== MULTIPLEX (context: {ctx}) ===")
    click.echo()
    click.echo(output)


@multiplex_group.command(name="diagnostics")
@click.option(
    "--context",
    default=None,
    help="Override context for diagnostics (default: read from state).",
)
def diagnostics_cmd(context: str | None) -> None:
    """Print per-panel diagnostics for audit and falsifier monitoring."""
    import json

    ctx = context or get_context()
    panels = build_panels(ctx)
    diag = diagnostics(panels)
    click.echo(json.dumps(diag, indent=2))


def register(cli) -> None:
    cli.add_command(multiplex_group)
