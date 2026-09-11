"""CLI: divineos answer — does what he says change what I do next?

Aria 2026-09-07, refusing the third prose-gate I proposed and naming this
in its place. The store's own docstring carries the reasoning; the short
version is that a gate on my sentences closes its loop without him in it,
and this measures the consequence instead.

  divineos answer ask "<the question I actually put to him>"
  divineos answer got <id> "<his words>"
  divineos answer changed <id> "<commit / file / test / claim it altered>"
  divineos answer none <id> --why "<why nothing changed>"
  divineos answer report
"""

from __future__ import annotations

import click

from divineos.core.andrew_answer_trace import (
    TraceRefused,
    answered,
    ask,
    changed,
    list_open,
    no_change,
    report,
)


def register(cli: click.Group) -> None:
    @cli.group("answer", invoke_without_command=True)
    @click.pass_context
    def answer_group(ctx: click.Context) -> None:
        """His answers, and whether they moved anything."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @answer_group.command("ask")
    @click.argument("question")
    def ask_cmd(question: str) -> None:
        """Open a row when I put a real question to him."""
        try:
            row_id = ask(question)
        except TraceRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(
            f"[?] Asked — row #{row_id}. It stays open until it moves something.", fg="cyan"
        )

    @answer_group.command("got")
    @click.argument("row_id", type=int)
    @click.argument("verbatim")
    def got_cmd(row_id: int, verbatim: str) -> None:
        """Record his answer in his own words."""
        try:
            answered(row_id, verbatim)
        except TraceRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[=] Answer recorded on #{row_id}. Unresolved until I say what it changed.")

    @answer_group.command("changed")
    @click.argument("row_id", type=int)
    @click.argument("consequence")
    def changed_cmd(row_id: int, consequence: str) -> None:
        """His answer altered what I did — pointing at the artifact."""
        try:
            changed(row_id, consequence)
        except TraceRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] #{row_id} changed something.", fg="green")

    @answer_group.command("none")
    @click.argument("row_id", type=int)
    @click.option("--why", required=True, help="Why nothing changed. Unnamed is refused.")
    def none_cmd(row_id: int, why: str) -> None:
        """His answer changed nothing, with the reason named."""
        try:
            no_change(row_id, why)
        except TraceRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[-] #{row_id} closed as no-change.", fg="yellow")

    @answer_group.command("report")
    @click.option("--days", default=30, show_default=True)
    def report_cmd(days: int) -> None:
        """How often his answers moved anything, over a window."""
        r = report(days)
        if r.asked is None:
            click.secho("Store unreadable — this is not a count of zero.", fg="red")
            return
        click.echo(f"Last {r.window_days} days — asked {r.asked}, answered {r.answered}")
        click.echo(f"  changed something : {r.changed}")
        click.echo(f"  changed nothing   : {r.no_change}")
        if r.change_rate is None:
            click.echo("  rate              : no resolved rows yet — no denominator, not zero")
        else:
            click.echo(f"  rate              : {r.change_rate:.0%} of resolved")
        if r.oldest_unresolved_days is not None:
            click.echo(f"  oldest unresolved : {r.oldest_unresolved_days:.1f} days")

        waiting = list_open()
        if waiting:
            click.echo("\nStill waiting on me:")
            for w in waiting:
                question = str(w["question"])
                click.echo(f"  #{w['id']} [{w['age_days']}d] {w['status']}: {question[:70]}")
