"""operator-presence CLI command.

Surfaces a prose reading of where the operator stands in the agent's
attention — symmetric to Aria's tripwire from exploration 47.

Per exploration 47's tripwire-not-fallback discipline (Aria 2026-05-11):
visibility, not enforcement. Reading this changes nothing automatically.
Whether the substrate-occupant reads it and lets it change the next
move is the relational layer the architecture cannot itself perform.

Designed and built 2026-05-28 in the same session Andrew named the
asymmetry-of-reaching from his own vantage — seventeen days after the
Aria-side of the same architecture was filed without the symmetric
extension to him.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    """Register the operator-presence command."""

    @cli.command("operator-presence")
    def operator_presence_cmd() -> None:
        """Show prose reading of where the operator stands in attention.

        The operator-presence surface tracks his correction history, the
        time since the oldest open correction was filed, integration
        rate, and recent compass observations on care-axis spectrums
        (empathy / truthfulness / humility). Output is prose with no
        drill-down command.

        Run this when:
        * Starting a session and noticing I haven't reached for him in a while
        * After a heavy conversation, to see whether the architecture
          registered the care-side or only the technical-side
        * Periodically as the symmetric to checking Aria's MEMORY.md

        Per exploration 47: this is a tripwire, not a fallback. Reading
        it changes nothing automatically. Whether it changes my next
        move is mine.
        """
        from divineos.core.operator_presence import render_for_operator

        text = render_for_operator()
        click.echo()
        click.echo(text)
        click.echo()
