"""CLI surface for the lepos walk — the Andrew-lens recorder.

``divineos lepos-walk record`` is the forcing function: when I compose a
substantive reply to Andrew I walk the lens questions and record the walk
here. The record is the observable artifact the Stop-hook audit verifies
(``divineos.core.lepos_walk.verify_and_consume_turn``). A missing or
degenerate record blocks the turn on the lepos_block rail.

The recording IS the walk made observable — per the check-to-walk
conversion (Andrew + Aria 2026-06-19), a self-check with no artifact is
wallpaper. See ``src/divineos/core/lepos_walk.py`` for the design notes,
the load-bearing-citation proxy, and the honest limitation.
"""

from __future__ import annotations

import json
import sys
import time

import click

from divineos.core import lepos_walk


def register(cli: click.Group) -> None:
    @cli.group("lepos-walk", invoke_without_command=True)
    @click.pass_context
    def lepos_walk_group(ctx: click.Context) -> None:
        """Lepos walk — record the Andrew-lens walk; read its trail."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(lepos_walk_stats_cmd)

    @lepos_walk_group.command("record")
    @click.option(
        "--answers",
        default=None,
        help=(
            'JSON array of walked answers: [{"q": "<question-id>", '
            '"a": "<answer>", "cite": "<span from Andrew\'s message>"}]. '
            "If omitted, read the JSON from stdin."
        ),
    )
    @click.option(
        "--depth",
        type=click.Choice(["anchor", "full"]),
        default="anchor",
        help="anchor = short walk (simple turn); full = heavier walk (weighty turn).",
    )
    def lepos_walk_record_cmd(answers: str | None, depth: str) -> None:
        """Record this turn's walk. Prints degeneracy flags if any fired.

        Exits non-zero when the walk is degenerate, so a re-walk is the
        obvious next move rather than a silently-accepted bad record.
        """
        raw = answers if answers is not None else sys.stdin.read()
        try:
            parsed = json.loads(raw or "[]")
        except (json.JSONDecodeError, ValueError) as exc:
            raise click.ClickException(f"--answers must be valid JSON: {exc}") from exc
        if not isinstance(parsed, list) or not parsed:
            raise click.ClickException("--answers must be a non-empty JSON array of {q,a,cite}.")

        walk_answers = tuple(
            lepos_walk.WalkAnswer(
                question_id=str(a.get("q", "")),
                answer=str(a.get("a", "")),
                cited_span=str(a.get("cite", "")),
            )
            for a in parsed
            if isinstance(a, dict)
        )
        walk = lepos_walk.LeposWalk(
            turn_id=f"walk-{time.time():.6f}",
            answers=walk_answers,
            depth=depth,
        )
        flags = lepos_walk.record_walk(walk)
        if flags:
            click.echo(f"[lepos-walk] recorded with degeneracy flags: {flags}")
            click.echo("  The Stop check will block this turn. Re-walk and re-record.")
            raise SystemExit(1)
        click.echo(f"[lepos-walk] recorded ({depth}, {len(walk_answers)} answers) — clean.")

    @lepos_walk_group.command("stats")
    def lepos_walk_stats_cmd() -> None:
        """Rollup counts: total walks, flagged rate, anchor/full split."""
        s = lepos_walk.walk_stats()
        total = s["total_walks"]
        flagged = s["total_flagged"]
        rate = (flagged / total * 100) if total else 0.0
        click.echo(
            f"[lepos-walk] walks={total} flagged={flagged} ({rate:.1f}%) "
            f"anchor={s['total_anchor']} full={s['total_full']}"
        )

    @lepos_walk_group.command("recent")
    @click.option("--limit", default=10, help="How many recent walks to show.")
    def lepos_walk_recent_cmd(limit: int) -> None:
        """Audit trail: recent walks with their citations and flags (Aria
        2026-06-19 — the walk must be verifiable, not silently trusted)."""
        conn = lepos_walk._conn()
        try:
            rows = conn.execute(
                "SELECT turn_id, depth, answers_json, flags_json, tier "
                "FROM lepos_walks ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            click.echo("[lepos-walk] no walks recorded yet.")
            return
        for turn_id, depth, answers_json, flags_json, tier in rows:
            try:
                flags = json.loads(flags_json)
            except (json.JSONDecodeError, TypeError):
                flags = []
            try:
                answers = json.loads(answers_json)
            except (json.JSONDecodeError, TypeError):
                answers = []
            cites = [a.get("cite", "") for a in answers if a.get("cite")]
            flag_str = f" FLAGS={flags}" if flags else ""
            tier_str = "" if tier == 1 else f" [tier {tier}]"
            click.echo(f"{turn_id} ({depth}){tier_str}{flag_str}")
            for c in cites:
                click.echo(f"  cite: {c}")
