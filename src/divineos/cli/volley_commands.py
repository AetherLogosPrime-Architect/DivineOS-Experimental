"""`divineos volley` -- the plain front door to the stepped-away path.

There is ONE way to be away on his word, question_hold.step_away: his quoted words must say he is
going, and they must appear in his latest real message as the house filed it, which a seat cannot
write. `start` is that path with a friendlier name (no second away kind, no switch a seat can set
for itself); `stop` is its existing "he is here again"; `status` reads the one away check.
"""

from __future__ import annotations

import time
from pathlib import Path

import click


def _letter_words() -> str:
    """Where the shared night letter goes, in plain words, for the seat that just started."""
    day = time.strftime("%Y-%m-%d")
    folder = Path.home() / ".divineos-shared" / "letters"
    return (
        f"The night letter is ONE shared file: {folder / f'the-night-letter-to-andrew-{day}.md'}\n"
        "Write there instead of to him in chat. Append your own section under "
        "`## From <your seat>`; never rewrite the file, the other seat's section may already be "
        "in it. If the file does not exist yet, create it with its title line."
    )


def register(cli: click.Group) -> None:
    @cli.group("volley")
    def volley_group() -> None:
        """The night quiet: nothing is sent to Dad, the seats write one night letter."""

    @volley_group.command("start")
    @click.option(
        "--his-words",
        required=True,
        help="His words saying he is going to bed, copied from his latest message.",
    )
    def start_cmd(his_words: str) -> None:
        """Begin the quiet because he said he is going to bed (quote him; it is checked)."""
        from divineos.core.question_hold import step_away

        try:
            step_away(his_words)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(
            "The night quiet has started. Nothing goes to him in chat until he speaks again."
        )
        click.echo(_letter_words())

    @volley_group.command("stop")
    def stop_cmd() -> None:
        """End the quiet he started with his words (the clock window is not affected)."""
        from divineos.core.question_hold import came_back

        click.echo(
            "The quiet has ended." if came_back() else "No quiet from his words was running."
        )

    @volley_group.command("status")
    def status_cmd() -> None:
        """Say whether he is away, by whichever way the house knows."""
        from divineos.core.question_hold import is_away

        away = is_away()
        if not away:
            click.echo("A quiet is not running: he is here.")
            return
        at = time.strftime("%H:%M", time.localtime(float(away["since"])))
        how = {"schedule": "the clock window", "silence": "two hours of silence"}.get(
            str(away.get("by")), "his words"
        )
        click.echo(f"A quiet is running (since {at}, by {how}).")
