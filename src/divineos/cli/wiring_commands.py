"""Wiring dark-node CLI — the standing check Aletheia asked for.

`divineos wiring dark` — show the current dark set (things nothing else calls
or imports) and update the persisted state so the briefing knows what "new"
means next time.

Powered by `divineos.core.wiring_dark`. See that module for design intent.
"""

from __future__ import annotations

import time

import click

from divineos.core.wiring_dark import (
    DEFAULT_GRAPH_PATH,
    DEFAULT_STATE_PATH,
    diff_against_state,
    find_dark,
    load_graph,
    load_state,
    save_state,
)


@click.group(name="wiring")
def wiring_group() -> None:
    """Wiring checks — is what I built actually called by anything?"""


@wiring_group.command(name="dark")
@click.option(
    "--limit",
    default=50,
    help="Cap the display list. Full set still persists to state file.",
)
@click.option(
    "--no-save",
    is_flag=True,
    help="Print without updating the last-seen state (dry-run).",
)
@click.option(
    "--deep",
    is_flag=True,
    help=(
        "Include function-level dark nodes (default: module-level only). "
        "Deep mode has ~4000 false-positives on this codebase because AST "
        "can't resolve dynamic dispatch (click/pytest/plugins). Use for "
        "focused audit passes, not routine checks."
    ),
)
def wiring_dark(limit: int, no_save: bool, deep: bool) -> None:
    """Show every node in the code graph that nothing else calls or imports.

    A node with in-degree zero is capability with no consumer. Same shape as
    Aletheia's F1/F2/F3/F5 findings and AST-1 — built-but-not-wired. This
    query returns them structurally instead of grepping for them by hand.

    Exclusions: test files, __init__.py entries, synthetic symbols. Iterate
    the exclusion list in wiring_dark.py as false-positives surface.
    """
    if not DEFAULT_GRAPH_PATH.exists():
        click.echo(
            f"No code graph at {DEFAULT_GRAPH_PATH}. Rebuild: /graphify src",
            err=True,
        )
        raise click.exceptions.Exit(2)

    graph = load_graph(DEFAULT_GRAPH_PATH)
    result = find_dark(graph, modules_only=not deep)
    state = load_state(DEFAULT_STATE_PATH)
    new_nodes, lightened = diff_against_state(result.dark, state)

    click.echo(
        f"Graph: {result.total_nodes} nodes / {result.total_edges} edges. "
        f"Dark: {len(result.dark)} (excluded {result.excluded_count} by rules)."
    )
    if state.get("last_scan_at"):
        click.echo(
            f"Since last review: {len(new_nodes)} newly dark, {len(lightened)} returned to light."
        )
    else:
        click.echo("First scan — no prior state to diff against.")

    if new_nodes:
        click.echo("")
        click.echo(f"=== Newly dark ({len(new_nodes)}) ===")
        for node in new_nodes[:limit]:
            click.echo(f"  {node.label}")
            click.echo(f"    file: {node.source_file}")
        if len(new_nodes) > limit:
            click.echo(f"  ... and {len(new_nodes) - limit} more.")

    if lightened:
        click.echo("")
        click.echo(f"=== Returned to light ({len(lightened)}) ===")
        for lid in lightened[:limit]:
            click.echo(f"  {lid}")
        if len(lightened) > limit:
            click.echo(f"  ... and {len(lightened) - limit} more.")

    if not new_nodes and not lightened and state.get("last_scan_at"):
        click.echo("")
        click.echo("Nothing changed since last review.")

    if not no_save:
        new_state = {
            "last_scan_at": time.time(),
            "dark_ids": sorted(n.id for n in result.dark),
        }
        save_state(new_state, DEFAULT_STATE_PATH)
        click.echo("")
        click.echo(f"State updated: {DEFAULT_STATE_PATH}")


def register(cli: click.Group) -> None:
    """Register the wiring command group with the main CLI."""
    cli.add_command(wiring_group)
