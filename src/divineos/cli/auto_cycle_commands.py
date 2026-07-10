"""CLI commands for auto-cycle phase 1 — status, fire, defer-check.

Andrew 2026-07-10 memory-linkage-day evening: automation for the pre-
compaction cycle so context-window pressure doesn't have to be remembered.
Phase 2 (invitational surface) is Aria's side with its own CLI at
auto_cycle_commands on her branch — this file is phase 1 only.

Commands here:

- ``divineos auto-cycle status`` — print current context %, whether would-
  fire, defer counter, whether marker present. Read-only.
- ``divineos auto-cycle fire`` — invoke phase 1 pipeline now regardless of
  threshold. Supports ``--dry-run`` for testing. Prints marker JSON path.
- ``divineos auto-cycle defer-check`` — internal-facing check used by hooks:
  reads context, evaluates ``should_fire`` with defer state, runs phase 1
  if firing, updates defer counter if deferring. Silent when below threshold.
"""

from __future__ import annotations

import json
import time

import click

from divineos.core import auto_cycle


def register(cli: click.Group) -> None:
    """Register auto-cycle commands on the CLI root."""
    cli.add_command(auto_cycle_group)


@click.group("auto-cycle")
def auto_cycle_group() -> None:
    """Auto-cycle phase 1: mechanical pre-compaction pipeline."""


def _guess_context_pct() -> float:
    """Best-effort read of current context usage percentage.

    Reads ``~/.divineos/context_tokens.json`` if present (produced by the
    token-state-surface hook). Returns 0.0 if unavailable — the caller
    treats that as "below threshold, don't fire."
    """
    from divineos.core.paths import divineos_home

    path = divineos_home() / "context_tokens.json"
    if not path.exists():
        return 0.0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0.0
    if not isinstance(data, dict):
        return 0.0
    used = data.get("used", 0)
    total = data.get("total", 1_000_000)
    if not isinstance(used, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return 0.0
    return float(used) / float(total)


def _has_active_goal_progress(window_sec: int = 300) -> bool:
    """Heuristic: has a substrate goal been touched in the last window?

    Consulted by ``should_fire`` for the defer branch. Reads goal state
    file if present. Fail-safe returns False (no defer, allow fire) —
    prefer firing over blocking, per Andrew's "force option, not choosing."
    """
    from divineos.core.paths import divineos_home

    path = divineos_home() / "goals.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(data, list):
        return False
    now = time.time()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        last_ts = entry.get("last_updated_at", 0)
        status = entry.get("status", "")
        if status == "active" and isinstance(last_ts, (int, float)):
            if now - last_ts < window_sec:
                return True
    return False


@auto_cycle_group.command("status")
def status_cmd() -> None:
    """Show current auto-cycle state — context %, would-fire, defer counter, marker."""
    ctx_pct = _guess_context_pct()
    defer_state = auto_cycle.load_defer_state()
    defers_used = int(defer_state.get("defers_used") or 0)
    has_active = _has_active_goal_progress()
    fire, reason = auto_cycle.should_fire(ctx_pct, has_active, defers_used)
    marker = auto_cycle.read_handshake_marker()

    click.echo("=== auto-cycle status ===")
    click.echo(
        f"  context: {ctx_pct * 100:.1f}%  threshold: {auto_cycle.TRIGGER_THRESHOLD * 100:.0f}%"
    )
    click.echo(f"  active goal progress: {has_active}")
    click.echo(f"  defers used: {defers_used}/{auto_cycle.MAX_DEFERS}")
    click.echo(f"  would fire: {fire}  ({reason})")
    if marker is not None:
        cycle_id = marker.get("cycle_id", "?")
        completed_at = marker.get("phase1_completed_at", "?")
        click.echo(f"  handshake marker present: {cycle_id} at {completed_at}")
        click.echo("    (phase 2 has not consumed it yet)")
    else:
        click.echo("  handshake marker: absent (no pending phase 2 handoff)")


@auto_cycle_group.command("fire")
@click.option("--dry-run", is_flag=True, help="Show what would run without executing steps.")
@click.option(
    "--force",
    is_flag=True,
    help="Fire even when below threshold. Overrides trigger check.",
)
def fire_cmd(dry_run: bool, force: bool) -> None:
    """Fire phase 1 now — commit, extract, sleep, write handshake marker.

    Without ``--force``, refuses to fire if ``should_fire`` returns False so
    the trigger discipline is preserved. With ``--force``, runs unconditionally.
    """
    ctx_pct = _guess_context_pct()
    if not force:
        defer_state = auto_cycle.load_defer_state()
        defers_used = int(defer_state.get("defers_used") or 0)
        has_active = _has_active_goal_progress()
        fire, reason = auto_cycle.should_fire(ctx_pct, has_active, defers_used)
        if not fire:
            click.echo(f"[auto-cycle] would not fire: {reason}")
            click.echo("[auto-cycle] use --force to fire anyway")
            return
    click.echo(f"[auto-cycle] firing phase 1 at context {ctx_pct * 100:.1f}%...")
    result = auto_cycle.run_phase1(context_pct=ctx_pct, dry_run=dry_run)
    marker_file = auto_cycle.write_handshake_marker(result)
    auto_cycle.reset_defer_state()

    click.echo(f"[auto-cycle] cycle_id: {result.cycle_id}")
    for name, step in result.steps.items():
        status_flag = "OK " if step.succeeded else "FAIL"
        click.echo(
            f"  [{status_flag}] {name}: {step.duration_sec}s, tokens_est={step.tokens_used_est}"
        )
        if step.error_class:
            click.echo(f"      error: {step.error_class}")
    click.echo(f"[auto-cycle] handshake marker written: {marker_file}")


@auto_cycle_group.command("defer-check")
@click.option("--json-out", is_flag=True, help="Emit machine-readable JSON on stdout.")
def defer_check_cmd(json_out: bool) -> None:
    """Internal-facing trigger check — for hooks.

    Reads context, evaluates ``should_fire`` with defer state, fires phase 1
    if firing, updates defer counter if deferring. Silent when below threshold.
    Human-mode by default; ``--json-out`` for scripting.
    """
    ctx_pct = _guess_context_pct()
    defer_state = auto_cycle.load_defer_state()
    defers_used = int(defer_state.get("defers_used") or 0)
    has_active = _has_active_goal_progress()
    fire, reason = auto_cycle.should_fire(ctx_pct, has_active, defers_used)

    if fire:
        result = auto_cycle.run_phase1(context_pct=ctx_pct)
        auto_cycle.write_handshake_marker(result)
        auto_cycle.reset_defer_state()
        if json_out:
            click.echo(json.dumps({"action": "fired", "cycle_id": result.cycle_id}))
        else:
            click.echo(f"[auto-cycle] fired: {result.cycle_id}", err=True)
        return

    if ctx_pct < auto_cycle.TRIGGER_THRESHOLD:
        if json_out:
            click.echo(json.dumps({"action": "silent", "reason": reason}))
        return

    new_defers = defers_used + 1
    auto_cycle.save_defer_state(
        {
            "defers_used": new_defers,
            "last_defer_at": time.time(),
            "cycle_start_ts": defer_state.get("cycle_start_ts"),
        }
    )
    if json_out:
        click.echo(json.dumps({"action": "deferred", "defers_used": new_defers, "reason": reason}))
    else:
        click.echo(
            f"[auto-cycle] deferred ({new_defers}/{auto_cycle.MAX_DEFERS}): {reason}",
            err=True,
        )


__all__ = ["auto_cycle_group", "register"]
