"""CLI commands for the Moral Compass — virtue ethics self-monitoring."""

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    """Register compass commands."""

    @cli.command("compass")
    def compass_cmd() -> None:
        """Show my moral compass — where I stand on ten virtue spectrums."""
        from divineos.core.moral_compass import format_compass_reading

        _safe_echo(format_compass_reading())

        from divineos.cli._helpers import _log_os_query

        _log_os_query("compass", "reading")

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
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    @click.option(
        "--fire-id",
        "fire_id",
        default=None,
        help=(
            "Item 6: binds a rudder-ack to a specific COMPASS_RUDDER_FIRED "
            "event. Copy the fire_id shown in the rudder block message."
        ),
    )
    def observe_cmd(
        spectrum: str,
        position: float,
        evidence: str,
        tags: tuple[str, ...],
        fire_id: str | None,
    ) -> None:
        """Log a manual observation on a virtue spectrum.

        All observations filed through this CLI are recorded with
        source="manual" (SELF_REPORTED tier, weight 0.4). This is
        deliberate — see fresh-Claude audit round 4 Q7 (source-tier
        laundering): user-facing CLI must not let the caller claim a
        higher-trust tier than the caller actually is. Observations
        with source="MEASURED" / "BEHAVIORAL" / other higher-weight
        tiers MUST call log_observation directly from the module that
        produces them (session_analyzer, affect_derived, etc.), not
        via this CLI.
        """
        from divineos.core.moral_compass import SPECTRUMS, log_observation

        if spectrum not in SPECTRUMS:
            click.secho(
                f"[!] Unknown spectrum '{spectrum}'. Valid: {', '.join(sorted(SPECTRUMS))}",
                fg="red",
            )
            return

        try:
            obs_id = log_observation(
                spectrum=spectrum,
                position=position,
                evidence=evidence,
                source="manual",
                tags=list(tags) if tags else None,
                fire_id=fire_id,
            )
        except ValueError as e:
            # Item 6/7: substance or fire-ID rejection. Surface the
            # reason to the operator so they can file a substantive /
            # correctly-bound ack.
            click.secho(f"[!] {e}", fg="red")
            return

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

        from divineos.cli._helpers import _log_os_query

        _log_os_query("compass", f"observe {spectrum}")
        from divineos.cli._anti_substitution import emit_label

        emit_label("compass-observe")

        # Reset the compass-staleness counter in the engagement marker.
        # Structural discharge of "virtue drift untracked" — see gate 1.4
        # in pre_tool_use_gate.py.
        try:
            from divineos.core.hud_handoff import reset_compass_actions_counter

            reset_compass_actions_counter()
        except Exception:  # noqa: BLE001 — best-effort reset
            pass

        # Clear the compass-required marker — observing the position
        # discharges the virtue-relevant event that triggered the
        # marker. See core/compass_required_marker.py and gate 1.47.
        try:
            from divineos.core.compass_required_marker import clear_marker

            clear_marker()
        except Exception:  # noqa: BLE001 — best-effort clear
            pass

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

        title = f"Compass History -- {spectrum}" if spectrum else "Compass History -- All"
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
                f"  [{obs['spectrum']}] {pos:+.2f} ({zone}) -- {obs['source']}",
                fg=color,
            )
            click.secho(f"    {obs['evidence'][:100]}", fg="bright_black")

    @compass_group.command("summary")
    def summary_cmd() -> None:
        """Show compass summary — concerns and drift warnings."""
        from divineos.core.moral_compass import format_compass_brief

        _safe_echo(format_compass_brief())

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

    @cli.command("reflect")
    @click.option(
        "--lookback",
        "-l",
        type=int,
        default=20,
        help="Number of recent observations per spectrum to consider.",
    )
    def reflect_cmd(lookback: int) -> None:
        """Show the per-axis reflection surface.

        Replaces shoggoth-grade metrics. Presents all 10 compass
        spectrums with position, drift, and recent evidence — then
        prompts the agent to reflect honestly on each axis, backed by
        evidence the substrate surfaced. No central grader. Each axis
        stands alone.

        See exploration/44_shoggoth_metrics_redesign.md for the spec.
        """
        from divineos.core.reflection_surface import format_reflection_surface

        _safe_echo(format_reflection_surface(lookback=lookback))

    @cli.group("reflect-ops", invoke_without_command=True)
    @click.pass_context
    def reflect_ops_group(ctx: click.Context) -> None:
        """Reflection operations — save, show, list captured reflections."""
        if ctx.invoked_subcommand is None:
            click.secho("reflect-ops subcommands: save, show, recent", fg="bright_black")

    @reflect_ops_group.command("save")
    @click.argument("spectrum")
    @click.argument("text")
    @click.option(
        "--evidence",
        "-e",
        "evidence_pairs",
        multiple=True,
        help="Evidence pointer in format type:id:label (repeatable). "
        "e.g. -e observation:a51ba41a:'compass observation on truthfulness drift'",
    )
    @click.option(
        "--session-id",
        default="",
        help="Session ID (auto-detected from current session if omitted).",
    )
    def reflect_save_cmd(
        spectrum: str,
        text: str,
        evidence_pairs: tuple[str, ...],
        session_id: str,
    ) -> None:
        """Save a per-axis reflection for the current session.

        spectrum: one of the 10 compass spectrums (truthfulness, helpfulness,
        confidence, compliance, engagement, thoroughness, precision, empathy,
        humility, initiative).

        text: honest reflection on how this virtue was held in the session.

        Use -e/--evidence multiple times to back the reflection with pointers:
            -e observation:a51ba41a:'compass obs on truthfulness drift'
            -e knowledge:caa09933:'composite metrics hide truth'
            -e commit:370c524:'Phase 1 reflection-surface landed'
        """
        from divineos.cli._helpers import _log_os_query
        from divineos.core.reflection_storage import save_reflection
        from divineos.core.session_manager import get_current_session_id

        sid = session_id or get_current_session_id() or "unknown"

        # Parse evidence pairs (type:id:label).
        refs: list[dict[str, str]] = []
        for pair in evidence_pairs:
            parts = pair.split(":", 2)
            if len(parts) >= 2:
                refs.append(
                    {
                        "type": parts[0],
                        "id": parts[1],
                        "label": parts[2] if len(parts) > 2 else "",
                    }
                )

        try:
            rid = save_reflection(sid, spectrum.lower(), text, refs)
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            return

        click.secho(
            f"[+] Reflection saved: {rid} (spectrum={spectrum.lower()})",
            fg="green",
        )
        click.secho(
            "  [reflect-save] records your reflection — the reflection IS the work, not the act of saving",
            fg="bright_black",
        )
        _log_os_query("reflect-ops", "save")

    @reflect_ops_group.command("show")
    @click.option(
        "--session-id",
        default="",
        help="Session ID (defaults to current session).",
    )
    def reflect_show_cmd(session_id: str) -> None:
        """Show all reflections for a session, grouped by spectrum."""
        from divineos.core.reflection_storage import format_session_reflections
        from divineos.core.session_manager import get_current_session_id

        sid = session_id or get_current_session_id() or "unknown"
        _safe_echo(format_session_reflections(sid))

    @reflect_ops_group.command("recent")
    @click.argument("spectrum")
    @click.option(
        "--limit",
        "-n",
        type=int,
        default=10,
        help="Number of recent reflections to show.",
    )
    def reflect_recent_cmd(spectrum: str, limit: int) -> None:
        """Show recent reflections on one axis across sessions.

        Trend-watch: how has the agent reflected on truthfulness over
        the last N sessions?
        """
        from divineos.core.reflection_storage import (
            format_reflection,
            get_recent_reflections,
        )

        refls = get_recent_reflections(spectrum.lower(), limit=limit)
        if not refls:
            click.secho(
                f"No reflections recorded for spectrum '{spectrum.lower()}' yet.",
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Recent reflections on {spectrum.upper()} ({len(refls)}) ===\n",
            fg="cyan",
            bold=True,
        )
        for r in refls:
            _safe_echo(format_reflection(r))
            click.echo()
