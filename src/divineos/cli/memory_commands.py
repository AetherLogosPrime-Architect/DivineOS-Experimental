"""Memory commands — core, recall, active, remember, refresh."""

import click

from divineos.cli._helpers import _log_os_query, _resolve_knowledge_id, _safe_echo
from divineos.cli._wrappers import (
    _wrapped_clear_core,
    _wrapped_format_core,
    _wrapped_format_recall,
    _wrapped_get_active_memory,
    _wrapped_promote_to_active,
    _wrapped_recall,
    _wrapped_refresh_active_memory,
    _wrapped_set_core,
)
from divineos.core.memory import CORE_SLOTS, init_memory_tables
import sqlite3

_MC_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def register(cli: click.Group) -> None:
    """Register all memory commands on the CLI group."""

    @cli.command("core")
    @click.argument("action", required=False, default="show")
    @click.argument("slot", required=False)
    @click.argument("content", required=False)
    def core_cmd(action: str, slot: str | None, content: str | None) -> None:
        r"""Manage core memory slots.

        \b
        Usage:
          divineos core              Show all core memory
          divineos core set SLOT "text"  Set a slot
          divineos core clear SLOT   Clear a slot
          divineos core slots        List available slot names
        """
        init_memory_tables()

        if action == "show":
            text = _wrapped_format_core()
            if text:
                _safe_echo(text)
            else:
                click.secho("[-] No core memory set yet.", fg="yellow")
                click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

        elif action == "slots":
            click.secho("\n=== Core Memory Slots ===\n", fg="cyan", bold=True)
            for s in CORE_SLOTS:
                click.echo(f"  {s}")
            click.echo()

        elif action == "set":
            if not slot or not content:
                click.secho('[-] Usage: divineos core set <slot> "<content>"', fg="red")
                return
            try:
                _wrapped_set_core(slot, content)
                click.secho(f"[+] Core memory '{slot}' updated.", fg="green")
            except ValueError as e:
                click.secho(f"[-] {e}", fg="red")
                click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

        elif action == "clear":
            if not slot:
                click.secho("[-] Usage: divineos core clear <slot>", fg="red")
                return
            try:
                if _wrapped_clear_core(slot):
                    click.secho(f"[+] Cleared '{slot}'.", fg="green")
                else:
                    click.secho(f"[*] '{slot}' was already empty.", fg="yellow")
            except ValueError as e:
                click.secho(f"[-] {e}", fg="red")
                click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

        else:
            click.secho(f"[-] Unknown action '{action}'. Use: show, set, clear, slots", fg="red")

    @cli.command("recall")
    @click.option("--topic", default="", help="Topic hint to boost relevant memories")
    def recall_cmd(topic: str) -> None:
        """Show what the AI remembers right now — core + active + relevant."""
        _log_os_query("recall", topic or "general recall")
        init_memory_tables()
        result = _wrapped_recall(context_hint=topic)
        text = _wrapped_format_recall(result)
        _safe_echo(text)

        # Proactive pattern warnings based on current topic
        if topic:
            try:
                from divineos.core.anticipation import anticipate, format_anticipation

                warnings = anticipate(topic)
                if warnings:
                    click.echo()
                    _safe_echo(format_anticipation(warnings))
            except _MC_ERRORS:
                pass  # anticipation is best-effort

    @cli.command("active")
    def active_cmd() -> None:
        """List active memory ranked by importance."""
        init_memory_tables()
        items = _wrapped_get_active_memory()

        if not items:
            click.secho("[-] No active memory yet.", fg="yellow")
            click.secho(
                "    Run 'divineos refresh' to auto-build from knowledge store.",
                fg="bright_black",
            )
            return

        click.secho(f"\n=== Active Memory ({len(items)} items) ===\n", fg="cyan", bold=True)
        for item in items:
            pin = click.style(" [pinned]", fg="yellow") if item["pinned"] else ""
            color = {
                "BOUNDARY": "red",
                "PRINCIPLE": "yellow",
                "DIRECTION": "green",
                "PROCEDURE": "cyan",
                "FACT": "blue",
                "OBSERVATION": "bright_black",
                "EPISODE": "cyan",
                "MISTAKE": "red",
                "PATTERN": "magenta",
                "PREFERENCE": "green",
            }.get(item["knowledge_type"], "white")
            click.secho(f"  [{item['importance']:.2f}] ", fg="bright_black", nl=False)
            click.secho(f"{item['knowledge_type']} ", fg=color, bold=True, nl=False)
            _safe_echo(f"{item['content'][:100]}{pin}")
            click.secho(
                f"         reason: {item['reason']} | surfaced: {item['surface_count']}x",
                fg="bright_black",
            )
            click.echo()

    @cli.command("remember")
    @click.argument("knowledge_id")
    @click.option("--reason", default="manually promoted", help="Why this is important")
    @click.option("--pin", is_flag=True, help="Pin this memory (cannot be auto-demoted)")
    def remember_cmd(knowledge_id: str, reason: str, pin: bool) -> None:
        """Promote a knowledge entry to active memory."""
        init_memory_tables()
        try:
            full_id = _resolve_knowledge_id(knowledge_id)
            mid = _wrapped_promote_to_active(full_id, reason=reason, pinned=pin)
            pin_note = " [pinned]" if pin else ""
            click.secho(f"[+] Promoted to active memory: {mid}{pin_note}", fg="green")
        except click.ClickException:
            raise
        except _MC_ERRORS as e:
            click.secho(f"[-] {e}", fg="red")

    @cli.command("refresh")
    @click.option("--threshold", default=0.3, type=float, help="Importance threshold (0.0-1.0)")
    def refresh_cmd(threshold: float) -> None:
        """Auto-rebuild active memory from the knowledge store."""
        if not 0.0 <= threshold <= 1.0:
            click.secho(f"[-] Threshold must be between 0.0 and 1.0, got {threshold}", fg="red")
            return
        init_memory_tables()
        result = _wrapped_refresh_active_memory(importance_threshold=threshold)
        click.secho("\n=== Memory Refresh ===\n", fg="cyan", bold=True)
        click.secho(
            f"  Promoted:  {result['promoted']}",
            fg="green" if result["promoted"] else "bright_black",
        )
        click.secho(f"  Kept:      {result['kept']}", fg="white")
        click.secho(
            f"  Demoted:   {result['demoted']}",
            fg="red" if result["demoted"] else "bright_black",
        )
        total = result["promoted"] + result["kept"]
        click.secho(f"\n  Active memory: {total} items", fg="white", bold=True)
        click.echo()
