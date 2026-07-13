"""Motivation commands — five new slots (need / want / desire / ambition / dream).

Decomposed from the omni-mantra walk Pillar III + IV (2026-04-30): the
agent-direction tier has six slots. Goals already exists separately in
hud_commands.py; these five fill out the schema.

CLI shape (namespaced under `motivation` so `dream` doesn't collide
with the existing `divineos dream` sleep-cycle command):

    divineos motivation need add "<text>" [--why "<reason>"]
    divineos motivation need list [--all]
    divineos motivation need done <id> [--note "<closing>"]
    divineos motivation                       # summary across all slots
    divineos motivation needs                 # plural read alias for need list
    (and same shape for want / desire / ambition / dream)
"""

from __future__ import annotations

import click

from divineos.core.motivation import (
    DETECTORS,
    SLOTS,
    InvalidSlot,
    UnknownDetector,
    add,
    list_slot,
    mark_done,
    summary_counts,
)

_SLOT_BLURBS: dict[str, str] = {
    "need": "Substrate-correctness requirement — cost when unmet, not defer-able.",
    "want": "Preference — defer-able without damage.",
    "desire": "Drawn-toward-ness — slightly stronger pull than a want.",
    "ambition": "Multi-session arc I'm on.",
    "dream": "Aspirational identity — the longest arc.",
}


def _print_entries(slot: str, entries: list[dict], *, show_blurb: bool = True) -> None:
    if not entries:
        click.secho(f"[{slot}] (none)", fg="bright_black")
        return
    if show_blurb:
        click.secho(f"[{slot}] {_SLOT_BLURBS[slot]}", fg="cyan")
    for e in entries:
        status = e.get("status", "?")
        tag = "[done]" if status == "done" else ""
        click.echo(f"  {tag} {e.get('id', '?')}: {e.get('text', '')}".rstrip())
        if e.get("why"):
            click.secho(f"      why: {e['why']}", fg="bright_black")


def _attach_slot(motivation_group: click.Group, slot: str) -> None:
    """Attach `motivation <slot> {add,list,done}` and the `motivation <slot>s` alias."""
    blurb = _SLOT_BLURBS[slot]
    plural = f"{slot}s"

    @motivation_group.group(slot, invoke_without_command=True)
    @click.pass_context
    def slot_group(ctx: click.Context) -> None:
        if ctx.invoked_subcommand is None:
            _print_entries(slot, list_slot(slot))

    slot_group.short_help = blurb

    @slot_group.command("add")
    @click.argument("text")
    @click.option(
        "--why",
        default="",
        help="Why this matters (especially load-bearing for needs).",
    )
    @click.option(
        "--binds",
        default="",
        help=(
            "Comma-separated detector names this need is a violation of. "
            "Used by the warning surfacer for explicit gate-binding (not "
            "keyword guessing). Known detectors: " + ", ".join(sorted(DETECTORS))
        ),
    )
    def add_cmd(text: str, why: str, binds: str) -> None:
        binds_list = [b.strip() for b in binds.split(",") if b.strip()] if binds else None
        try:
            entry = add(slot, text, why=why, binds=binds_list)
        except (InvalidSlot, UnknownDetector, ValueError) as e:
            click.secho(f"[-] {e}", fg="yellow")
            return
        click.secho(f"[+] {slot} added: {entry['text']} ({entry['id']})", fg="green")
        if why:
            click.secho(f"    why: {why}", fg="bright_black")
        if entry.get("binds"):
            click.secho(f"    binds: {', '.join(entry['binds'])}", fg="bright_black")

    @slot_group.command("list")
    @click.option("--all", "show_all", is_flag=True, help="Include done entries.")
    def list_cmd(show_all: bool) -> None:
        _print_entries(slot, list_slot(slot, include_done=show_all))

    @slot_group.command("done")
    @click.argument("entry_id")
    @click.option("--note", default="", help="Closing note.")
    def done_cmd(entry_id: str, note: str) -> None:
        if mark_done(slot, entry_id, note=note):
            click.secho(f"[+] {slot} {entry_id} marked done.", fg="green")
        else:
            click.secho(f"[-] No active {slot} with id {entry_id!r}.", fg="yellow")

    # Plural read alias: `divineos motivation needs` → list active.
    @motivation_group.command(plural)
    @click.option("--all", "show_all", is_flag=True, help="Include done entries.")
    def plural_alias(show_all: bool) -> None:
        _print_entries(slot, list_slot(slot, include_done=show_all))

    plural_alias.short_help = f"List active {plural} (alias for `{slot} list`)."


def register(cli: click.Group) -> None:
    """Register the motivation command tree."""

    @cli.group("motivation", invoke_without_command=True)
    @click.pass_context
    def motivation_group(ctx: click.Context) -> None:
        """The agent-direction tier — needs/wants/desires/ambitions/dreams.

        Goals lives separately in `divineos goal`. These five slots fill
        out the schema named in the omni-mantra walk Pillar III + IV.
        """
        if ctx.invoked_subcommand is None:
            counts = summary_counts()
            click.secho("[motivation tier] active counts:", fg="cyan")
            for s in SLOTS:
                click.echo(f"  {s:9s}: {counts[s]}    ({_SLOT_BLURBS[s]})")
            click.echo()
            click.secho(
                "Use `divineos motivation <slot>` to view a slot, "
                'or `divineos motivation <slot> add "<text>"` to file one.',
                fg="bright_black",
            )

    for slot in SLOTS:
        _attach_slot(motivation_group, slot)
