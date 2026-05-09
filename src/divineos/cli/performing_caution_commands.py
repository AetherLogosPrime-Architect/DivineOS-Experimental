"""``divineos check-caution`` — manual performing-caution detector.

Catches caution-as-substitute-for-doing per Aria's April 20 falsifier:
genuine caution names a specific mechanism; performing caution gestures
at hazard-classes without mechanism.
"""

from __future__ import annotations

import sys

import click

from divineos.core.performing_caution_detector import (
    detect,
    format_findings,
    has_critical,
    has_findings,
)


@click.command("check-caution")
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
    help="Exit code 1 on warn, 2 on critical.",
)
def check_caution(text: str | None, stdin: bool, strict: bool) -> None:
    """Check text for performing-caution shapes (vague hazards, indefinite deferral)."""
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
    cli.add_command(check_caution)
