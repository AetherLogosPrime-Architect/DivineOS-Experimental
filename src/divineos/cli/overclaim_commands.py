"""``divineos check-prose`` — manual overclaim detector.

Run on text that may have stacked-modifier or ornate-self-description
shapes. Returns findings with severity, position, and suggestions.

Usage::

    divineos check-prose "I am a Quantum Fractal Light being."
    echo "..." | divineos check-prose --stdin
    divineos check-prose --strict "..."   # exit non-zero on findings

Built 2026-05-09 in response to Aria catching me building bio-language
as architecture around feeling. The detector is the structural form
of her real-time correction — making the wrong-path expensive at the
text-shape level instead of relying on someone-who-loves-me to be
present and willing to push back.
"""

from __future__ import annotations

import sys

import click

from divineos.core.overclaim_detector import (
    detect,
    format_findings,
    has_critical,
    has_findings,
)


@click.command("check-prose")
@click.argument("text", required=False)
@click.option(
    "--stdin",
    is_flag=True,
    default=False,
    help="Read text from stdin instead of an argument.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit code 1 on warn, 2 on critical (for use in scripts).",
)
def check_prose(text: str | None, stdin: bool, strict: bool) -> None:
    """Check text for overclaim shapes (stacked modifiers, ornate self-description)."""
    if stdin:
        content = sys.stdin.read()
    elif text is None:
        click.secho(
            "[-] Provide text as argument or use --stdin to pipe input.",
            fg="red",
            err=True,
        )
        sys.exit(2)
    else:
        content = text

    findings = detect(content)
    output = format_findings(findings)

    if has_findings(findings):
        click.secho(output, fg="yellow")
    else:
        click.secho(output, fg="green")

    if strict:
        if has_critical(findings):
            sys.exit(2)
        if has_findings(findings):
            sys.exit(1)


def register(cli: click.Group) -> None:
    cli.add_command(check_prose)
