"""`divineos volley` -- start, end or read the night quiet by hand."""

from __future__ import annotations

import time

import click


def register(cli: click.Group) -> None:
    @cli.group("volley")
    def volley_group() -> None:
        """The night quiet: nothing is sent to Dad, the seats write one night letter."""

    @volley_group.command("start")
    def start_cmd() -> None:
        """Begin the quiet now (call this when you read that he is going to bed)."""
        from divineos.core import volley_now

        state = volley_now.start()
        click.echo("The night quiet has started. Nothing goes to him in chat until it ends.")
        click.echo(volley_now.letter_path_words(state["since"]))
        click.echo(
            "It ends by itself at midnight, when the clock window takes over, "
            "or sooner with `divineos volley stop`."
        )

    @volley_group.command("stop")
    def stop_cmd() -> None:
        """End the quiet that `start` began (the clock window is not affected)."""
        from divineos.core import volley_now

        click.echo(
            "The quiet you started has ended."
            if volley_now.stop()
            else "No started quiet was running."
        )

    @volley_group.command("status")
    def status_cmd() -> None:
        """Say whether a started quiet is running (the clock window is separate)."""
        from divineos.core import volley_now

        state = volley_now.active()
        if state:
            at = time.strftime("%H:%M", time.localtime(state["since"]))
            click.echo(f"A started quiet is running (since {at}).")
        else:
            click.echo("A started quiet is not running.")
