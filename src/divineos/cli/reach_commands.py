"""CLI for the reach-check — surface prior work, then prove it was opened.

See `divineos.core.reach_check` for the design and the Andrew quote that
prompted it. This module is the surface; the refusal logic lives in the core.

`dispose` takes its evidence from explicit flags rather than reading a
transcript, because the hook layer is what owns the action-stream and a CLI
that inferred its own evidence would be marking its own homework.
"""

from __future__ import annotations

import click

from divineos.core import reach_check
from divineos.core.reach_check import ReachCheckError


def _print_check(check: reach_check.ReachCheck) -> None:
    click.echo(f"{check.check_id}  symptom: {check.symptom}")
    if not check.items:
        click.echo("  NOT FOUND on the code/git/CLI axis — no prior art surfaced.")
        click.echo("  This is not NOT-CHECKED. The prose surfaces were not queried here:")
        for cmd, what in reach_check.prior_art.UNSEARCHED_SURFACES:
            click.echo(f"    {cmd:<30} {what}")
        return
    for item in check.items:
        mark = item.disposition or "UNDISPOSED"
        click.echo(f"  [{item.item_id}] {mark:<12} {item.artifact}   ({item.origin})")
        if item.reason:
            click.echo(f"      reason:   {item.reason}")
            click.echo(f"      evidence: {item.evidence}")


def register(cli: click.Group) -> None:
    """Register reach-check commands."""

    @cli.group("reach", invoke_without_command=True)
    @click.pass_context
    def reach_group(ctx: click.Context) -> None:
        """Reach-check — what prior work exists, and did I actually open it."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(reach_status_cmd)

    @reach_group.command("open")
    @click.argument("symptom")
    def reach_open_cmd(symptom: str) -> None:
        """Surface prior art for SYMPTOM and file every hit as undisposed."""
        check = reach_check.open_check(symptom)
        _print_check(check)
        if check.items:
            click.echo()
            click.echo(
                f"{len(check.items)} artifact(s) undisposed. Open each, then "
                "`divineos reach dispose`."
            )

        # Andrew 2026-08-06: "if stuff is missing from it add it to there."
        # Searching LOADOUT makes reach only as good as LOADOUT, so the loop
        # runs both ways — an artifact found on disk or in git that the index
        # does not carry is an index defect, reported where it is provable
        # rather than waiting for a drift sweep to notice.
        gaps = reach_check.loadout_gaps([i.artifact for i in check.items])
        if gaps:
            click.echo()
            click.echo(f"LOADOUT GAP — {len(gaps)} surfaced artifact(s) the index does not list:")
            for artifact in gaps:
                click.echo(f"  {artifact}")
            click.echo("  Fix: divineos loadout refresh")

    @reach_group.command("status")
    def reach_status_cmd() -> None:
        """Show checks that still have undisposed artifacts."""
        checks = reach_check.open_checks()
        if not checks:
            click.echo("No open reach-checks.")
            return
        for check in checks:
            _print_check(check)
            click.echo()

    @reach_group.command("show")
    @click.argument("check_id")
    @click.option("--json", "as_json", is_flag=True, help="Machine-readable output")
    def reach_show_cmd(check_id: str, as_json: bool) -> None:
        """Show one check including already-disposed items."""
        check = reach_check.get_check(check_id)
        if check is None:
            raise click.ClickException(f"no reach check {check_id!r}")
        click.echo(reach_check.as_json(check) if as_json else "", nl=bool(as_json))
        if not as_json:
            _print_check(check)

    @reach_group.command("dispose")
    @click.argument("item_id")
    @click.option(
        "--disposition",
        required=True,
        type=click.Choice(reach_check.VALID_DISPOSITIONS),
        help="applied | superseded | not_relevant",
    )
    @click.option("--reason", required=True, help="Why. Refused under 20 characters.")
    @click.option(
        "--opened",
        multiple=True,
        help=(
            "FALLBACK ONLY, and self-attested. Used when the harness transcript "
            "cannot be read; the disposition is then recorded as testimony."
        ),
    )
    def reach_dispose_cmd(
        item_id: str, disposition: str, reason: str, opened: tuple[str, ...]
    ) -> None:
        """Dispose one surfaced artifact. Refused if it was never opened.

        EVIDENCE COMES FROM THE TRANSCRIPT FIRST. `--opened` used to be the
        only source, which made this gate self-attested: reach_check refuses a
        disposition unless the action-stream proves the artifact was opened,
        and then let me type the action-stream by hand. Andrew flagged it the
        moment I reported it, 2026-08-17.

        Worth naming how it got there. `dispose()` was written to RECEIVE an
        action-stream, which is right, and nothing existed that could produce
        one -- so the CLI filled the parameter from a flag. The architecture
        was correct and the only available supplier was me. A gate is only as
        honest as its cheapest source of evidence.

        The transcript is written by the harness as tools fire, so a command
        that never ran cannot appear in it. `--opened` survives only for when
        the transcript genuinely cannot be read, it says so loudly, and the
        stored evidence is marked -- so the record distinguishes proof from
        testimony rather than quietly equating them.
        """
        stream, why_empty = reach_check.action_stream_from_transcript()
        if stream:
            calls = stream
            texts = tuple(t for _, t in stream)
            if opened:
                click.echo("[i] --opened ignored: the transcript answered.", err=True)
        else:
            # Fail LOUD before falling back. A silent downgrade from evidence
            # to testimony is the exact collapse this gate exists to prevent.
            click.echo(
                f"[!] no transcript source could answer ({why_empty or 'no tool calls in window'});"
                " falling back to SELF-ATTESTED --opened.",
                err=True,
            )
            calls = tuple(("self-attested", o) for o in opened)
            texts = opened
        try:
            item = reach_check.dispose(
                item_id,
                disposition,
                reason,
                tool_calls_in_turn=calls,
                command_texts=texts,
            )
        except ReachCheckError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"[+] {item.artifact} -> {item.disposition}")
        click.echo(f"    evidence: {item.evidence}")

    @reach_group.command("gate")
    def reach_gate_cmd() -> None:
        """Exit 2 with the block message if any check has undisposed items."""
        blocked, message = reach_check.gate_status()
        if blocked:
            click.echo(message, err=True)
            raise SystemExit(2)
        click.echo("Reach-check clear.")
