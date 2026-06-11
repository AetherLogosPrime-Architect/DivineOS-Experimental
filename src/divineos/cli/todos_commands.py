"""`divineos todos` — unified action-item list across all substrate stores.

Closes claim 2026-06-06 18:28: the OS does not generate todos from its
own observable state. Pulls from preregs / corrections / audit /
claims into a single ranked surface; renders grouped by source with
the source-appropriate priority key first.

Recognition-aware: audit findings whose titles begin with ``CONFIRMS``
or ``RECOGNIZED`` are excluded — they're acknowledgements, not action
items. Same discipline as the briefing dashboard's unresolved-finding
row.
"""

from __future__ import annotations

import click


_SOURCE_HEADER = {
    "prereg": "Pre-registrations (OPEN, most-overdue first)",
    "correction": "Andrew-corrections (OPEN, oldest first)",
    "audit": "Audit findings (OPEN, recognition-filtered, severity-ranked)",
    "claim": "Claims (OPEN, action-tier T1/T2 only)",
}


def register(cli: click.Group) -> None:
    """Register the todos command."""

    @cli.command("todos")
    @click.option(
        "--source",
        "source",
        type=click.Choice(["prereg", "correction", "audit", "claim", "all"]),
        default="all",
        help="Restrict to one source (default: all four).",
    )
    @click.option(
        "--counts-only",
        is_flag=True,
        help="Print per-source counts only; skip per-item detail.",
    )
    @click.option(
        "--limit",
        type=int,
        default=10,
        help="Cap items shown per source (default: 10).",
    )
    def todos_cmd(source: str, counts_only: bool, limit: int) -> None:
        """Unified action-item list across preregs/corrections/audit/claims."""
        from divineos.core.unified_todos import collect_todos, summary_counts

        if counts_only:
            counts = summary_counts()
            total = sum(counts.values())
            click.echo(f"=== Todos summary (total action items: {total}) ===")
            for src, count in counts.items():
                click.echo(f"  {src:12} {count:4}  ({_SOURCE_HEADER[src]})")
            return

        sources = ("prereg", "correction", "audit", "claim") if source == "all" else (source,)
        items = collect_todos(sources=sources)
        if not items:
            click.echo("=== Todos — no action items in the requested sources ===")
            return

        click.echo(f"=== Todos ({len(items)} action items) ===\n")
        current_source = None
        shown_for_current = 0
        for it in items:
            if it.source != current_source:
                current_source = it.source
                shown_for_current = 0
                click.echo(f"\n## {_SOURCE_HEADER[it.source]}\n")
            if shown_for_current >= limit:
                continue
            shown_for_current += 1
            age = f"{it.age_days:.0f}d ago" if it.age_days is not None else "—"
            extra_bits = []
            if it.source == "prereg":
                overdue = it.extra.get("overdue_days") or 0
                if overdue > 0:
                    extra_bits.append(f"{overdue:.0f}d overdue")
            elif it.source == "audit":
                extra_bits.append(it.extra.get("severity", ""))
            elif it.source == "claim":
                extra_bits.append(it.extra.get("tier", ""))
            extras = " | ".join(b for b in extra_bits if b)
            line = f"  [{it.item_id[:20]}] {age:12}"
            if extras:
                line += f"  ({extras})"
            click.echo(line)
            click.echo(f"      {it.summary[:140]}")

        # Per-source truncation note
        per_source_counts: dict[str, int] = {}
        for it in items:
            per_source_counts[it.source] = per_source_counts.get(it.source, 0) + 1
        truncated = [(src, n) for src, n in per_source_counts.items() if n > limit]
        if truncated:
            click.echo("")
            for src, n in truncated:
                click.echo(
                    f"  ({n - limit} more {src}-items truncated; use --limit {n} to see all)"
                )
