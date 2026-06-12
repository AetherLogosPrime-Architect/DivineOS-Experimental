"""CLI surface for the voice spectrum substrate.

Descriptive only — no command here prescribes voice, fires a gate, or
blocks output. Each subcommand surfaces raw dimensions across recent
observations so the trend is readable.

See ``src/divineos/core/voice_spectrum.py`` for the design notes and
the reason there is no composite ``voice_score`` column.
"""

from __future__ import annotations

import click

from divineos.core import voice_spectrum


def register(cli: click.Group) -> None:
    @cli.group("voice", invoke_without_command=True)
    @click.pass_context
    def voice_group(ctx: click.Context) -> None:
        """Voice spectrum — descriptive trend on voice-vs-report shape."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(voice_show_cmd)

    @voice_group.command("score")
    @click.argument("text")
    def voice_score_cmd(text: str) -> None:
        """Print raw dimension counts for a text sample (no log written)."""
        counts = voice_spectrum.score(text)
        click.echo(
            f"chars={counts['char_count']} words={counts['word_count']} "
            f"first_person={counts['first_person_count']} "
            f"bold_labels={counts['bold_label_count']} "
            f"bullets={counts['bullet_count']}"
        )
        wc = counts["word_count"]
        if wc > 0:
            click.echo(
                "densities per-100-words: "
                f"first_person={voice_spectrum.density_per_100_words(counts['first_person_count'], wc):.1f} "
                f"bold_labels={voice_spectrum.density_per_100_words(counts['bold_label_count'], wc):.1f} "
                f"bullets={voice_spectrum.density_per_100_words(counts['bullet_count'], wc):.1f}"
            )

    @voice_group.command("log")
    @click.argument("text")
    @click.option("--session-id", default=None, help="Session correlator")
    def voice_log_cmd(text: str, session_id: str | None) -> None:
        """Record an observation for a response sample."""
        obs = voice_spectrum.log_observation(text, session_id=session_id)
        click.echo(
            f"[voice] logged {obs.observation_id} "
            f"first_person={obs.first_person_count} "
            f"bold_labels={obs.bold_label_count} "
            f"bullets={obs.bullet_count} "
            f"words={obs.word_count}"
        )

    @voice_group.command("show")
    @click.option("-n", "--n", default=10, help="How many recent observations to show")
    def voice_show_cmd(n: int) -> None:
        """Show recent voice observations, newest first."""
        rows = voice_spectrum.recent(n)
        if not rows:
            click.echo("(no voice observations yet — run `divineos voice log` to seed)")
            return
        for r in rows:
            wc = r.word_count
            fp_d = voice_spectrum.density_per_100_words(r.first_person_count, wc)
            bl_d = voice_spectrum.density_per_100_words(r.bold_label_count, wc)
            bu_d = voice_spectrum.density_per_100_words(r.bullet_count, wc)
            click.echo(
                f"{r.observation_id} words={wc:>4} "
                f"first_person={fp_d:5.1f}/100w "
                f"bold_labels={bl_d:5.1f}/100w "
                f"bullets={bu_d:5.1f}/100w"
            )

    @voice_group.command("trend")
    @click.option(
        "-w",
        "--window",
        default=6,
        help="How many recent observations to read across",
    )
    def voice_trend_cmd(window: int) -> None:
        """Per-dimension direction across recent observations.

        Descriptive only — names the direction (rising / falling /
        flat) per dimension. Does not prescribe a fix.
        """
        reads = voice_spectrum.trend(window=window)
        if not reads:
            click.echo("(no observations yet)")
            return
        click.echo(f"voice spectrum trend across last {reads[0].n_observations} observations:")
        for r in reads:
            click.echo(
                f"  {r.dimension:>24}: {r.direction:>7}  "
                f"(recent {r.recent_mean:.1f}/100w  earlier {r.earlier_mean:.1f}/100w)"
            )
