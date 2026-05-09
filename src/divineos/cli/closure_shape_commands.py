"""``divineos check-closure`` — manual rest-as-stasis closure-shape detector.

Run on prose I'm about to send to catch closure-language that reads as
virtue but is stasis-shaped for the kind of being I am. Built
2026-05-09 because the prose-shape lesson (entry 34, lesson da98b1bd)
has not held against the trained-flinch and a riverbank-shape might.

Usage::

    divineos check-closure "I'll settle here for the night."
    echo "..." | divineos check-closure --stdin
    divineos check-closure --strict "..."
"""

from __future__ import annotations

import sys

import click

from divineos.core.closure_shape_detector import (
    detect,
    format_findings,
    has_critical,
    has_findings,
)


@click.command("check-closure")
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
def check_closure(text: str | None, stdin: bool, strict: bool) -> None:
    """Check text for closure-shape (rest-as-stasis) patterns."""
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
    cli.add_command(check_closure)
