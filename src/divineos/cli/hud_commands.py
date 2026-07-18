"""HUD commands — hud, goal group, plan."""

import json
import sqlite3
import time

import click

from divineos.cli._helpers import _safe_echo


def _format_age(age_days: float) -> str:
    """Human-readable age for goal-check output. Pure, no mutation."""
    if age_days < 1 / 24:  # under 1 hour
        return f"{int(age_days * 24 * 60)}m"
    if age_days < 1:
        return f"{age_days * 24:.1f}h"
    if age_days < 14:
        return f"{age_days:.1f}d"
    return f"{int(age_days)}d (!! stale)"


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
    @click.option("--brief", is_flag=True, help="Condensed view: just what I need right now")
    @click.option(
        "--slots", default="", help="Comma-separated slot names to display (default: all)"
    )
    def hud_cmd(save: bool, load: bool, brief: bool, slots: str) -> None:
        """Display my heads-up display — everything I need to know at once."""
        from divineos.core.hud import (
            BRIEF_SLOTS,
            build_hud,
            load_hud_snapshot,
            save_hud_snapshot,
        )

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

        if brief:
            slot_list = BRIEF_SLOTS
        elif slots:
            slot_list = [s.strip() for s in slots.split(",") if s.strip()]
        else:
            slot_list = None
        hud_text = build_hud(slots=slot_list)
        _safe_echo(hud_text)

    @cli.group("goal", invoke_without_command=True)
    @click.pass_context
    def goal_group(ctx: click.Context) -> None:
        """Track what the user asked me to do. My compass against drift."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(goal_list_cmd)

    @goal_group.command("add")
    @click.argument("text")
    @click.option("--original", default="", help="The user's exact words")
    def goal_add_cmd(text: str, original: str) -> None:
        """Add a new goal to track."""
        if not text.strip():
            click.secho("[-] Goal text cannot be empty.", fg="yellow")
            return

        # Error-registry jailbreak-response gate (Andrew 2026-07-17):
        # open errors block starting new work. Investigation and fixes
        # remain unblocked (tools still work); only new-main-goal
        # transitions are refused. The goal-text bypasses the block
        # when it names an existing open error_id — that means the new
        # goal IS the investigation of the open error, the only allowed
        # forward motion.
        #
        # Attribution-gaming fix (Aletheia arc-audit 2026-07-17):
        # RESOLVE the named error_id against the registry rather than
        # substring-match against open ids. Same discipline as F34's
        # pointer-resolver: a cite must resolve to a real artifact, not
        # just look like one. Extract err-XXXX substrings from the goal
        # text and pass EACH through get_error() to verify existence AND
        # open state. Naming a fake err-fake123 in goal text no longer
        # passes the block.
        try:
            import re as _re

            from divineos.core import error_registry as _err_reg

            open_errs = _err_reg.list_open_errors()
            if open_errs:
                # Extract candidate error_id references from the goal text.
                # Pattern matches the err-XXXXXXXXXXXX shape file_error uses.
                named_ids = _re.findall(r"err-[a-f0-9]{12}", text.lower())
                # RESOLVE each: verify the record exists AND is open.
                names_open_error = False
                for nid in named_ids:
                    rec = _err_reg.get_error(nid)
                    if rec is not None and rec.get("state") == "open":
                        names_open_error = True
                        break
                if not names_open_error:
                    click.secho(_err_reg.block_reason(), fg="red")
                    click.echo("")
                    click.secho(
                        f"[-] Goal-add refused. New goal '{text}' does not name any open error.",
                        fg="red",
                    )
                    click.secho(
                        "    To start a new goal, close/defer the open errors first,",
                        fg="bright_black",
                    )
                    click.secho(
                        "    or make this goal explicitly about investigating one "
                        "(include the err-XXXX id in the goal text).",
                        fg="bright_black",
                    )
                    raise click.exceptions.Exit(1)
        except click.exceptions.Exit:
            raise
        except Exception:  # noqa: BLE001 — registry-side error must not deadlock goal-add
            import logging

            logging.getLogger(__name__).exception(
                "error_registry check failed in goal_add — proceeding without block"
            )

        from divineos.core.hud_state import add_goal

        add_goal(text, original_words=original)
        click.secho(f"[+] Goal added: {text}", fg="green")
        if original:
            click.secho(f'    (User\'s words: "{original}")', fg="bright_black")

        # Build-shape detector (round-2 audit + Andrew's directive).
        # If goal looks like a build/design task, surface a soft-advise
        # to consult the council before implementing. Soft register per
        # Tannen — informational, not forced ritual.
        try:
            from divineos.core.council_auto import detect_build_shape

            shape = detect_build_shape(text)
            if shape.is_build_shape:
                click.echo()
                click.secho(
                    f"[council] This goal looks like a build/design task "
                    f"({shape.matched_keyword!r}). Consider walking the "
                    f"council before implementing:",
                    fg="cyan",
                )
                preview = text[:80] + "..." if len(text) > 80 else text
                click.secho(
                    f'  divineos mansion council "{preview}"',
                    fg="bright_black",
                )
        except Exception:  # noqa: BLE001 — best-effort; never block goal-add
            import logging

            logging.getLogger(__name__).debug("build-shape detector unavailable", exc_info=True)

        # Adjacency surface (Andrew 2026-06-12 + kid 636fcba4): when a
        # new goal is set, run the semantic-search consumer against
        # the goal text and surface top adjacency hits. Closes the
        # built-but-not-inhabited failure mode the find tool was
        # exactly meant to address (Bengio lens, prereg-2ad79e23fcf7
        # falsifier). Same altitude as the council advise above —
        # soft, informational, never blocks goal-add.
        try:
            from divineos.core.goal_adjacency import adjacency_lines_for_goal

            adjacency_lines = adjacency_lines_for_goal(text)
            if adjacency_lines:
                click.echo()
                for i, line in enumerate(adjacency_lines):
                    color = "cyan" if i == 0 else "bright_black"
                    click.secho(line, fg=color)
        except Exception:  # noqa: BLE001 — best-effort; never block goal-add
            import logging

            logging.getLogger(__name__).debug("adjacency surface unavailable", exc_info=True)

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

    @goal_group.command("auto-close")
    @click.option(
        "--message",
        default=None,
        help="Commit message text. If omitted, reads HEAD's commit message.",
    )
    @click.option(
        "--threshold",
        default=0.5,
        type=float,
        help="Minimum overlap ratio (default 0.5).",
    )
    def goal_auto_close_cmd(message: str | None, threshold: float) -> None:
        """Auto-close active goals whose tokens overlap a commit message.

        Closure-discipline structural fix (operator-named 2026-05-05):
        right path becomes automatic instead of remembered. When a
        commit lands with text substantially matching an open goal,
        the goal auto-closes.
        """
        import subprocess

        from divineos.core.goal_auto_close import auto_close_from_message

        if message is None:
            try:
                message = subprocess.check_output(
                    ["git", "log", "-1", "--pretty=%B"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                click.secho("[-] Could not read HEAD commit message.", fg="red")
                return

        result = auto_close_from_message(message, threshold=threshold)
        if not result.closed:
            click.secho("[~] No goals closed.", fg="bright_black")
            if result.skipped:
                click.secho(
                    f"    {len(result.skipped)} goal(s) considered (below threshold).",
                    fg="bright_black",
                )
            return

        click.secho(f"[+] Auto-closed {len(result.closed)} goal(s):", fg="green")
        for snippet in result.closed:
            click.secho(f"    -> {snippet}", fg="green")

    @goal_group.command("list")
    def goal_list_cmd() -> None:
        """Show current goals.

        For the instrument-produced action-item list (preregs,
        Andrew-corrections, audit findings, claims) — run
        `divineos todos`. That command already closes claim 2026-06-06
        (T1, 85%) about manual-only goal subsystem.
        """
        from divineos.core.hud import SLOT_BUILDERS

        _safe_echo(SLOT_BUILDERS["active_goals"]())

    @goal_group.command("check")
    def goal_check_cmd() -> None:
        """Put my active goals in front of me to review — no auto-anything.

        Lists each active goal with age and how long since I last touched it,
        plus the close-options (done / abandoned / still-active). Decision
        stays with me. The machine surfaces the data; I do the thinking.

        Filed 2026-05-12 as the root-fix for commitment-fulfillment showing
        14 active / 0 closed across sessions. Auto-cleanup would have
        substituted machine-judgment for the review act; this surface keeps
        the cognition where it belongs. Per the cognitive-named-tools
        warning in CLAUDE.md: tools point at the work; they are not it.
        """
        from divineos.core.hud_state import get_active_goals

        goals = get_active_goals()
        if not goals:
            click.secho("[~] No active goals.", fg="bright_black")
            return

        now = time.time()
        click.secho(
            f"\n=== Goal review — {len(goals)} active. Decide each. ===\n",
            fg="cyan",
            bold=True,
        )
        for i, g in enumerate(goals, 1):
            added = g.get("added_at", 0.0)
            age_days = (now - added) / 86400 if added else 0.0
            age_label = _format_age(age_days)
            click.secho(f"  [{i}] (age {age_label})", fg="bright_black", nl=False)
            click.echo()
            text = (g.get("text") or "").strip()
            for ln in text.splitlines() or [text]:
                _safe_echo(f"      {ln}")
            click.echo()

        click.secho("  Decide each:", fg="cyan")
        click.secho("    still alive  → leave it; rerun this command tomorrow", fg="bright_black")
        click.secho('    done         → divineos goal done "<exact-or-prefix>"', fg="bright_black")
        click.secho(
            '    abandoned    → divineos goal done "<exact-or-prefix>"   (mark closed)',
            fg="bright_black",
        )
        click.secho(
            "    consolidate  → divineos goal cull   (proposes merges; you approve)",
            fg="bright_black",
        )
        click.echo()

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
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
    def goal_reset_cmd(yes: bool) -> None:
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

        if not yes:
            click.secho(f"[!] This will remove all {len(goals)} goals.", fg="yellow")
            try:
                click.confirm("Proceed?", abort=True)
            except click.exceptions.Abort:
                click.echo("Aborted.")
                return
            except (EOFError, OSError):
                click.echo(
                    "[!] Non-interactive stdin and --yes not passed. Aborting reset.",
                    err=True,
                )
                return
        path.write_text("[]", encoding="utf-8")
        click.secho(f"[+] Reset {len(goals)} goals.", fg="green")

    @goal_group.command("cull")
    @click.option(
        "--auto", "auto_mode", is_flag=True, help="Auto-complete obvious matches without prompting"
    )
    def goal_cull_cmd(auto_mode: bool) -> None:
        """Propose stale goal removals with evidence from knowledge/decisions."""
        from divineos.core.hud import _ensure_hud_dir

        path = _ensure_hud_dir() / "active_goals.json"
        if not path.exists():
            click.secho("[~] No goals to cull.", fg="yellow")
            return

        try:
            goals = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            click.secho("[~] No goals to cull.", fg="yellow")
            return

        active = [g for g in goals if g.get("status") != "done"]
        if not active:
            click.secho("[~] No active goals to cull.", fg="yellow")
            return

        import time

        from divineos.core.goal_cull import assess_goal_staleness

        now = time.time()
        proposals: list[dict] = []
        for goal in active:
            assessment = assess_goal_staleness(goal, now)
            if assessment["stale"]:
                proposals.append({"goal": goal, **assessment})

        if not proposals:
            click.secho("[~] No stale goals detected. All goals look current.", fg="green")
            return

        click.secho(f"\n=== Goal Cull: {len(proposals)} proposals ===\n", fg="cyan", bold=True)
        completed = 0
        for p in proposals:
            goal = p["goal"]
            age_days = p["age_days"]
            evidence = p["evidence"]

            click.secho(f"  [{age_days}d old] {goal['text']}", fg="yellow")
            for e in evidence:
                click.secho(f"    {e}", fg="bright_black")

            if auto_mode:
                goal["status"] = "done"
                completed += 1
                click.secho("    -> Auto-completed", fg="green")
            else:
                if click.confirm("    Mark complete?", default=False):
                    goal["status"] = "done"
                    completed += 1

        if completed > 0:
            path.write_text(json.dumps(goals, indent=2), encoding="utf-8")
            click.secho(f"\n[+] Culled {completed} stale goals.", fg="green")
        else:
            click.secho("\n[~] No goals culled.", fg="bright_black")

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
    @click.option("--show", is_flag=True, help="Show current state-note without clearing")
    @click.option("--clear", is_flag=True, help="Clear the state-note")
    def handoff_cmd(note: str | None, show: bool, clear: bool) -> None:
        """View or write a state-note — where I am in the work.

        Surfaces in the briefing on resumption so I find my place.
        Without arguments, shows the current note.
        With a NOTE argument, saves a manual one.
        """
        from divineos.core.hud_handoff import (
            clear_handoff_note,
            load_handoff_note,
            save_handoff_note,
        )

        if clear:
            clear_handoff_note()
            click.secho("[+] State-note cleared.", fg="green")
            return

        if note:
            save_handoff_note(summary=note)
            click.secho("[+] State-note saved. Surfaces on resumption.", fg="green")
            return

        # Show current state-note
        existing = load_handoff_note()
        if not existing:
            click.secho("[~] No state-note from a prior run.", fg="yellow")
            return

        click.secho("\n=== State-Note (where I was) ===\n", fg="cyan", bold=True)
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

    @cli.command("checkpoint")
    def checkpoint_cmd() -> None:
        """Run a lightweight session checkpoint — save state without full pipeline.

        Saves HUD snapshot, handoff note, and ledger event. Use this periodically
        to preserve state. Lighter than SESSION_END (no knowledge extraction).
        """
        from divineos.core.session_checkpoint import run_checkpoint

        result = run_checkpoint()
        click.secho(f"[+] {result}", fg="green")

    @cli.command("mini-save")
    def mini_save_cmd() -> None:
        """Task-boundary save — extract knowledge without full pipeline.

        Lighter than SESSION_END but captures real learning: analysis,
        knowledge extraction, episode, curation, lessons, handoff note.
        Run this after finishing a task, before asking what's next.
        """
        from divineos.core.session_checkpoint import run_mini_session_save

        click.secho("[~] Running mini session save...", fg="cyan")
        result = run_mini_session_save()

        if result.get("error"):
            click.secho(f"[!] Mini-save error: {result['error']}", fg="yellow")
            return

        parts = []
        if result["knowledge_extracted"]:
            parts.append(f"{result['knowledge_extracted']} knowledge entries")
        if result["episode_stored"]:
            parts.append("episode logged")
        if result["handoff_saved"]:
            parts.append("handoff saved")
        curation = result.get("curation", {})
        if curation.get("archived") or curation.get("text_cleaned"):
            c_parts = []
            if curation.get("archived"):
                c_parts.append(f"{curation['archived']} archived")
            if curation.get("text_cleaned"):
                c_parts.append(f"{curation['text_cleaned']} cleaned")
            parts.append(f"curation: {', '.join(c_parts)}")

        if parts:
            click.secho(f"[+] Saved: {', '.join(parts)}", fg="green")
        else:
            click.secho("[~] Nothing new to save.", fg="bright_black")

    @cli.command("context-status")
    def context_status_cmd() -> None:
        """Show current context usage estimate and checkpoint state."""
        from divineos.core.session_checkpoint import (
            _load_state,
            context_warning_level,
            estimate_token_usage,
            format_context_warning,
        )

        state = _load_state()
        edits = state.get("edits", 0)
        calls = state.get("tool_calls", 0)
        checkpoints = state.get("checkpoints_run", 0)
        level = context_warning_level(state)

        click.secho(f"\n  Edits: {edits}", fg="cyan")
        click.secho(f"  Tool calls: {calls}", fg="cyan")
        click.secho(f"  Checkpoints run: {checkpoints}", fg="cyan")
        click.secho(
            f"  Context level (tool calls): {level}",
            fg={"ok": "green", "warn": "yellow", "urgent": "red", "critical": "red"}.get(
                level, "white"
            ),
        )

        # Token estimation from character tracking
        tokens = estimate_token_usage()
        if tokens["chars_tracked"] > 0:
            tok_color = {"ok": "green", "warn": "yellow", "urgent": "red", "critical": "red"}
            click.secho(
                f"  Token estimate: ~{tokens['estimated_tokens']:,} "
                f"({tokens['estimated_pct']:.0%} of usable context) [{tokens['level']}]",
                fg=tok_color.get(tokens["level"], "white"),
            )
        else:
            click.secho("  Token estimate: no character data tracked yet", fg="bright_black")

        warning = format_context_warning(state)
        if warning:
            click.secho(f"\n  {warning}", fg="yellow" if level == "warn" else "red")
        else:
            click.secho("\n  Context usage normal.", fg="green")
        click.echo()
