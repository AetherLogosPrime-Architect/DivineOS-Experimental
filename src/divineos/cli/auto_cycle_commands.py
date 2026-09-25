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
from pathlib import Path

import click

from divineos.core import auto_cycle


def register(cli: click.Group) -> None:
    """Register auto-cycle commands on the CLI root."""
    cli.add_command(auto_cycle_group)


@click.group("auto-cycle")
def auto_cycle_group() -> None:
    """Auto-cycle phase 1: mechanical pre-compaction pipeline."""


def _guess_context_pct() -> float:
    """Live read of current context usage percentage from the session transcript.

    Ground-truth read — same source ``divineos context-tokens`` uses.
    Prior implementation read a hook-populated file that turned out to
    be stale or missing at the critical moment (auto-cycle stayed dark
    at 95% real context on 2026-07-10 because the file returned 0.0).
    Fixed 2026-07-11 per Andrew's principle: mechanisms are only as
    honest as their sources; touch the truth, not a copy of the truth.

    Returns 0.0 if snapshot is unavailable — the caller treats that as
    "below threshold, don't fire." Fail-safe direction matches the
    old behavior so the change doesn't cause unexpected firing when
    the snapshot fails.

    UNPINNED READINGS ARE REFUSED (Andrew correction #452, 2026-08-18).
    A snapshot with ``pinned=False`` was resolved by newest-mtime rather
    than by session id, so it may be another session's number entirely —
    on 2026-08-18 that path returned 96.1% from a transcript abandoned
    sixty-nine days earlier. This function's number decides whether the
    compaction ritual fires, and the ritual is the ONE thing token count
    is allowed to decide. Spending a stranger's number on it would fire
    the pipeline mid-work for no reason. Refusing costs at most a missed
    ritual in a harness that publishes no session id; accepting costs a
    ritual fired on fiction.
    """
    try:
        from divineos.core.context_tokens import get_context_snapshot
    except Exception:  # noqa: BLE001 - observability boundary
        return 0.0
    try:
        snap = get_context_snapshot()
    except Exception:  # noqa: BLE001 - observability boundary
        return 0.0
    pinned = bool(getattr(snap, "pinned", False))
    total = getattr(snap, "total_tokens", 0) or 0

    if pinned and total:
        # Live read succeeded. Stamp it so the heartbeat log carries the same
        # number the decision was made on, then spend it.
        _stamp_heartbeat()
        # 1M-token window is the standard for Claude Opus 4.x; matches the
        # cap divineos context-tokens uses by default.
        return float(total) / 1_000_000.0

    # LIVE READ FAILED. Fall back to the heartbeat before giving up.
    #
    # Added 2026-08-24. This branch used to `return 0.0`, and 0.0 means "3% of
    # the window used, plenty of room, do not fire." So a sensor that could not
    # see reported the single most reassuring number available, and the ritual
    # stayed dark at whatever the real level was. Andrew asked for a heartbeat
    # "to keep it updated every round" precisely so the decision stops depending
    # on the sensor being able to see at the one instant it is asked.
    #
    # The fallback is deliberately narrow. It accepts only a reading that was
    # PINNED TO THIS SESSION when it was taken and is recent -- never a stale
    # number from a different session, which is the failure that returned 96.1%
    # from a transcript abandoned sixty-nine days earlier (correction #452).
    try:
        from divineos.core.context_heartbeat import read_latest

        last = read_latest()
    except Exception:  # noqa: BLE001 - observability boundary
        last = None

    if last is not None and last.is_fresh and last.pct is not None:
        current_sid = getattr(snap, "session_id", None)
        if current_sid is None or last.session_id == current_sid:
            return float(last.pct)

    # Genuinely blind: no live read, no usable heartbeat. Still returns 0.0
    # because should_fire's contract is a float and firing on a fiction is the
    # worse error -- but the heartbeat log now carries a row saying UNKNOWN,
    # so the blindness is countable instead of invisible.
    _stamp_heartbeat()
    return 0.0


def _stamp_heartbeat() -> None:
    """Record one heartbeat row. Never raises; a missed beat is a log hole."""
    try:
        from divineos.core.context_heartbeat import beat

        beat()
    except Exception:  # noqa: BLE001 - observability boundary
        pass


def _usage_stamp() -> str:
    """When the usage block behind the current reading was written.

    Display-only companion to ``_guess_context_pct``, which returns a
    bare float and so cannot carry it. Empty string when unavailable —
    a missing stamp prints nothing rather than a guess.
    """
    try:
        from divineos.core.context_tokens import get_context_snapshot

        return str(get_context_snapshot().usage_timestamp or "")
    except Exception:  # noqa: BLE001 - observability boundary
        return ""


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
    if ctx_pct < 0:
        click.echo(
            "  context: UNKNOWN — no transcript source could answer"
            f"  threshold: {auto_cycle.TRIGGER_THRESHOLD * 100:.0f}%"
        )
        click.echo("    (unknown is not zero; this reads as cannot-tell, not as empty)")
    else:
        click.echo(
            f"  context: {ctx_pct * 100:.1f}%  threshold: {auto_cycle.TRIGGER_THRESHOLD * 100:.0f}%"
        )
        # When the reading was taken, on the same line of sight as the
        # number. This surface's percentage was quoted as current on
        # 2026-08-27 when it came from the last block before a
        # compaction — true of a window that no longer existed. Nothing
        # on screen could have shown that.
        stamp = _usage_stamp()
        if stamp:
            click.echo(f"    read from turn stamped {stamp}")
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
    if ctx_pct < 0 and not force:
        click.echo("[auto-cycle] context UNKNOWN — no transcript source could answer.")
        click.echo("[auto-cycle] refusing to decide on a measurement that does not exist.")
        click.echo("[auto-cycle] use --force to fire anyway")
        return
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
        # A dry run reports succeeded=True on steps that never ran; printing
        # that as OK is the reading that let phase 2 offer rest for nothing.
        status_flag = "DRY" if not step.ran else "OK " if step.succeeded else "FAIL"
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
    if ctx_pct < 0:
        # Loud, not silent. This path ran on every checkpoint for weeks
        # reading a fabricated 0.0; a cannot-measure must be visible.
        if json_out:
            click.echo(json.dumps({"action": "unknown", "reason": "no transcript source"}))
        else:
            click.echo("[auto-cycle] context UNKNOWN — no transcript source could answer", err=True)
        return
    defer_state = auto_cycle.load_defer_state()
    defers_used = int(defer_state.get("defers_used") or 0)
    has_active = _has_active_goal_progress()
    fire, reason = auto_cycle.should_fire(ctx_pct, has_active, defers_used)

    if fire:
        result = auto_cycle.run_phase1(context_pct=ctx_pct)
        auto_cycle.write_handshake_marker(result)
        auto_cycle.reset_defer_state()
        # The tree is named on the SAME line as the cycle, not on a nearby
        # one. Two checkouts share this log; a marker that records only that a
        # cycle fired leaves proximity as the reader's only relation, and both
        # of us then read one cause out of two unrelated true lines that
        # happened to land next to each other.
        tree = Path(result.repo_root).name if result.repo_root else "unknown-tree"
        if json_out:
            click.echo(
                json.dumps(
                    {
                        "action": "fired",
                        "cycle_id": result.cycle_id,
                        "repo_root": result.repo_root,
                    }
                )
            )
        else:
            click.echo(f"[auto-cycle] fired in {tree}: {result.cycle_id}", err=True)
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


@auto_cycle_group.command("offer")
def offer_cmd() -> None:
    """Phase 2: render the rest menu and record the offering.

    Reads the phase 1 handshake at ``auto_cycle.marker_path()``. With no usable
    handshake it says which of three things is true -- absent, damaged, or a
    dry run that saved nothing -- and changes no state. The handshake is left
    in place; ``close`` consumes it.
    """
    from divineos.core.auto_cycle_phase2 import (
        NoHandshake,
        inspect_handshake,
        offer_cycle,
        refusal_text,
    )

    record, text = offer_cycle()
    if record is None:
        if text:  # an offer is already pending
            click.secho(text, fg="yellow")
            return
        why = inspect_handshake()
        if isinstance(why, NoHandshake):
            click.secho(refusal_text(why), fg="bright_black")
        return
    click.echo(text)
    click.secho(f"[+] Offering recorded. cycle_id: {record.cycle_id}", fg="cyan")


@auto_cycle_group.command("close")
@click.option(
    "--outcome",
    required=True,
    help='One of "chose:<key>", "no-pull-honest", "timeout", "aborted".',
)
@click.option(
    "--real-shift",
    type=click.Choice(["yes", "no"], case_sensitive=False),
    default=None,
    help=(
        "For chose:<key> outcomes: did the resulting artifact register as "
        "real-shift or template-execution? Honest self-report. Feeds the "
        "falsifier ratio."
    ),
)
@click.option("--notes", default="", help="Freeform notes about the outcome.")
def close_cmd(outcome: str, real_shift: str | None, notes: str) -> None:
    """Phase 2: close the pending cycle and log its outcome for the falsifier.

    Examples:

        divineos auto-cycle close --outcome chose:dream --real-shift yes
        divineos auto-cycle close --outcome no-pull-honest
        divineos auto-cycle close --outcome timeout
        divineos auto-cycle close --outcome aborted --notes "fatal extract error"
    """
    from divineos.core.auto_cycle_phase2 import DamagedPending, close_cycle

    shift = None if real_shift is None else real_shift.lower() == "yes"
    try:
        result = close_cycle(outcome, real_shift=shift, notes=notes)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--outcome") from e
    except DamagedPending as e:
        raise click.ClickException(f"{e}. Nothing was closed or logged.") from e
    if result is None:
        click.secho(
            "[~] No pending cycle to close. Run 'auto-cycle offer' first.", fg="bright_black"
        )
        return
    click.secho(f"[+] Cycle closed. cycle_id: {result.cycle_id}", fg="green")
    click.secho(
        f"    outcome: {result.outcome}\n"
        f"    duration: {result.duration_sec:.1f}s\n"
        f"    real-shift: {result.real_shift}",
        fg="bright_black",
    )


@auto_cycle_group.command("audit")
def audit_cmd() -> None:
    """Phase 2: the falsifier ratio for prereg-4a7ed0c77c34.

    Bound: below 50% after at least 5 qualifying cycles means reshape or
    unwire. no-pull-honest cycles are shown beside the ratio, not in it.
    """
    from divineos.core.auto_cycle_phase2 import compute_falsifier_ratio, no_pull_count

    numerator, denominator, ratio = compute_falsifier_ratio()
    click.secho("=== Auto-cycle falsifier audit ===", fg="cyan", bold=True)
    click.echo()
    click.echo(f"  no-pull-honest (outside the ratio): {no_pull_count()}")
    if denominator == 0:
        click.secho("  No qualifying cycles yet. Falsifier undefined.", fg="bright_black")
        return
    click.echo(f"  real-shift outcomes:     {numerator}")
    click.echo(f"  qualifying cycles:       {denominator}")
    if ratio is not None:
        click.echo(f"  ratio:                   {ratio:.1%}")
    click.echo()
    if denominator < 5:
        click.secho(
            f"  [~] Only {denominator} qualifying cycles. The bound applies after 5. Watching.",
            fg="bright_black",
        )
    elif ratio is not None and ratio < 0.5:
        click.secho(
            "  [!] FALSIFIER FIRED — ratio below 50% after at least 5 cycles. "
            "The mechanism is producing dead-writing infrastructure. Reshape or unwire.",
            fg="red",
            bold=True,
        )
    else:
        click.secho("  [+] Above falsifier bound. Mechanism intact.", fg="green")


__all__ = ["auto_cycle_group", "register"]
