"""CLI for class-fix declarations (see ``divineos.core.class_fix``).

Deliberately thin. Every judgement lives in the core module; this is the door.
Note what is absent: no way to state a population. The count is produced by
running the search and by nothing else, which is the constraint the council
walk put on this whole mechanism.
"""

from __future__ import annotations

import click

from divineos.core import class_fix as cf


@click.group("class-fix")
def class_fix_group() -> None:
    """Declare a class-repair and prove the population actually fell."""


def register(cli: click.Group) -> None:
    cli.add_command(class_fix_group)


@class_fix_group.command("declare")
@click.argument("name")
@click.option("--pattern", required=True, help="Regex identifying every site of the class.")
@click.option("--root", default=".", help="Directory to sweep (default: here).")
@click.option(
    "--glob",
    "globs",
    multiple=True,
    default=("*.py",),
    help="Filename globs to search; repeatable.",
)
@click.option(
    "--exclude",
    "exclude",
    multiple=True,
    help="Path substrings to leave out, e.g. the module that OWNS the convention. "
    "Stored with the declaration and reused verbatim at verify time, and printed "
    "on every report, because this is where the mechanism could be turned into a stamp.",
)
def declare_cmd(
    name: str, pattern: str, root: str, globs: tuple[str, ...], exclude: tuple[str, ...]
) -> None:
    """Measure how many sites of this class exist, before repairing any of them."""
    fix = cf.declare(name, pattern, root, tuple(globs), tuple(exclude))
    click.echo(cf.format_fix(fix))
    if fix.state() == cf.PROBE_BROKEN:
        raise SystemExit(1)


@class_fix_group.command("verify")
@click.argument("fix_id")
def verify_cmd(fix_id: str) -> None:
    """Re-run the stored pattern and report what survived the repair."""
    try:
        fix = cf.verify(fix_id)
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    click.echo(cf.format_fix(fix))


@class_fix_group.command("list")
@click.option("--open", "only_open", is_flag=True, help="Only classes still carrying sites.")
def list_cmd(only_open: bool) -> None:
    """Browse declared classes, newest first."""
    fixes = cf.open_fixes() if only_open else cf.all_fixes()
    if not fixes:
        click.echo("No class-fixes declared." if not only_open else "No open class-fixes.")
        return
    for fix in fixes:
        click.echo(cf.format_fix(fix))
        click.echo("")


@class_fix_group.command("show")
@click.argument("fix_id")
def show_cmd(fix_id: str) -> None:
    """Print one class-fix without re-running its search."""
    fix = cf.get(fix_id)
    if fix is None:
        raise SystemExit(f"no such class-fix: {fix_id}")
    click.echo(cf.format_fix(fix))
