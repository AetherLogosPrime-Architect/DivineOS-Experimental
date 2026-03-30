"""HUD commands — hud, goal group, plan."""

import json
import sqlite3

import click

from divineos.cli._helpers import _safe_echo

_HC_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def register(cli: click.Group) -> None:
    """Register all HUD commands on the CLI group."""

    @cli.command("hud")
    @click.option("--save", is_flag=True, help="Save a HUD snapshot to disk")
    @click.option("--load", is_flag=True, help="Load the last saved HUD snapshot")
    @click.option(
        "--slots", default="", help="Comma-separated slot names to display (default: all)"
    )
    def hud_cmd(save: bool, load: bool, slots: str) -> None:
        """Display my heads-up display — everything I need to know at once."""
        from divineos.core.hud import build_hud, load_hud_snapshot, save_hud_snapshot

        if save:
            path = save_hud_snapshot()
            click.secho(f"[+] HUD snapshot saved to {path}", fg="green")
            return

        if load:
            snapshot = load_hud_snapshot()
            if snapshot:
                _safe_echo(snapshot)
            else:
                click.secho("[~] No saved HUD snapshot found.", fg="yellow")
            return

        slot_list = [s.strip() for s in slots.split(",") if s.strip()] if slots else None
        hud_text = build_hud(slots=slot_list)
        _safe_echo(hud_text)

    @cli.group("goal")
    def goal_group() -> None:
        """Track what the user asked me to do. My compass against drift."""

    @goal_group.command("add")
    @click.argument("text")
    @click.option("--original", default="", help="The user's exact words")
    def goal_add_cmd(text: str, original: str) -> None:
        """Add a new goal to track."""
        if not text.strip():
            click.secho("[-] Goal text cannot be empty.", fg="yellow")
            return
        from divineos.core.hud_state import add_goal

        add_goal(text, original_words=original)
        click.secho(f"[+] Goal added: {text}", fg="green")
        if original:
            click.secho(f'    (User\'s words: "{original}")', fg="bright_black")

    @goal_group.command("done")
    @click.argument("text")
    def goal_done_cmd(text: str) -> None:
        """Mark a goal as complete (matches partial text)."""
        if not text.strip():
            click.secho("[-] Please specify which goal to complete.", fg="yellow")
            return
        from divineos.core.hud_state import complete_goal

        if complete_goal(text):
            click.secho(f"[+] Goal completed: {text}", fg="green")
        else:
            click.secho(f"[~] No matching goal found for: {text}", fg="yellow")

    @goal_group.command("list")
    def goal_list_cmd() -> None:
        """Show current goals."""
        from divineos.core.hud import SLOT_BUILDERS

        _safe_echo(SLOT_BUILDERS["active_goals"]())

    @goal_group.command("clear")
    def goal_clear_cmd() -> None:
        """Remove completed goals from the list."""
        from divineos.core.hud import _ensure_hud_dir

        path = _ensure_hud_dir() / "active_goals.json"
        if not path.exists():
            click.secho("[~] No goals to clear.", fg="yellow")
            return

        try:
            goals = json.loads(path.read_text(encoding="utf-8"))
            active = [g for g in goals if g.get("status") != "done"]
            removed = len(goals) - len(active)
            path.write_text(json.dumps(active, indent=2), encoding="utf-8")
            click.secho(
                f"[+] Cleared {removed} completed goals, {len(active)} remain.",
                fg="green",
            )
        except _HC_ERRORS as e:
            click.secho(f"[!] Failed to clear goals: {e}", fg="red")

    @goal_group.command("reset")
    def goal_reset_cmd() -> None:
        """Remove ALL goals (completed and active). Use when goals are stale."""
        from divineos.core.hud import _ensure_hud_dir

        path = _ensure_hud_dir() / "active_goals.json"
        if not path.exists():
            click.secho("[~] No goals to reset.", fg="yellow")
            return

        try:
            goals = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            goals = []

        if not goals:
            click.secho("[~] No goals to reset.", fg="yellow")
            return

        click.secho(f"[!] This will remove all {len(goals)} goals.", fg="yellow")
        click.confirm("Proceed?", abort=True)
        path.write_text("[]", encoding="utf-8")
        click.secho(f"[+] Reset {len(goals)} goals.", fg="green")

    @cli.command("plan")
    @click.argument("goal")
    @click.option("--files", default=0, type=int, help="Estimated files to touch")
    @click.option("--time", "time_min", default=0, type=int, help="Estimated minutes")
    def plan_cmd(goal: str, files: int, time_min: int) -> None:
        """Set a session plan so clarity analysis can compare plan vs actual."""
        if not goal.strip():
            click.secho("[-] Plan goal cannot be empty.", fg="yellow")
            return
        from divineos.core.hud_state import set_session_plan

        set_session_plan(
            goal=goal,
            estimated_files=files,
            estimated_time_minutes=time_min,
        )
        click.secho(f"[+] Session plan set: {goal}", fg="green")
        if files:
            click.secho(f"    Estimated files: {files}", fg="bright_black")
        if time_min:
            click.secho(f"    Estimated time: {time_min}min", fg="bright_black")

    @cli.command("handoff")
    @click.argument("note", required=False)
    @click.option("--show", is_flag=True, help="Show current handoff note without clearing")
    @click.option("--clear", is_flag=True, help="Clear the handoff note")
    def handoff_cmd(note: str | None, show: bool, clear: bool) -> None:
        """View or write a handoff note for the next session.

        Without arguments, shows the current handoff note.
        With a NOTE argument, saves a manual handoff note.
        """
        from divineos.core.hud_handoff import (
            clear_handoff_note,
            load_handoff_note,
            save_handoff_note,
        )

        if clear:
            clear_handoff_note()
            click.secho("[+] Handoff note cleared.", fg="green")
            return

        if note:
            save_handoff_note(summary=note)
            click.secho("[+] Handoff note saved.", fg="green")
            return

        # Show current handoff note
        existing = load_handoff_note()
        if not existing:
            click.secho("[~] No handoff note from previous session.", fg="yellow")
            return

        click.secho("\n=== Handoff Note ===\n", fg="cyan", bold=True)
        if existing.get("summary"):
            _safe_echo(existing["summary"])
        if existing.get("open_threads"):
            click.secho("\nOpen threads:", fg="white", bold=True)
            for thread in existing["open_threads"]:
                _safe_echo(f"  - {thread}")
        if existing.get("mood"):
            click.secho(f"\nMood: {existing['mood']}", fg="bright_black")
        if existing.get("goals_state"):
            click.secho(f"Goals: {existing['goals_state']}", fg="bright_black")
        click.echo()

        if not show:
            clear_handoff_note()
            click.secho(
                "[~] Note consumed (cleared). Use --show to peek without clearing.",
                fg="bright_black",
            )

    @cli.command("preflight")
    @click.option("--auto", "auto_fix", is_flag=True, help="Auto-load briefing if missing")
    def preflight_cmd(auto_fix: bool) -> None:
        """Pre-session readiness check. Run this before doing any work.

        Checks: briefing loaded, thinking tools used, handoff note, active goals.
        With --auto, loads the briefing automatically if it's missing.
        """
        from divineos.core.hud_handoff import (
            mark_briefing_loaded,
            preflight_check,
        )

        result = preflight_check()

        click.secho("\n=== PREFLIGHT CHECK ===\n", fg="cyan", bold=True)

        for check in result["checks"]:
            if check["passed"]:
                click.secho(f"  [PASS] {check['name']}: {check['detail']}", fg="green")
            else:
                click.secho(f"  [FAIL] {check['name']}: {check['detail']}", fg="red")

        click.echo()

        if result["ready"]:
            click.secho("[+] Ready to work.", fg="green", bold=True)
        elif auto_fix and not result["briefing_loaded"]:
            # Auto-load briefing
            click.secho("[~] Auto-loading briefing...", fg="yellow")
            from divineos.core.active_memory import refresh_active_memory
            from divineos.core.knowledge import generate_briefing
            from divineos.core.memory import init_memory_tables

            init_memory_tables()
            refresh_active_memory(importance_threshold=0.3)

            output = generate_briefing(max_items=20)
            if output and output.strip():
                _safe_echo(output)
            mark_briefing_loaded()
            click.secho("\n[+] Briefing loaded. Ready to work.", fg="green", bold=True)
        else:
            click.secho(
                "[!] Not ready. Run: divineos briefing",
                fg="red",
                bold=True,
            )

        click.echo()
