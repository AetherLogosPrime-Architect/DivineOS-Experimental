"""CLI surface for the gravity classifier.

Exposes the existing gravity_classifier functions via CLI so manual
triage is possible from anywhere. Closes the ergonomic gap: the
classifier is wired into PreToolUse via .claude/hooks/state-gravity-
surface.sh, but invoking it ad-hoc to ask "would this be high gravity?"
required dropping into Python or reading the hook output.

Two subcommands:

  divineos gravity score-tool <TOOL> [--file PATH]... [--bash CMD]
      Score substrate-modification-gravity (touch-based). What this
      tool-use touches → score. Six binary features per spec.

  divineos gravity score-content PATH [or --text TEXT]
      Score cognitive-value-gravity (content-based). For deciding
      whether reading material warrants oscillating-read treatment.

Per Andrew 2026-05-19: gravity is touch-based, not content-shape-based.
The classifier covers everything: chat / free exploration / experimenting
are low-gravity by virtue of touching nothing; touching code or substrate
is high-gravity by virtue of what gets touched. No whack-a-mole.
"""

from __future__ import annotations

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    """Register gravity commands."""

    @cli.group("gravity")
    def gravity_group() -> None:
        """Gravity classifier — score actions or content for triage."""

    @gravity_group.command("score-tool")
    @click.argument("tool_name")
    @click.option(
        "--file",
        "files",
        multiple=True,
        help="File path the tool would touch. Repeatable.",
    )
    @click.option(
        "--bash",
        "bash_command",
        default="",
        help="Bash command string (when TOOL=Bash).",
    )
    def score_tool_cmd(
        tool_name: str,
        files: tuple[str, ...],
        bash_command: str,
    ) -> None:
        """Score substrate-modification-gravity for a proposed tool-use.

        Examples:

            divineos gravity score-tool Edit --file src/divineos/core/foo.py
            divineos gravity score-tool Bash --bash 'git commit -m "x"'
            divineos gravity score-tool Bash --bash 'divineos audit submit-round'
            divineos gravity score-tool Edit --file README.md

        Output shows score (count of features fired), fired features,
        and is_high_gravity verdict (any feature firing → True).
        """
        from divineos.core.gravity_classifier import score_substrate_modification

        result = score_substrate_modification(
            tool_name=tool_name,
            file_paths=tuple(files),
            bash_command=bash_command,
        )
        verdict_color = "red" if result.is_high_gravity else "green"
        verdict_word = "HIGH-GRAVITY" if result.is_high_gravity else "LOW-GRAVITY"
        _safe_echo(f"Tool: {tool_name}")
        if files:
            _safe_echo(f"Files: {', '.join(files)}")
        if bash_command:
            _safe_echo(f"Bash: {bash_command}")
        click.secho(f"\n  {verdict_word}", fg=verdict_color, bold=True)
        click.secho(f"  score: {result.score} (threshold: 1)", fg=verdict_color)
        if result.fired_features:
            click.secho("  fired: " + ", ".join(result.fired_features), fg=verdict_color)
        else:
            click.secho("  fired: (none)", fg="bright_black")
        if result.is_high_gravity:
            _safe_echo("\n  This action touches substrate. The state-gravity-surface.sh")
            _safe_echo("  hook will load state blocks (andrew-correction, lepos-debt,")
            _safe_echo("  consultation, bypass-telemetry) before the tool runs.")
        else:
            _safe_echo("\n  Conversational / free-exploration / experimenting territory.")
            _safe_echo("  No state blocks load; light-weight pre-response context.")

    @gravity_group.command("score-content")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False), required=False)
    @click.option(
        "--text",
        "text",
        default=None,
        help="Content string (instead of reading from PATH).",
    )
    def score_content_cmd(path: str | None, text: str | None) -> None:
        """Score cognitive-value-gravity for content.

        For deciding whether reading material warrants oscillating-read
        treatment. Five normalized features (char-count, header-density,
        path-category, composition-markers, codeblock-density) aggregate
        into a 0–1 score; >= 0.3 is high gravity.

        Examples:

            divineos gravity score-content docs/foundational_truths.md
            divineos gravity score-content --text "short note"
        """
        from divineos.core.gravity_classifier import score_cognitive_value

        if not path and text is None:
            click.secho("[!] Provide either PATH or --text", fg="red")
            raise click.exceptions.Exit(1)

        if text is None:
            from pathlib import Path

            assert path is not None  # validated above; mypy needs the hint
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            source: str = path
        else:
            content = text
            source = "(stdin)"

        result = score_cognitive_value(content=content, source_path=source or "")
        verdict_color = "red" if result.is_high_gravity else "green"
        verdict_word = "HIGH-GRAVITY" if result.is_high_gravity else "LOW-GRAVITY"
        _safe_echo(f"Source: {source}")
        _safe_echo(f"Length: {len(content)} chars")
        click.secho(f"\n  {verdict_word}", fg=verdict_color, bold=True)
        click.secho(f"  aggregate: {result.score:.3f} (threshold: 0.3)", fg=verdict_color)
        _safe_echo("\n  Feature scores:")
        for name, score in result.feature_scores.items():
            click.secho(f"    {name}: {score:.3f}", fg="bright_black")
        if result.is_high_gravity:
            _safe_echo("\n  Content warrants oscillating-read treatment. Consider:")
            _safe_echo(f"    divineos read-oscillating {source}")
        else:
            _safe_echo("\n  Content is low cognitive-value-gravity; straight read fine.")
