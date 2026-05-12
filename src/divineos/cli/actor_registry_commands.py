"""Actor registry CLI commands — Phase 1 of actor-authenticity.

Exposes the core/actor_registry module via:

- ``divineos actor-registry init`` — create the registry file
- ``divineos actor-registry add <name> --kind <kind> [--notes "..."]`` — register an actor
- ``divineos actor-registry list`` — show all registered actors
- ``divineos actor-registry show <name>`` — show one actor's entry
- ``divineos actor-registry check <event-type> --actor <name>`` —
  preview the capability verdict for an (actor, event-type) pair

See exploration/45_actor_authenticity_design.md for the design rationale.

## Phase 1 scope reminder

This phase ships the registry + CLI + advisory capability lookups.
**No event-emission paths block yet** — unknown actors warn,
capability violations are surfaced as advisory verdicts. Phase 2 wires
the registry into event-emission gates after the design's seven open
questions are resolved.
"""

from __future__ import annotations

import click

from divineos.cli._helpers import _log_os_query


def register(cli: click.Group) -> None:
    """Register actor-registry commands on the CLI group."""

    @cli.group("actor-registry", invoke_without_command=True)
    @click.pass_context
    def actor_registry_group(ctx: click.Context) -> None:
        """Actor registry operations (Phase 1 of actor-authenticity).

        Records which actor names are recognized and what kind each is.
        Phase 1 is registry-only — no signing keys yet, no enforcement
        gates. Unknown actors trigger warnings, not failures.

        See exploration/45_actor_authenticity_design.md for the design.
        """
        if ctx.invoked_subcommand is None:
            click.secho(
                "actor-registry subcommands: init, add, list, show, check",
                fg="bright_black",
            )

    @actor_registry_group.command("init")
    @click.option(
        "--force",
        is_flag=True,
        default=False,
        help="Overwrite existing registry. Default refuses to wipe.",
    )
    def actor_registry_init_cmd(force: bool) -> None:
        """Create the registry file (if it does not exist).

        Idempotent by default — running on an existing registry is a
        no-op. Use --force to wipe and re-initialize.
        """
        from divineos.core.actor_registry import init_registry

        path = init_registry(force=force)
        click.secho(f"[+] Actor registry at {path}", fg="green")
        if force:
            click.secho(
                "  --force used; previous registry contents discarded.",
                fg="yellow",
            )
        _log_os_query("actor-registry", "init")

    @actor_registry_group.command("add")
    @click.argument("name")
    @click.option(
        "--kind",
        type=click.Choice(["agent", "audit-sibling", "operator", "external-vantage", "subagent"]),
        required=True,
        help="Actor kind. Determines capability defaults.",
    )
    @click.option(
        "--notes",
        default="",
        help="Free-text notes about this actor (purpose, scope, etc.).",
    )
    def actor_registry_add_cmd(name: str, kind: str, notes: str) -> None:
        """Register a new actor by name and kind.

        Phase 1: only records name + kind + metadata. No key material
        yet — that's Phase 2.
        """
        from divineos.core.actor_registry import add_actor

        try:
            actor = add_actor(name, kind, notes)
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            return

        click.secho(
            f"[+] Actor registered: {actor.name} (kind={actor.kind})",
            fg="green",
        )
        if actor.notes:
            click.secho(f"    notes: {actor.notes[:120]}", fg="bright_black")
        click.secho(
            "  [actor-registry-add] records identity-metadata — Phase 1 does not add "
            "key material; Phase 2 will. See exploration/45.",
            fg="bright_black",
        )
        _log_os_query("actor-registry", f"add {actor.kind}")

    @actor_registry_group.command("list")
    def actor_registry_list_cmd() -> None:
        """Show all registered actors."""
        from divineos.core.actor_registry import list_actors

        actors = list_actors()
        if not actors:
            click.secho(
                "(no actors registered yet — file one with `actor-registry add`)",
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Registered actors ({len(actors)}) ===\n",
            fg="cyan",
            bold=True,
        )
        for actor in actors:
            click.secho(f"  {actor.name}", fg="white", bold=True)
            click.secho(f"    kind: {actor.kind}", fg="bright_black")
            click.secho(f"    added: {actor.added_at}", fg="bright_black")
            if actor.notes:
                click.secho(f"    notes: {actor.notes[:120]}", fg="bright_black")
            if actor.public_key:
                click.secho(
                    f"    key: {actor.key_fingerprint or '(set)'}",
                    fg="bright_black",
                )
            click.echo()

    @actor_registry_group.command("show")
    @click.argument("name")
    def actor_registry_show_cmd(name: str) -> None:
        """Show one actor's registry entry."""
        from divineos.core.actor_registry import get_actor

        actor = get_actor(name)
        if not actor:
            click.secho(f"[!] no actor named '{name}' registered", fg="red")
            return

        click.secho(f"\n=== Actor: {actor.name} ===\n", fg="cyan", bold=True)
        click.secho(f"  kind: {actor.kind}", fg="white")
        click.secho(f"  added: {actor.added_at}", fg="white")
        if actor.notes:
            click.secho(f"  notes: {actor.notes}", fg="white")
        click.secho(
            f"  public_key: {actor.public_key or '(none — Phase 1)'}",
            fg="white",
        )
        if actor.key_fingerprint:
            click.secho(f"  fingerprint: {actor.key_fingerprint}", fg="white")
        if actor.valid_from or actor.valid_until:
            click.secho(
                f"  valid: {actor.valid_from or '*'} → {actor.valid_until or 'no expiry'}",
                fg="white",
            )

    @actor_registry_group.command("check")
    @click.argument("event_type")
    @click.option(
        "--actor",
        required=True,
        help="Actor name to check the capability verdict against.",
    )
    def actor_registry_check_cmd(event_type: str, actor: str) -> None:
        """Preview the capability verdict for (actor, event_type).

        Phase 1: this is advisory only — event-emission paths don't
        yet enforce the verdict. Useful for understanding what Phase 2
        will start blocking.
        """
        from divineos.core.actor_capabilities import Verdict, can_emit
        from divineos.core.actor_registry import get_actor

        registered = get_actor(actor)
        if not registered:
            click.secho(
                f"[!] actor '{actor}' is not registered — Phase 1 advisory: "
                f"this would trigger an unknown-actor warning",
                fg="yellow",
            )
            return

        verdict = can_emit(registered.kind, event_type)
        color = {
            Verdict.ALLOWED: "green",
            Verdict.RESTRICTED: "yellow",
            Verdict.DENIED: "red",
        }[verdict]
        click.secho(
            f"\n  Actor: {actor} (kind={registered.kind})",
            fg="white",
        )
        click.secho(f"  Event type: {event_type}", fg="white")
        click.secho(f"  Verdict: {verdict.value}", fg=color, bold=True)
        if verdict == Verdict.RESTRICTED:
            click.secho(
                "  Note: RESTRICTED means the emission is conditional — "
                "see actor_capabilities source for the conditions.",
                fg="bright_black",
            )
        elif verdict == Verdict.DENIED:
            click.secho(
                "  Phase 1 advisory: this emission would be DENIED under "
                "the capability model. Phase 2 will enforce; Phase 1 only "
                "warns. The behavioral discipline named in knowledge "
                "fec598d7 covers this case in the interim.",
                fg="bright_black",
            )
