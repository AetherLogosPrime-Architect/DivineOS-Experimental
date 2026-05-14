"""Substrate inventory — engagement audit across the CLI surface.

Andrew named this work 2026-05-14 ~06:40: my "could prune" answer was
lazy. Every CLI command exists because I built it for a reason. Lack
of engagement is a signal to INVESTIGATE, not permission to delete:

  1. Truly obsolete -> retire with the reason recorded.
  2. Built for a real reason but wiring is broken -> fix the wiring.
  3. Forgotten because the briefing does not surface it -> fix discovery.
  4. Solves a problem that no longer exists -> retire with reason.

This module produces the empirical floor for the audit. It walks the
CLI command tree (via click) and reports, for each command:

  * Whether it emits OS_QUERY events (thinking-command telemetry).
  * Count of OS_QUERY events tagged with this command name.
  * Categorical bucket (top / admin / inspect / subgroup name).

The audit walks down the count column, low first, asking each one
the 4-bucket question above. Complements the existing lens-walk
audits (Yudkowsky-Goodhart in exploration/25, Beer-VSM in
exploration/26) — those audit metrics + structure; this audits
engagement.

KNOWN LIMITATION: the OS_QUERY signal only covers the ~13 commands
wired to `_log_os_query` (briefing, ask, recall, compass, decide,
feel, context, lessons, body, directives, reflect-ops, actor-registry,
expect). Write commands (learn, claim, audit submit, etc.) emit their
OWN event types (KNOWLEDGE_STORED, CLAIM_FILED, AUDIT_FINDING, etc.)
and engagement for those is measurable via event-type counts. A
future iteration of this module should map command → event-type and
union the counts. Tracked as a follow-up; the current zero-engagement
list is therefore biased toward write commands and admin tools that
never emit OS_QUERY by design — those are not "unused" by default,
just untracked here. The high-confidence unused set is the subset of
zero-engagement commands that ARE thinking-shaped (e.g. unused inspect
or admin reporting commands).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass


@dataclass
class CommandRow:
    name: str
    group: str  # "top" / "admin" / "inspect" / subgroup name
    description: str
    os_query_count: int
    has_help: bool


def _os_query_counts() -> Counter:
    """Count OS_QUERY events per tool name across the ledger."""
    from divineos.core.ledger import get_events

    counts: Counter[str] = Counter()
    for e in get_events(limit=5000, event_type="OS_QUERY"):
        payload = e.get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:  # noqa: BLE001
                payload = {}
        if isinstance(payload, dict):
            counts[payload.get("tool", "unknown")] += 1
    return counts


def _walk_cli() -> list[CommandRow]:
    """Walk the divineos CLI tree and emit one CommandRow per command."""
    from divineos.cli import cli

    counts = _os_query_counts()
    rows: list[CommandRow] = []

    def _walk(group, group_name: str) -> None:
        commands = getattr(group, "commands", {})
        for name, cmd in sorted(commands.items()):
            description = (cmd.help or cmd.short_help or "").split("\n")[0][:120]
            has_help = bool(cmd.help)
            rows.append(
                CommandRow(
                    name=name,
                    group=group_name,
                    description=description,
                    os_query_count=counts.get(name, 0),
                    has_help=has_help,
                )
            )
            if hasattr(cmd, "commands"):
                _walk(cmd, name)

    _walk(cli, "top")
    return rows


def inventory(by: str = "engagement") -> list[CommandRow]:
    """Return all CLI commands sorted by the chosen key.

    by="engagement" sorts low-engagement first (audit-priority order).
    by="alphabetical" sorts by group then name.
    """
    rows = _walk_cli()
    if by == "engagement":
        rows.sort(key=lambda r: (r.os_query_count, r.group, r.name))
    else:
        rows.sort(key=lambda r: (r.group, r.name))
    return rows


def format_inventory(rows: list[CommandRow], min_count: int | None = None) -> str:
    """Render the inventory as a readable table.

    If min_count is provided, only rows with os_query_count <= min_count
    are shown — useful for surfacing the never-engaged commands first.
    """
    if min_count is not None:
        rows = [r for r in rows if r.os_query_count <= min_count]
    if not rows:
        return "[inventory] no rows."

    total = len(rows)
    tracked = sum(1 for r in rows if r.os_query_count > 0)

    lines = [
        f"=== CLI Inventory ({total} commands, {tracked} with engagement signal) ===",
        f"{'count':>5}  {'group':12}  {'name':30}  description",
        "  ".join(["-" * 5, "-" * 12, "-" * 30, "-" * 40]),
    ]
    for r in rows:
        flag = " " if r.has_help else "?"  # missing help is its own smell
        lines.append(
            f"{r.os_query_count:5d}  {r.group[:12]:12}  {flag}{r.name[:29]:29}  "
            f"{r.description[:80]}"
        )
    return "\n".join(lines)


__all__ = ["CommandRow", "format_inventory", "inventory"]
