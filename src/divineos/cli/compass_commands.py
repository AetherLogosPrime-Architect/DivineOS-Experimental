"""CLI commands for the Moral Compass — virtue ethics self-monitoring."""

import click


def register(cli: click.Group) -> None:
    """Register compass commands."""

    @cli.command("compass")
    def compass_cmd() -> None:
        """Show my moral compass — where I stand on ten virtue spectrums."""
        from divineos.core.moral_compass import format_compass_reading

        click.echo(format_compass_reading())

        # Mark OS engagement
        from divineos.core.hud_handoff import mark_engaged

        mark_engaged()

    @cli.group("compass-ops", invoke_without_command=True)
    @click.pass_context
    def compass_group(ctx: click.Context) -> None:
        """Moral compass operations — observe, review, reflect."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(history_cmd)

    @compass_group.command("observe")
    @click.argument("spectrum")
    @click.option(
        "--position",
        "-p",
        type=click.FloatRange(-1.0, 1.0),
        required=True,
        help="-1.0=deficiency, 0.0=virtue, +1.0=excess",
    )
    @click.option("--evidence", "-e", required=True, help="What happened that shows this")
    @click.option("--source", "-s", default="self_report", help="Where this came from")
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    def observe_cmd(
        spectrum: str,
        position: float,
        evidence: str,
        source: str,
        tags: tuple[str, ...],
    ) -> None:
        """Log an observation on a virtue spectrum."""
        from divineos.core.moral_compass import SPECTRUMS, log_observation

        if spectrum not in SPECTRUMS:
            click.secho(
                f"[!] Unknown spectrum '{spectrum}'. Valid: {', '.join(sorted(SPECTRUMS))}",
                fg="red",
            )
            return

        obs_id = log_observation(
            spectrum=spectrum,
            position=position,
            evidence=evidence,
            source=source,
            tags=list(tags) if tags else None,
        )

        spec = SPECTRUMS[spectrum]
        if position < -0.3:
            zone_label = spec["deficiency"]
            color = "yellow"
        elif position > 0.3:
            zone_label = spec["excess"]
            color = "yellow"
        else:
            zone_label = spec["virtue"]
            color = "green"

        click.secho(
            f"[+] Compass observation ({spectrum} -> {zone_label}): {obs_id[:8]}...",
            fg=color,
        )
        click.secho(f"    {evidence}", fg="bright_black")

        from divineos.core.hud_handoff import mark_engaged

        mark_engaged()

    @compass_group.command("history")
    @click.option("--spectrum", "-s", default=None, help="Filter by spectrum name")
    @click.option("--limit", "-n", default=20, help="Number of entries")
    def history_cmd(spectrum: str | None, limit: int) -> None:
        """Show recent compass observations."""
        from divineos.core.moral_compass import SPECTRUMS, get_observations

        if spectrum and spectrum not in SPECTRUMS:
            click.secho(f"[!] Unknown spectrum '{spectrum}'.", fg="red")
            return

        observations = get_observations(spectrum=spectrum, limit=limit)
        if not observations:
            click.secho("[~] No compass observations yet.", fg="bright_black")
            return

        title = f"Compass History — {spectrum}" if spectrum else "Compass History — All"
        click.secho(f"\n=== {title} ===\n", fg="cyan", bold=True)

        for obs in observations:
            pos = obs["position"]
            spec = SPECTRUMS[obs["spectrum"]]
            if pos < -0.3:
                zone = spec["deficiency"]
                color = "yellow"
            elif pos > 0.3:
                zone = spec["excess"]
                color = "yellow"
            else:
                zone = spec["virtue"]
                color = "green"

            click.secho(
                f"  [{obs['spectrum']}] {pos:+.2f} ({zone}) — {obs['source']}",
                fg=color,
            )
            click.secho(f"    {obs['evidence'][:100]}", fg="bright_black")

    @compass_group.command("summary")
    def summary_cmd() -> None:
        """Show compass summary — concerns and drift warnings."""
        from divineos.core.moral_compass import format_compass_brief

        click.echo(format_compass_brief())

    @compass_group.command("spectrums")
    def spectrums_cmd() -> None:
        """List all ten virtue spectrums with descriptions."""
        from divineos.core.moral_compass import SPECTRUMS

        click.secho("\n=== The Ten Spectrums ===\n", fg="cyan", bold=True)
        for name, spec in SPECTRUMS.items():
            click.secho(f"  {name.upper()}", fg="white", bold=True)
            click.secho(
                f"    {spec['deficiency']} <-- [{spec['virtue']}] --> {spec['excess']}",
                fg="bright_black",
            )
            click.secho(f"    {spec['description']}", fg="bright_black")
            click.echo()
