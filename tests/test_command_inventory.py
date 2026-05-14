"""Regression-pin tests for the substrate-inventory audit tool.

Andrew named the audit work 2026-05-14 ~06:40. The inventory is the
empirical floor: walk every CLI command, report engagement counts,
investigate the zero-engagement set rather than prune.

If these tests fail, the inventory has lost its ability to walk the
tree or its rendering contract has drifted.
"""

from __future__ import annotations

from divineos.core.command_inventory import (
    CommandRow,
    format_inventory,
    inventory,
)


def test_inventory_returns_rows() -> None:
    """LOAD-BEARING: the inventory must enumerate at least the core
    set of CLI commands; if this drops to zero the walker is broken."""
    rows = inventory()
    assert len(rows) >= 50, (
        f"Inventory only enumerated {len(rows)} commands. "
        "The CLI has ~150+. Walker has regressed."
    )


def test_inventory_includes_briefing_command() -> None:
    """`briefing` is one of the most-used thinking commands and must
    appear in the inventory."""
    rows = inventory()
    names = {r.name for r in rows}
    assert "briefing" in names, "Inventory missing 'briefing' command."


def test_inventory_includes_subgroup_commands() -> None:
    """Subgroup commands (e.g. admin, audit) must be walked, not just
    the top-level group itself."""
    rows = inventory()
    names = {r.name for r in rows}
    # `seed-export` lives under the admin subgroup
    assert "seed-export" in names, (
        "Inventory did not descend into the admin subgroup. "
        "Subgroup walker has regressed."
    )


def test_format_inventory_renders_count_column() -> None:
    """Render output must include the engagement count column header."""
    rows = inventory()[:5]
    rendered = format_inventory(rows)
    assert "count" in rendered
    assert "group" in rendered
    assert "description" in rendered


def test_format_inventory_min_count_filter() -> None:
    """min_count filter must restrict to rows at or below threshold."""
    rows = [
        CommandRow(name="a", group="top", description="", os_query_count=0, has_help=True),
        CommandRow(name="b", group="top", description="", os_query_count=10, has_help=True),
    ]
    rendered = format_inventory(rows, min_count=0)
    assert "a" in rendered
    assert " b " not in rendered  # b filtered out


def test_inventory_sort_by_engagement_low_first() -> None:
    """The default sort surfaces low-engagement commands first so the
    audit walks them in priority order."""
    rows = inventory(by="engagement")
    counts = [r.os_query_count for r in rows]
    assert counts == sorted(counts), (
        "Inventory not sorted ascending by engagement; audit-priority "
        "order has regressed."
    )
