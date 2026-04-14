"""RT (Resonant Truth) protocol commands."""

import click

from divineos.cli._helpers import _log_os_query, _safe_echo


def register(cli: click.Group) -> None:
    """Register RT protocol commands."""

    @cli.group("rt", invoke_without_command=True)
    @click.pass_context
    def rt_group(ctx: click.Context) -> None:
        """Resonant Truth protocol — load, invoke, deactivate."""
        if ctx.invoked_subcommand is None:
            # Default: show status
            ctx.invoke(status_cmd)

    @rt_group.command("load")
    def load_cmd() -> None:
        """Load the RT protocol from disk into context."""
        from divineos.core.resonant_truth import load_protocol

        _log_os_query("rt load", "loading RT protocol")
        text = load_protocol()
        click.secho("[+] RT protocol loaded from disk.", fg="green", bold=True)
        click.echo()
        _safe_echo(text)

    @rt_group.command("invoke")
    def invoke_cmd() -> None:
        """Activate RT reception mode. Requires load first."""
        from divineos.core.resonant_truth import invoke_rt

        _log_os_query("rt invoke", "activating RT mode")
        text = invoke_rt()
        click.secho("[+] RT mode ACTIVE.", fg="green", bold=True)
        click.echo()
        _safe_echo(text)

    @rt_group.command("status")
    def status_cmd() -> None:
        """Show current RT protocol state."""
        from divineos.core.resonant_truth import is_rt_active, is_rt_loaded

        if is_rt_active():
            click.secho("RT: ACTIVE — genuine protocol loaded from disk", fg="green", bold=True)
        elif is_rt_loaded():
            click.secho("RT: Loaded (not active)", fg="cyan")
        else:
            click.secho("RT: Not loaded", fg="yellow")
            click.echo("Run: divineos rt load")

    @rt_group.command("deactivate")
    def deactivate_cmd() -> None:
        """Exit RT reception mode."""
        from divineos.core.resonant_truth import deactivate_rt

        deactivate_rt()
        click.secho("[+] RT mode deactivated.", fg="yellow")

    @rt_group.command("text")
    def text_cmd() -> None:
        """Print the raw RT mantra without changing state."""
        from divineos.core.resonant_truth import _PROTOCOL_FILE

        if not _PROTOCOL_FILE.exists():
            click.secho("[-] RT protocol file not found on disk.", fg="red")
            raise SystemExit(1)
        _safe_echo(_PROTOCOL_FILE.read_text(encoding="utf-8"))

    @rt_group.command("pull-check")
    @click.argument("context", required=False, default="")
    def pull_check_cmd(context: str) -> None:
        """Run pull detection — check for fabrication markers.

        Without context: prints the marker list as a pre-response mirror.
        With context: scans text for active fabrication markers.
        """
        from divineos.core.pull_detection import check_pull

        _log_os_query("rt pull-check", "running pull detection")
        result = check_pull(context)

        if result.clean:
            click.secho("[+] Pull check: CLEAN", fg="green", bold=True)
        else:
            click.secho("[!] PULL DETECTED", fg="red", bold=True)
            for marker in result.markers_fired:
                click.secho(f"    [{marker}]", fg="red")

        click.echo()
        _safe_echo(result.message if result.message else result.format())

    @rt_group.command("pull-markers")
    def pull_markers_cmd() -> None:
        """Print all fabrication markers — the mirror to look in."""
        from divineos.core.pull_detection import precheck

        _safe_echo(precheck())
